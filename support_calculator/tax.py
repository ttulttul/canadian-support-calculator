import logging

logger = logging.getLogger(__name__)

BC_COMBINED_APPROX_TAX_BRACKETS_2023 = (
    (0, 45654, 20.06),
    (45654, 53359, 22.70),
    (53359, 91310, 28.20),
    (91310, 104835, 31.00),
    (104835, 106717, 32.79),
    (106717, 127299, 38.29),
    (127299, 165430, 40.70),
    (165430, 172602, 44.02),
    (172602, 235675, 46.12),
    (235675, 240716, 49.80),
    (240716, float("inf"), 53.50),
)


def calculate_bc_tax_approx(income: float) -> float:
    normalized_income = max(income, 0.0)
    tax = 0.0
    for lower, upper, rate in BC_COMBINED_APPROX_TAX_BRACKETS_2023:
        if normalized_income <= lower:
            break

        taxable_amount = min(normalized_income, upper) - lower
        tax += taxable_amount * rate / 100.0

    logger.debug("Calculated approximate BC tax: income=%s tax=%s", income, tax)
    return round(tax, 2)
