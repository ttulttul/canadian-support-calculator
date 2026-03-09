import logging

from .tables import ChildSupportTable, load_default_child_support_table

logger = logging.getLogger(__name__)


def calculate_child_support_breakdown(
    *,
    num_children: int,
    payor_income: float,
    recipient_income: float,
    net_monthly_override: float | None = None,
    table: ChildSupportTable | None = None,
) -> dict:
    if num_children <= 0:
        raise ValueError("Number of children must be greater than zero.")

    if payor_income < 0 or recipient_income < 0:
        raise ValueError("Income values must be zero or greater.")

    active_table = table or load_default_child_support_table()
    payor_table_income = active_table.rounded_income(payor_income)
    recipient_table_income = active_table.rounded_income(recipient_income)
    payor_monthly = active_table.amount(num_children, payor_income)
    recipient_monthly = active_table.amount(num_children, recipient_income)
    guideline_net_monthly = round(payor_monthly - recipient_monthly, 2)
    net_monthly = guideline_net_monthly if net_monthly_override is None else round(
        net_monthly_override,
        2,
    )
    direction = "none"
    if net_monthly > 0:
        direction = "payor_to_recipient"
    elif net_monthly < 0:
        direction = "recipient_to_payor"

    logger.debug(
        "Child support breakdown calculated: jurisdiction=%s children=%s payor=%s recipient=%s net=%s",
        active_table.jurisdiction_code,
        num_children,
        payor_income,
        recipient_income,
        net_monthly,
    )
    return {
        "jurisdiction": active_table.jurisdiction_code,
        "jurisdictionName": active_table.jurisdiction_name,
        "children": num_children,
        "payorIncome": payor_income,
        "recipientIncome": recipient_income,
        "tableYear": active_table.table_year,
        "payorTableIncome": payor_table_income,
        "recipientTableIncome": recipient_table_income,
        "payorMonthly": payor_monthly,
        "recipientMonthly": recipient_monthly,
        "guidelineNetMonthly": guideline_net_monthly,
        "netMonthly": net_monthly,
        "payorAnnual": round(payor_monthly * 12, 2),
        "recipientAnnual": round(recipient_monthly * 12, 2),
        "guidelineNetAnnual": round(guideline_net_monthly * 12, 2),
        "overrideApplied": net_monthly_override is not None,
        "overrideMonthly": None if net_monthly_override is None else round(net_monthly_override, 2),
        "overrideAnnual": (
            None
            if net_monthly_override is None
            else round(net_monthly_override * 12, 2)
        ),
        "netAnnual": round(net_monthly * 12, 2),
        "direction": direction,
    }
