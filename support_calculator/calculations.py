import logging

from .tables import ChildSupportTable, load_default_child_support_table

logger = logging.getLogger(__name__)


def calculate_child_support_breakdown(
    *,
    num_children: int,
    payor_income: float,
    recipient_income: float,
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
    net_monthly = round(payor_monthly - recipient_monthly, 2)
    direction = "none"
    if net_monthly > 0:
        direction = "payor_to_recipient"
    elif net_monthly < 0:
        direction = "recipient_to_payor"

    logger.debug(
        "Child support breakdown calculated: children=%s payor=%s recipient=%s net=%s",
        num_children,
        payor_income,
        recipient_income,
        net_monthly,
    )
    return {
        "jurisdiction": "BC",
        "children": num_children,
        "payorIncome": payor_income,
        "recipientIncome": recipient_income,
        "payorTableIncome": payor_table_income,
        "recipientTableIncome": recipient_table_income,
        "payorMonthly": payor_monthly,
        "recipientMonthly": recipient_monthly,
        "netMonthly": net_monthly,
        "payorAnnual": round(payor_monthly * 12, 2),
        "recipientAnnual": round(recipient_monthly * 12, 2),
        "netAnnual": round(net_monthly * 12, 2),
        "direction": direction,
    }
