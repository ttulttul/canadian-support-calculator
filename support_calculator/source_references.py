import logging

logger = logging.getLogger(__name__)

CALCULATION_SOURCE_REFERENCES = [
    {
        "key": "childSupportTables",
        "label": "Justice Canada Federal Child Support Tables",
        "url": "https://www.justice.gc.ca/eng/fl-df/child-enfant/fcsg-lfpae/2025/index.html",
    },
    {
        "key": "taxRates",
        "label": "CRA payroll deductions formulas and tax brackets",
        "url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/payroll-deductions-t4127-payroll-deductions-formulas/t4127-jan/t4127-jan-payroll-deductions-formulas-computer-programs.html",
    },
    {
        "key": "canadaChildBenefitAnnual",
        "label": "Canada child benefit overview",
        "url": "https://www.canada.ca/en/revenue-agency/services/child-family-benefits/canada-child-benefit-overview.html",
    },
    {
        "key": "gstHstCreditAnnual",
        "label": "GST/HST credit eligibility",
        "url": "https://www.canada.ca/en/revenue-agency/services/child-family-benefits/gsthstc-eligibility.html",
    },
    {
        "key": "bcFamilyBenefitAnnual",
        "label": "B.C. family benefit",
        "url": "https://www2.gov.bc.ca/gov/content/taxes/income-taxes/personal/credits/bc-family-benefit",
    },
    {
        "key": "bcClimateActionCreditAnnual",
        "label": "B.C. climate action tax credit",
        "url": "https://www2.gov.bc.ca/gov/content/taxes/income-taxes/personal/credits/climate-action",
    },
]


def filter_source_references(
    *,
    has_child_support: bool,
    has_spousal_support: bool,
    benefit_line_items: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    benefit_keys = {item["key"] for item in benefit_line_items or []}
    filtered_references = []
    for reference in CALCULATION_SOURCE_REFERENCES:
        if reference["key"] == "childSupportTables" and not has_child_support:
            continue
        if reference["key"] == "taxRates" and not has_spousal_support:
            continue
        if reference["key"] not in {"childSupportTables", "taxRates"} and reference["key"] not in benefit_keys:
            continue
        filtered_references.append(reference)

    logger.debug(
        "Filtered source references: child=%s spousal=%s benefits=%s count=%s",
        has_child_support,
        has_spousal_support,
        sorted(benefit_keys),
        len(filtered_references),
    )
    return filtered_references
