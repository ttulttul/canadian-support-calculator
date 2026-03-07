import logging

from .calculations import calculate_child_support_breakdown
from .tables import ChildSupportTable, load_default_child_support_table
from .tax import calculate_bc_tax_approx

logger = logging.getLogger(__name__)


def calculate_spousal_support_estimate(
    *,
    payor_income: float,
    recipient_income: float,
    num_children: int,
    tax_year: int,
    target_range: tuple[float, float] = (0.40, 0.46),
    max_iterations: int = 300,
    step: float = 500.0,
    tolerance: float = 0.5,
    table: ChildSupportTable | None = None,
) -> dict:
    if payor_income < 0 or recipient_income < 0:
        raise ValueError("Income values must be zero or greater.")

    target_min, target_max = target_range
    if not 0 < target_min < target_max < 1:
        raise ValueError("Target range must be between 0 and 1.")

    active_table = table or load_default_child_support_table()
    child_support = calculate_child_support_breakdown(
        num_children=num_children,
        payor_income=payor_income,
        recipient_income=recipient_income,
        table=active_table,
    )
    net_child_support_annual = child_support["netAnnual"]
    target_min_percent = target_min * 100.0
    target_max_percent = target_max * 100.0
    target_midpoint = (target_min_percent + target_max_percent) / 2.0

    logger.info(
        "Starting spousal support estimate: payor=%s recipient=%s children=%s",
        payor_income,
        recipient_income,
        num_children,
    )

    spousal_support_annual = 0.0
    history: list[dict] = []

    for iteration in range(max_iterations):
        current_payor_income = max(payor_income - spousal_support_annual, 0.0)
        current_recipient_income = recipient_income + spousal_support_annual
        payor_tax = calculate_bc_tax_approx(current_payor_income, tax_year=tax_year)
        recipient_tax = calculate_bc_tax_approx(current_recipient_income, tax_year=tax_year)

        ndi_payor = payor_income - payor_tax - spousal_support_annual - net_child_support_annual
        ndi_recipient = (
            recipient_income
            - recipient_tax
            + spousal_support_annual
            + net_child_support_annual
        )
        total_ndi = ndi_payor + ndi_recipient
        recipient_share = 50.0 if total_ndi <= 0 else (ndi_recipient / total_ndi) * 100.0

        snapshot = {
            "iteration": iteration,
            "spousalSupportAnnual": round(spousal_support_annual, 2),
            "netChildSupportAnnual": round(net_child_support_annual, 2),
            "ndiPayor": round(ndi_payor, 2),
            "ndiRecipient": round(ndi_recipient, 2),
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
                (previous_share - target_midpoint) * (recipient_share - target_midpoint)
            ) < 0
            if crossed_midpoint or inside_band:
                step = max(1.0, step / 2.0)
    else:
        logger.warning("Maximum iterations reached before convergence.")

    final_snapshot = history[-1]
    return {
        "jurisdiction": "BC",
        "children": num_children,
        "taxYear": tax_year,
        "payorIncome": payor_income,
        "recipientIncome": recipient_income,
        "targetRangePercent": {
            "min": round(target_min_percent, 2),
            "max": round(target_max_percent, 2),
        },
        "estimatedSpousalSupportAnnual": final_snapshot["spousalSupportAnnual"],
        "estimatedSpousalSupportMonthly": round(
            final_snapshot["spousalSupportAnnual"] / 12.0,
            2,
        ),
        "childSupport": child_support,
        "ndiPayor": final_snapshot["ndiPayor"],
        "ndiRecipient": final_snapshot["ndiRecipient"],
        "recipientSharePercent": final_snapshot["recipientSharePercent"],
        "iterations": len(history),
        "history": history,
    }
