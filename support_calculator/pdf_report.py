import logging
from datetime import date
from html import escape

from weasyprint import HTML

logger = logging.getLogger(__name__)


def _format_currency(value: float) -> str:
    rounded = round(value or 0.0)
    sign = "-" if rounded < 0 else ""
    amount = abs(rounded)
    return f"{sign}${amount:,.0f}"


def _format_percent(value: float) -> str:
    return f"{value:.2f}%"


def _format_monthly(value: float) -> str:
    return _format_currency((value or 0.0) / 12.0)


def _render_reference_list(source_references: list[dict[str, str]]) -> str:
    items = []
    for reference in source_references:
        items.append(
            "<li>"
            f"<a href=\"{escape(reference['url'])}\">{escape(reference['label'])}</a>"
            "</li>"
        )
    return "".join(items)


def _selected_range_point_label(value: str) -> str:
    labels = {
        "low": "Low",
        "mid": "Mid",
        "high": "High",
        "fixed_total_override": "Fixed total override",
    }
    return labels.get(value, str(value or "").replace("_", " ").title())


def _render_key_value_rows(rows: list[tuple[str, str]]) -> str:
    return "".join(
        f"<tr><td>{escape(label)}</td><td class=\"numeric\">{escape(value)}</td></tr>"
        for label, value in rows
    )


