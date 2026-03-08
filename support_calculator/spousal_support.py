import logging

from .benefits import calculate_shared_custody_benefits
from .calculations import calculate_child_support_breakdown
from .tables import ChildSupportTable, load_default_child_support_table
from .tax import calculate_equivalent_before_tax_income, calculate_tax_approx

logger = logging.getLogger(__name__)


def calculate_spousal_support_estimate(
    *,
    payor_income: float,
    recipient_income: float,
    payor_spousal_income: float | None = None,
    recipient_spousal_income: float | None = None,
    fixed_total_support_annual: float | None = None,
    num_children: int,
    tax_year: int,
    children_under_six: int = 0,
    target_range: tuple[float, float] = (0.40, 0.46),
    max_iterations: int = 300,
    step: float = 500.0,
    tolerance: float = 0.5,
    table: ChildSupportTable | None = None,
) -> dict:
    if payor_income < 0 or recipient_income < 0:
        raise ValueError("Income values must be zero or greater.")

    if children_under_six < 0 or children_under_six > num_children:
        raise ValueError("'childrenUnderSix' must be between zero and the total number of children.")

    target_min, target_max = target_range
    if not 0 < target_min < target_max < 1:
        raise ValueError("Target range must be between 0 and 1.")

    active_table = table or load_default_child_support_table()
    jurisdiction_code = active_table.jurisdiction_code
    active_payor_spousal_income = (
        payor_income if payor_spousal_income is None else payor_spousal_income
    )
    active_recipient_spousal_income = (
        recipient_income
        if recipient_spousal_income is None
        else recipient_spousal_income
    )
    child_support = calculate_child_support_breakdown(
        num_children=num_children,
        payor_income=payor_income,
        recipient_income=recipient_income,
        table=active_table,
    )
    ndi_child_support = calculate_child_support_breakdown(
        num_children=num_children,
        payor_income=active_payor_spousal_income,
        recipient_income=active_recipient_spousal_income,
        table=active_table,
    )
    actual_net_child_support_annual = child_support["netAnnual"]
    ndi_net_child_support_annual = ndi_child_support["netAnnual"]
    target_min_percent = target_min * 100.0
    target_max_percent = target_max * 100.0
    target_midpoint = (target_min_percent + target_max_percent) / 2.0

    logger.info(
        "Starting spousal support estimate: payor=%s recipient=%s spousal_payor=%s spousal_recipient=%s children=%s",
        payor_income,
        recipient_income,
        active_payor_spousal_income,
        active_recipient_spousal_income,
        num_children,
    )

    def calculate_financial_state(
        *,
        spousal_support_annual: float,
        net_child_support_annual: float,
    ) -> dict:
        current_payor_taxable_income = max(payor_income - spousal_support_annual, 0.0)
        current_recipient_taxable_income = recipient_income + spousal_support_annual
        payor_tax = calculate_tax_approx(
            current_payor_taxable_income,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
        )
        recipient_tax = calculate_tax_approx(
            current_recipient_taxable_income,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
        )
        benefits = calculate_shared_custody_benefits(
            jurisdiction_code=jurisdiction_code,
            payor_adjusted_family_net_income=current_payor_taxable_income,
            recipient_adjusted_family_net_income=current_recipient_taxable_income,
            num_children=num_children,
            children_under_six=children_under_six,
            tax_year=tax_year,
        )
        payor_benefits = benefits["payor"]["totalAnnual"]
        recipient_benefits = benefits["recipient"]["totalAnnual"]

        ndi_payor = (
            active_payor_spousal_income
            - payor_tax
            - spousal_support_annual
            - net_child_support_annual
            + payor_benefits
        )
        ndi_recipient = (
            active_recipient_spousal_income
            - recipient_tax
            + spousal_support_annual
            + net_child_support_annual
            + recipient_benefits
        )
        total_ndi = ndi_payor + ndi_recipient
        recipient_share = 50.0 if total_ndi <= 0 else (ndi_recipient / total_ndi) * 100.0

        return {
            "payorTaxableIncome": current_payor_taxable_income,
            "recipientTaxableIncome": current_recipient_taxable_income,
            "payorTax": payor_tax,
            "recipientTax": recipient_tax,
            "benefits": benefits,
            "payorBenefitsAnnual": payor_benefits,
            "recipientBenefitsAnnual": recipient_benefits,
            "ndiPayor": ndi_payor,
            "ndiRecipient": ndi_recipient,
            "recipientSharePercent": recipient_share,
        }

    spousal_support_annual = 0.0
    history: list[dict] = []

    if fixed_total_support_annual is None:
        for iteration in range(max_iterations):
            financial_state = calculate_financial_state(
                spousal_support_annual=spousal_support_annual,
                net_child_support_annual=ndi_net_child_support_annual,
            )
            recipient_share = financial_state["recipientSharePercent"]

            snapshot = {
                "iteration": iteration,
                "spousalSupportAnnual": round(spousal_support_annual, 2),
                "netChildSupportAnnual": round(ndi_net_child_support_annual, 2),
                "payorBenefitsAnnual": round(financial_state["payorBenefitsAnnual"], 2),
                "recipientBenefitsAnnual": round(
                    financial_state["recipientBenefitsAnnual"], 2
                ),
                "ndiPayor": round(financial_state["ndiPayor"], 2),
                "ndiRecipient": round(financial_state["ndiRecipient"], 2),
                "recipientSharePercent": round(recipient_share, 2),
                "step": round(step, 2),
            }
            history.append(snapshot)
            logger.debug("Spousal support iteration: %s", snapshot)

            inside_band = target_min_percent <= recipient_share <= target_max_percent
            close_to_midpoint = abs(recipient_share - target_midpoint) <= tolerance
            if inside_band and (close_to_midpoint or step <= 1.0):
                logger.info("Spousal support estimate converged at iteration %s.", iteration)
                break

            if recipient_share < target_min_percent:
                spousal_support_annual += step
            else:
                spousal_support_annual = max(spousal_support_annual - step, 0.0)

            if len(history) > 1:
                previous_share = history[-2]["recipientSharePercent"]
                crossed_midpoint = (
                    (previous_share - target_midpoint)
                    * (recipient_share - target_midpoint)
                ) < 0
                if crossed_midpoint or inside_band:
                    step = max(1.0, step / 2.0)
        else:
            logger.warning("Maximum iterations reached before convergence.")

        final_snapshot = history[-1]
        estimated_spousal_support_annual = final_snapshot["spousalSupportAnnual"]
        final_financial_state = calculate_financial_state(
            spousal_support_annual=estimated_spousal_support_annual,
            net_child_support_annual=ndi_net_child_support_annual,
        )
    else:
        if fixed_total_support_annual < actual_net_child_support_annual:
            raise ValueError(
                "'fixedTotalSupportAnnual' must be at least the actual annual child support amount."
            )

        logger.info(
            "Using fixed total support override: total=%s actual_child_support=%s",
            fixed_total_support_annual,
            actual_net_child_support_annual,
        )
        ndi_child_support = child_support
        ndi_net_child_support_annual = actual_net_child_support_annual
        estimated_spousal_support_annual = (
            fixed_total_support_annual - actual_net_child_support_annual
        )
        final_financial_state = calculate_financial_state(
            spousal_support_annual=estimated_spousal_support_annual,
            net_child_support_annual=ndi_net_child_support_annual,
        )
        final_snapshot = {
            "iteration": 0,
            "spousalSupportAnnual": round(estimated_spousal_support_annual, 2),
            "netChildSupportAnnual": round(ndi_net_child_support_annual, 2),
            "payorBenefitsAnnual": round(final_financial_state["payorBenefitsAnnual"], 2),
            "recipientBenefitsAnnual": round(
                final_financial_state["recipientBenefitsAnnual"], 2
            ),
            "ndiPayor": round(final_financial_state["ndiPayor"], 2),
            "ndiRecipient": round(final_financial_state["ndiRecipient"], 2),
            "recipientSharePercent": round(
                final_financial_state["recipientSharePercent"], 2
            ),
            "step": 0.0,
        }
        history.append(final_snapshot)

    payor_tax_before_support_deduction = calculate_tax_approx(
        payor_income,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
    )
    recipient_tax_before_support_inclusion = calculate_tax_approx(
        recipient_income,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
    )
    payor_taxable_income = final_financial_state["payorTaxableIncome"]
    recipient_taxable_income = final_financial_state["recipientTaxableIncome"]
    payor_tax = final_financial_state["payorTax"]
    recipient_tax = final_financial_state["recipientTax"]
    benefits = final_financial_state["benefits"]
    payor_tax_deduction_benefit = max(payor_tax_before_support_deduction - payor_tax, 0.0)
    recipient_tax_support_cost = max(recipient_tax - recipient_tax_before_support_inclusion, 0.0)
    actual_net_income_payor = (
        payor_income
        - payor_tax
        - estimated_spousal_support_annual
        - actual_net_child_support_annual
        + benefits["payor"]["totalAnnual"]
    )
    actual_net_income_recipient = (
        recipient_income
        - recipient_tax
        + estimated_spousal_support_annual
        + actual_net_child_support_annual
        + benefits["recipient"]["totalAnnual"]
    )
    payor_equivalent_before_tax_income = calculate_equivalent_before_tax_income(
        actual_net_income_payor,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
    )
    recipient_equivalent_before_tax_income = calculate_equivalent_before_tax_income(
        actual_net_income_recipient,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
    )
    return {
        "jurisdiction": active_table.jurisdiction_code,
        "jurisdictionName": active_table.jurisdiction_name,
        "children": num_children,
        "childrenUnderSix": children_under_six,
        "taxYear": tax_year,
        "payorIncome": payor_income,
        "recipientIncome": recipient_income,
        "payorSpousalIncome": active_payor_spousal_income,
        "recipientSpousalIncome": active_recipient_spousal_income,
        "fixedTotalSupportAnnual": (
            None if fixed_total_support_annual is None else round(fixed_total_support_annual, 2)
        ),
        "targetRangePercent": {
            "min": round(target_min_percent, 2),
            "max": round(target_max_percent, 2),
        },
        "estimatedSpousalSupportAnnual": estimated_spousal_support_annual,
        "estimatedSpousalSupportMonthly": round(
            estimated_spousal_support_annual / 12.0,
            2,
        ),
        "childSupport": child_support,
        "ndiChildSupport": ndi_child_support,
        "payorTaxableIncome": round(payor_taxable_income, 2),
        "recipientTaxableIncome": round(recipient_taxable_income, 2),
        "payorTaxBeforeSupportDeduction": round(payor_tax_before_support_deduction, 2),
        "payorTax": round(payor_tax, 2),
        "payorTaxDeductionBenefit": round(payor_tax_deduction_benefit, 2),
        "recipientTaxBeforeSupportInclusion": round(recipient_tax_before_support_inclusion, 2),
        "recipientTax": round(recipient_tax, 2),
        "recipientTaxSupportCost": round(recipient_tax_support_cost, 2),
        "benefits": benefits,
        "actualNetIncomePayor": round(actual_net_income_payor, 2),
        "actualNetIncomeRecipient": round(actual_net_income_recipient, 2),
        "payorEquivalentBeforeTaxIncome": round(payor_equivalent_before_tax_income, 2),
        "recipientEquivalentBeforeTaxIncome": round(
            recipient_equivalent_before_tax_income, 2
        ),
        "ndiPayor": final_snapshot["ndiPayor"],
        "ndiRecipient": final_snapshot["ndiRecipient"],
        "recipientSharePercent": final_snapshot["recipientSharePercent"],
        "iterations": len(history),
        "history": history,
    }
