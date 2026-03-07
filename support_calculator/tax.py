import logging

logger = logging.getLogger(__name__)
BASE_TAX_YEAR = 2023
DEFAULT_TAX_YEAR = 2023
DEFAULT_EXTRAPOLATION_RATE = 0.025

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

KNOWN_TAX_YEAR_INDEX_FACTORS = {
    2017: 45_916 / 53_359,
    2018: 46_605 / 53_359,
    2019: 47_630 / 53_359,
    2020: 48_535 / 53_359,
    2021: 49_020 / 53_359,
    2022: 50_197 / 53_359,
    2023: 1.0,
    2024: 55_867 / 53_359,
    2025: 57_375 / 53_359,
}


def resolve_tax_year_index_factor(tax_year: int) -> float:
    if tax_year in KNOWN_TAX_YEAR_INDEX_FACTORS:
        return KNOWN_TAX_YEAR_INDEX_FACTORS[tax_year]

    min_year = min(KNOWN_TAX_YEAR_INDEX_FACTORS)
    max_year = max(KNOWN_TAX_YEAR_INDEX_FACTORS)
    if tax_year < min_year:
        years = min_year - tax_year
        return KNOWN_TAX_YEAR_INDEX_FACTORS[min_year] / ((1 + DEFAULT_EXTRAPOLATION_RATE) ** years)

    years = tax_year - max_year
    return KNOWN_TAX_YEAR_INDEX_FACTORS[max_year] * ((1 + DEFAULT_EXTRAPOLATION_RATE) ** years)


def indexed_tax_brackets(tax_year: int) -> tuple[tuple[float, float, float], ...]:
    factor = resolve_tax_year_index_factor(tax_year)
    indexed_brackets = []
    for lower, upper, rate in BC_COMBINED_APPROX_TAX_BRACKETS_2023:
        indexed_lower = round(lower * factor, 2)
        indexed_upper = float("inf") if upper == float("inf") else round(upper * factor, 2)
        indexed_brackets.append((indexed_lower, indexed_upper, rate))

    logger.debug("Built indexed tax brackets for tax year %s with factor %s", tax_year, factor)
    return tuple(indexed_brackets)


def calculate_bc_tax_approx(income: float, tax_year: int = DEFAULT_TAX_YEAR) -> float:
    normalized_income = max(income, 0.0)
    tax = 0.0
    for lower, upper, rate in indexed_tax_brackets(tax_year):
        if normalized_income <= lower:
            break

        taxable_amount = min(normalized_income, upper) - lower
        tax += taxable_amount * rate / 100.0

    logger.debug(
        "Calculated approximate BC tax: income=%s tax_year=%s tax=%s",
        income,
        tax_year,
        tax,
    )
    return round(tax, 2)