def _render_benefit_rows(spousal_support: dict) -> str:
    payor_benefits = spousal_support["benefits"]["payor"]
    recipient_benefits = spousal_support["benefits"]["recipient"]
    rows = []
    for item in spousal_support["benefits"]["lineItems"]:
        key = item["key"]
        rows.append(
            "<tr>"
            f"<td>{escape(item['label'])}</td>"
            f"<td class=\"numeric\">{_format_currency(payor_benefits.get(key, 0.0))}</td>"
            f"<td class=\"numeric\">{_format_currency(recipient_benefits.get(key, 0.0))}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_support_report_pdf(
    *,
    scenario: dict,
    child_support: dict,
    spousal_support: dict,
    source_references: list[dict[str, str]],
) -> bytes:
    logger.info(
        "Rendering PDF report for jurisdiction=%s children=%s tax_year=%s",
        scenario["jurisdiction"],
        scenario["children"],
        scenario["taxYear"],
    )
    payor_benefits = spousal_support["benefits"]["payor"]["totalAnnual"]
    recipient_benefits = spousal_support["benefits"]["recipient"]["totalAnnual"]
    benefit_assumptions = spousal_support["benefits"]["assumptions"]
    assumption_summary = spousal_support["assumptions"]
    override_summary = spousal_support["overrides"]
    payor_tax_profile = spousal_support["payorTaxProfile"]
    recipient_tax_profile = spousal_support["recipientTaxProfile"]
    notes = []
    if spousal_support["payorSpousalIncome"] != spousal_support["payorIncome"]:
        notes.append(
            "Payor income for spousal support only: "
            f"{_format_currency(spousal_support['payorSpousalIncome'])}"
        )
    if spousal_support["recipientSpousalIncome"] != spousal_support["recipientIncome"]:
        notes.append(
            "Recipient income for spousal support only: "
            f"{_format_currency(spousal_support['recipientSpousalIncome'])}"
        )
    if spousal_support["childSupportOverrideMonthly"] is not None:
        notes.append(
            "Net child support override: "
            f"{_format_currency(spousal_support['childSupportOverrideMonthly'])} per month"
        )
    if spousal_support["fixedTotalSupportAnnual"] is not None:
        notes.append(
            "Fixed total gross support override: "
            f"{_format_currency(spousal_support['fixedTotalSupportAnnual'])}"
        )
    if spousal_support["relationshipYears"] is not None:
        notes.append(f"Length of relationship/cohabitation: {spousal_support['relationshipYears']:.2f} years")
    if spousal_support["recipientAgeAtSeparation"] is not None:
        notes.append(
            f"Recipient age at separation: {spousal_support['recipientAgeAtSeparation']:.0f} years"
        )
    if spousal_support["eligibleDependantClaimant"] != "none":
        notes.append(
            "Eligible dependant credit claimed by "
            f"{spousal_support['eligibleDependantClaimant'].capitalize()}"
        )
    if benefit_assumptions["explicitAllocation"]:
        notes.append(
            "Explicit child allocation applied: "
            f"payor {benefit_assumptions['payorRegisteredChildren']} child(ren), "
            f"recipient {benefit_assumptions['recipientRegisteredChildren']} child(ren)"
        )
    if (
        benefit_assumptions["payorHouseholdAdults"] != 1
        or benefit_assumptions["recipientHouseholdAdults"] != 1
    ):
        notes.append(
            "Household adults modeled as "
            f"{benefit_assumptions['payorHouseholdAdults']} for payor and "
            f"{benefit_assumptions['recipientHouseholdAdults']} for recipient"
        )
    assumption_rows = [
        ("Formula", "With-child shared-custody SSAG-style"),
        ("Selected point in range", _selected_range_point_label(assumption_summary["selectedRangePoint"])),
        ("Eligible dependant claimant", spousal_support["eligibleDependantClaimant"].capitalize()),
        (
            "Benefit allocation",
            "Explicit household allocation"
            if benefit_assumptions["explicitAllocation"]
            else "Default shared-custody half-split",
        ),
        (
            "Duration inputs",
            "Provided" if assumption_summary["durationInputsProvided"] else "Not provided",
        ),
    ]
    override_rows = [
        (
            "Child support applied",
            f"{_format_currency(override_summary['childSupport']['appliedNetMonthly'])} per month",
        ),
        (
            "Child support guideline",
            f"{_format_currency(override_summary['childSupport']['guidelineNetMonthly'])} per month",
        ),
        (
            "Fixed total support",
            _format_currency(override_summary["spousalSupport"]["fixedTotalSupportAnnual"])
            if override_summary["spousalSupport"]["fixedTotalSupportApplied"]
            else "None",
        ),
        (
            "Separate spousal incomes",
            "Applied"
            if override_summary["incomeAdjustments"]["separateSpousalIncomesApplied"]
            else "Not applied",
        ),
        (
            "Trace payload",
            f"v{spousal_support['calculationTrace']['traceVersion']} in JSON response",
        ),
    ]
    benefit_rows = _render_benefit_rows(spousal_support)

    html = f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <style>
      @page {{
        size: Letter;
        margin: 0.55in 0.55in 0.65in;
      }}
      body {{
        font-family: "Georgia", "Times New Roman", serif;
        color: #251f1a;
        font-size: 9.5pt;
        line-height: 1.3;
      }}
      h1, h2, h3, p {{
        margin: 0;
      }}
      .page-header {{
        border-bottom: 1.2pt solid #786554;
        padding-bottom: 10pt;
        margin-bottom: 12pt;
      }}
      .page-header h1 {{
        font-size: 15pt;
        letter-spacing: 0.02em;
      }}
      .page-header__meta {{
        margin-top: 4pt;
        color: #62574c;
        font-size: 8.5pt;
      }}
      .report-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10pt;
      }}
      .section {{
        margin-bottom: 12pt;
        break-inside: avoid;
      }}
      .section h2 {{
        font-size: 10.5pt;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #5b4d40;
        border-bottom: 0.8pt solid #bba993;
        padding-bottom: 3pt;
        margin-bottom: 6pt;
      }}
      .subhead {{
        font-size: 9pt;
        font-weight: 700;
        margin: 8pt 0 4pt;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      th, td {{
        padding: 4pt 5pt;
        border-bottom: 0.55pt solid #d7c8b6;
        vertical-align: top;
      }}
      th {{
        text-align: left;
        font-size: 8.2pt;
        color: #635548;
      }}
      td.numeric, th.numeric {{
        text-align: right;
        white-space: nowrap;
      }}
      .support-scenario th {{
        background: #f4ede5;
      }}
      .note-box {{
        background: #f9f4ee;
        border: 0.8pt solid #ccb8a4;
        padding: 8pt;
      }}
      .note-box ul {{
        margin: 4pt 0 0 14pt;
        padding: 0;
      }}
      .references {{
        margin-top: 6pt;
        padding-left: 16pt;
      }}
      .references li {{
        margin-bottom: 3pt;
      }}
      .references a {{
        color: #704f2e;
        text-decoration: none;
      }}
      .references a:hover {{
        text-decoration: underline;
      }}
      .muted {{
        color: #6d6157;
      }}
    </style>
  </head>
  <body>
    <header class="page-header">
      <h1>Canadian Support Calculator Report</h1>
      <div class="page-header__meta">
        <div>{escape(spousal_support['jurisdictionName'])} | Tax year {scenario['taxYear']} | Prepared {date.today().isoformat()}</div>
        <div class="muted">Layout inspired by DivorceMate-style working reports; values are produced by this calculator's own child-support, tax, benefit, and NDI models.</div>
      </div>
    </header>

    <section class="section">
      <h2>Calculation Input</h2>
      <div class="report-grid">
        <table>
          <thead>
            <tr><th>Scenario item</th><th class="numeric">Value</th></tr>
          </thead>
          <tbody>
            <tr><td>Jurisdiction</td><td class="numeric">{escape(spousal_support['jurisdictionName'])}</td></tr>
            <tr><td>Children</td><td class="numeric">{scenario['children']}</td></tr>
            <tr><td>Children under 6</td><td class="numeric">{scenario['childrenUnderSix']}</td></tr>
            <tr><td>Eligible dependant claimant</td><td class="numeric">{escape(spousal_support['eligibleDependantClaimant'].capitalize())}</td></tr>
            <tr><td>Tax year</td><td class="numeric">{scenario['taxYear']}</td></tr>
            <tr><td>Target recipient NDI range</td><td class="numeric">{_format_percent(spousal_support['targetRangePercent']['min'])} to {_format_percent(spousal_support['targetRangePercent']['max'])}</td></tr>
          </tbody>
        </table>
        <table>
          <thead>
            <tr><th>Party</th><th class="numeric">Gross income</th></tr>
          </thead>
          <tbody>
            <tr><td>Payor</td><td class="numeric">{_format_currency(spousal_support['payorIncome'])}</td></tr>
            <tr><td>Recipient</td><td class="numeric">{_format_currency(spousal_support['recipientIncome'])}</td></tr>
            <tr><td>Registered children for benefits</td><td class="numeric">Payor {spousal_support['payorRegisteredChildren']} | Recipient {spousal_support['recipientRegisteredChildren']}</td></tr>
            <tr><td>Household adults</td><td class="numeric">Payor {spousal_support['payorHouseholdAdults']} | Recipient {spousal_support['recipientHouseholdAdults']}</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <h2>Child Support Guidelines (CSG)</h2>
      <div class="subhead">Monthly table amounts with offset calculation</div>
      <p class="muted">Using {child_support['tableYear']} federal child support tables.</p>
      <table>
        <thead>
          <tr>
            <th>Party</th>
            <th class="numeric">Table income</th>
            <th class="numeric">Monthly</th>
            <th class="numeric">Annual</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Payor</td>
            <td class="numeric">{_format_currency(child_support['payorTableIncome'])}</td>
            <td class="numeric">{_format_currency(child_support['payorMonthly'])}</td>
            <td class="numeric">{_format_currency(child_support['payorAnnual'])}</td>
          </tr>
          <tr>
            <td>Recipient</td>
            <td class="numeric">{_format_currency(child_support['recipientTableIncome'])}</td>
            <td class="numeric">{_format_currency(child_support['recipientMonthly'])}</td>
            <td class="numeric">{_format_currency(child_support['recipientAnnual'])}</td>
          </tr>
          <tr>
            <td>Guideline net transfer</td>
            <td class="numeric"></td>
            <td class="numeric">{_format_currency(child_support['guidelineNetMonthly'])}</td>
            <td class="numeric">{_format_currency(child_support['guidelineNetAnnual'])}</td>
          </tr>
          <tr>
            <td><strong>Applied net transfer</strong></td>
            <td class="numeric"></td>
            <td class="numeric"><strong>{_format_currency(child_support['netMonthly'])}</strong></td>
            <td class="numeric"><strong>{_format_currency(child_support['netAnnual'])}</strong></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Spousal Support Advisory Guidelines (SSAG)</h2>
      <div class="report-grid">
        <table>
          <tbody>
            <tr><th>Estimated monthly spousal support</th><td class="numeric">{_format_currency(spousal_support['estimatedSpousalSupportMonthly'])}</td></tr>
            <tr><th>Estimated annual spousal support</th><td class="numeric">{_format_currency(spousal_support['estimatedSpousalSupportAnnual'])}</td></tr>
            <tr><th>Low / Mid / High monthly</th><td class="numeric">{_format_currency(spousal_support['spousalSupportRange']['lowMonthly'])} / {_format_currency(spousal_support['spousalSupportRange']['midMonthly'])} / {_format_currency(spousal_support['spousalSupportRange']['highMonthly'])}</td></tr>
            <tr><th>Formula recipient share</th><td class="numeric">{_format_percent(spousal_support['recipientSharePercent'])}</td></tr>
            <tr><th>Actual recipient share</th><td class="numeric">{_format_percent(spousal_support['actualRecipientSharePercent'])}</td></tr>
            <tr><th>Duration</th><td class="numeric">{
                "Indefinite"
                + (
                    ""
                    if not spousal_support["duration"]["inputsProvided"]
                    else f" | Min {spousal_support['duration']['minYears']:.2f} years | Max {spousal_support['duration']['maxYears']:.2f} years"
                )
            }</td></tr>
            <tr><th>Iterations</th><td class="numeric">{spousal_support['iterations']}</td></tr>
          </tbody>
        </table>
        <div class="note-box">
          <strong>Cautions / Overrides</strong>
          {"<ul>" + "".join(f"<li>{escape(note)}</li>" for note in notes) + "</ul>" if notes else "<p class='muted'>No special spousal-only incomes or fixed-support override were provided.</p>"}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Assumptions and Overrides</h2>
      <div class="report-grid">
        <table>
          <thead>
            <tr><th>Assumption</th><th class="numeric">Value</th></tr>
          </thead>
          <tbody>
            {_render_key_value_rows(assumption_rows)}
          </tbody>
        </table>
        <table>
          <thead>
            <tr><th>Override / Trace</th><th class="numeric">Value</th></tr>
          </thead>
          <tbody>
            {_render_key_value_rows(override_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <h2>Tax and Payroll Detail</h2>
      <table>
        <thead>
          <tr>
            <th>Line item</th>
            <th class="numeric">Payor Annual</th>
            <th class="numeric">Recipient Annual</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Income tax after credits</td>
            <td class="numeric">{_format_currency(-payor_tax_profile['incomeTax'])}</td>
            <td class="numeric">{_format_currency(-recipient_tax_profile['incomeTax'])}</td>
          </tr>
          <tr>
            <td>Eligible dependant credit</td>
            <td class="numeric">{_format_currency(payor_tax_profile['federalEligibleDependantCredit'] + payor_tax_profile['provincialEligibleDependantCredit'])}</td>
            <td class="numeric">{_format_currency(recipient_tax_profile['federalEligibleDependantCredit'] + recipient_tax_profile['provincialEligibleDependantCredit'])}</td>
          </tr>
          <tr>
            <td>CPP contributions</td>
            <td class="numeric">{_format_currency(-payor_tax_profile['totalCppContribution'])}</td>
            <td class="numeric">{_format_currency(-recipient_tax_profile['totalCppContribution'])}</td>
          </tr>
          <tr>
            <td>EI premiums</td>
            <td class="numeric">{_format_currency(-payor_tax_profile['eiPremium'])}</td>
            <td class="numeric">{_format_currency(-recipient_tax_profile['eiPremium'])}</td>
          </tr>
          <tr>
            <td><strong>Total deductions</strong></td>
            <td class="numeric"><strong>{_format_currency(-payor_tax_profile['totalDeductions'])}</strong></td>
            <td class="numeric"><strong>{_format_currency(-recipient_tax_profile['totalDeductions'])}</strong></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Benefits Detail</h2>
      <table>
        <thead>
          <tr>
            <th>Line item</th>
            <th class="numeric">Payor Annual</th>
            <th class="numeric">Recipient Annual</th>
          </tr>
        </thead>
        <tbody>
          {benefit_rows}
          <tr>
            <td><strong>Total modeled benefits</strong></td>
            <td class="numeric"><strong>{_format_currency(payor_benefits)}</strong></td>
            <td class="numeric"><strong>{_format_currency(recipient_benefits)}</strong></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Support Scenario</h2>
      <table class="support-scenario">
        <thead>
          <tr>
            <th></th>
            <th class="numeric">Payor Monthly</th>
            <th class="numeric">Recipient Monthly</th>
            <th class="numeric">Payor Annual</th>
            <th class="numeric">Recipient Annual</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Gross Income</td>
            <td class="numeric">{_format_monthly(spousal_support['payorIncome'])}</td>
            <td class="numeric">{_format_monthly(spousal_support['recipientIncome'])}</td>
            <td class="numeric">{_format_currency(spousal_support['payorIncome'])}</td>
            <td class="numeric">{_format_currency(spousal_support['recipientIncome'])}</td>
          </tr>
          <tr>
            <td>Income Tax</td>
            <td class="numeric">{_format_monthly(-payor_tax_profile['incomeTax'])}</td>
            <td class="numeric">{_format_monthly(-recipient_tax_profile['incomeTax'])}</td>
            <td class="numeric">{_format_currency(-payor_tax_profile['incomeTax'])}</td>
            <td class="numeric">{_format_currency(-recipient_tax_profile['incomeTax'])}</td>
          </tr>
          <tr>
            <td>CPP and EI</td>
            <td class="numeric">{_format_monthly(-payor_tax_profile['payrollDeductions'])}</td>
            <td class="numeric">{_format_monthly(-recipient_tax_profile['payrollDeductions'])}</td>
            <td class="numeric">{_format_currency(-payor_tax_profile['payrollDeductions'])}</td>
            <td class="numeric">{_format_currency(-recipient_tax_profile['payrollDeductions'])}</td>
          </tr>
          <tr>
            <td>Benefits and Credits</td>
            <td class="numeric">{_format_monthly(payor_benefits)}</td>
            <td class="numeric">{_format_monthly(recipient_benefits)}</td>
            <td class="numeric">{_format_currency(payor_benefits)}</td>
            <td class="numeric">{_format_currency(recipient_benefits)}</td>
          </tr>
          <tr>
            <td>Spousal Support</td>
            <td class="numeric">{_format_monthly(-spousal_support['estimatedSpousalSupportAnnual'])}</td>
            <td class="numeric">{_format_monthly(spousal_support['estimatedSpousalSupportAnnual'])}</td>
            <td class="numeric">{_format_currency(-spousal_support['estimatedSpousalSupportAnnual'])}</td>
            <td class="numeric">{_format_currency(spousal_support['estimatedSpousalSupportAnnual'])}</td>
          </tr>
          <tr>
            <td>Child Support (Table)</td>
            <td class="numeric">{_format_monthly(-child_support['netAnnual'])}</td>
            <td class="numeric">{_format_monthly(child_support['netAnnual'])}</td>
            <td class="numeric">{_format_currency(-child_support['netAnnual'])}</td>
            <td class="numeric">{_format_currency(child_support['netAnnual'])}</td>
          </tr>
          <tr>
            <td><strong>Net Disposable Income (NDI)</strong></td>
            <td class="numeric"><strong>{_format_monthly(spousal_support['ndiPayor'])}</strong></td>
            <td class="numeric"><strong>{_format_monthly(spousal_support['ndiRecipient'])}</strong></td>
            <td class="numeric"><strong>{_format_currency(spousal_support['ndiPayor'])}</strong></td>
            <td class="numeric"><strong>{_format_currency(spousal_support['ndiRecipient'])}</strong></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Source Data</h2>
      <ol class="references">
        {_render_reference_list(source_references)}
      </ol>
    </section>
  </body>
</html>
"""

    pdf_bytes = HTML(string=html).write_pdf()
    logger.info("Rendered PDF report with %s bytes.", len(pdf_bytes))
    return pdf_bytes
