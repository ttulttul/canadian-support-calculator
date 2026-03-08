import logging

logger = logging.getLogger(__name__)

BASE_TAX_YEAR = 2023
DEFAULT_TAX_YEAR = 2023
DEFAULT_EXTRAPOLATION_RATE = 0.025

FEDERAL_TAX_BRACKETS_2023 = (
    (0.0, 53_359.0, 15.0),
    (53_359.0, 106_717.0, 20.5),
    (106_717.0, 165_430.0, 26.0),
    (165_430.0, 235_675.0, 29.0),
    (235_675.0, float("inf"), 33.0),
)

PROVINCIAL_TAX_BRACKETS_2023 = {
    "AB": (
        (0.0, 142_292.0, 10.0),
        (142_292.0, 170_751.0, 12.0),
        (170_751.0, 227_668.0, 13.0),
        (227_668.0, 341_502.0, 14.0),
        (341_502.0, float("inf"), 15.0),
    ),
    "BC": (
        (0.0, 45_654.0, 5.06),
        (45_654.0, 91_310.0, 7.70),
        (91_310.0, 104_835.0, 10.50),
        (104_835.0, 127_299.0, 12.29),
        (127_299.0, 172_602.0, 14.70),
        (172_602.0, 240_716.0, 16.80),
        (240_716.0, float("inf"), 20.50),
    ),
    "MB": (
        (0.0, 47_000.0, 10.80),
        (47_000.0, 100_000.0, 12.75),
        (100_000.0, float("inf"), 17.40),
    ),
    "NB": (
        (0.0, 47_715.0, 9.40),
        (47_715.0, 95_431.0, 14.00),
        (95_431.0, 176_756.0, 16.00),
        (176_756.0, float("inf"), 19.50),
    ),
    "NL": (
        (0.0, 41_457.0, 8.70),
        (41_457.0, 82_913.0, 14.50),
        (82_913.0, 148_027.0, 15.80),
        (148_027.0, 207_239.0, 17.80),
        (207_239.0, 264_750.0, 19.80),
        (264_750.0, 529_500.0, 20.80),
        (529_500.0, float("inf"), 21.30),
    ),
    "NS": (
        (0.0, 29_590.0, 8.79),
        (29_590.0, 59_180.0, 14.95),
        (59_180.0, 93_000.0, 16.67),
        (93_000.0, 150_000.0, 17.50),
        (150_000.0, float("inf"), 21.00),
    ),
    "NT": (
        (0.0, 48_326.0, 5.90),
        (48_326.0, 96_655.0, 8.60),
        (96_655.0, 157_139.0, 12.20),
        (157_139.0, float("inf"), 14.05),
    ),
    "NU": (
        (0.0, 53_268.0, 4.00),
        (53_268.0, 106_537.0, 7.00),
        (106_537.0, 173_205.0, 9.00),
        (173_205.0, float("inf"), 11.50),
    ),
    "ON": (
        (0.0, 49_231.0, 5.05),
        (49_231.0, 98_463.0, 9.15),
        (98_463.0, 150_000.0, 11.16),
        (150_000.0, 220_000.0, 12.16),
        (220_000.0, float("inf"), 13.16),
    ),
    "PE": (
        (0.0, 31_984.0, 9.80),
        (31_984.0, 63_969.0, 13.80),
        (63_969.0, float("inf"), 16.70),
    ),
    "SK": (
        (0.0, 49_720.0, 10.50),
        (49_720.0, 142_058.0, 12.50),
        (142_058.0, float("inf"), 14.50),
    ),
    "YT": (
        (0.0, 53_359.0, 6.40),
        (53_359.0, 106_717.0, 9.00),
        (106_717.0, 165_430.0, 10.90),
        (165_430.0, 500_000.0, 12.80),
        (500_000.0, float("inf"), 15.00),
    ),
}

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
        return KNOWN_TAX_YEAR_INDEX_FACTORS[min_year] / (
            (1 + DEFAULT_EXTRAPOLATION_RATE) ** years
        )

    years = tax_year - max_year
    return KNOWN_TAX_YEAR_INDEX_FACTORS[max_year] * (
        (1 + DEFAULT_EXTRAPOLATION_RATE) ** years
    )


def _normalize_jurisdiction_code(jurisdiction_code: str) -> str:
    normalized_code = str(jurisdiction_code or "BC").upper()
    if normalized_code not in PROVINCIAL_TAX_BRACKETS_2023:
        raise ValueError(f"Unsupported jurisdiction code '{jurisdiction_code}'.")
    return normalized_code


def _index_brackets(
    brackets: tuple[tuple[float, float, float], ...],
    *,
    tax_year: int,
) -> tuple[tuple[float, float, float], ...]:
    factor = resolve_tax_year_index_factor(tax_year)
    indexed_brackets = []
    for lower, upper, rate in brackets:
        indexed_lower = round(lower * factor, 2)
        indexed_upper = (
            float("inf") if upper == float("inf") else round(upper * factor, 2)
        )
        indexed_brackets.append((indexed_lower, indexed_upper, rate))

    return tuple(indexed_brackets)


def indexed_federal_tax_brackets(
    tax_year: int,
) -> tuple[tuple[float, float, float], ...]:
    brackets = _index_brackets(FEDERAL_TAX_BRACKETS_2023, tax_year=tax_year)
    logger.debug(
        "Built indexed federal tax brackets for tax year %s: %s",
        tax_year,
        brackets,
    )
    return brackets


def indexed_provincial_tax_brackets(
    jurisdiction_code: str,
    tax_year: int,
) -> tuple[tuple[float, float, float], ...]:
    normalized_code = _normalize_jurisdiction_code(jurisdiction_code)
    brackets = _index_brackets(
        PROVINCIAL_TAX_BRACKETS_2023[normalized_code], tax_year=tax_year
    )
    logger.debug(
        "Built indexed provincial tax brackets for %s in tax year %s: %s",
        normalized_code,
        tax_year,
        brackets,
    )
    return brackets


def _calculate_progressive_tax(
    income: float,
    brackets: tuple[tuple[float, float, float], ...],
) -> float:
    normalized_income = max(income, 0.0)
    tax = 0.0
    for lower, upper, rate in brackets:
        if normalized_income <= lower:
            break

        taxable_amount = min(normalized_income, upper) - lower
        tax += taxable_amount * rate / 100.0

    return tax


def calculate_tax_approx(
    income: float,
    *,
    jurisdiction_code: str = "BC",
    tax_year: int = DEFAULT_TAX_YEAR,
) -> float:
    normalized_code = _normalize_jurisdiction_code(jurisdiction_code)
    normalized_income = max(income, 0.0)
    federal_tax = _calculate_progressive_tax(
        normalized_income,
        indexed_federal_tax_brackets(tax_year),
    )
    provincial_tax = _calculate_progressive_tax(
        normalized_income,
        indexed_provincial_tax_brackets(normalized_code, tax_year),
    )
    total_tax = round(federal_tax + provincial_tax, 2)
    logger.debug(
        "Calculated approximate tax: jurisdiction=%s income=%s tax_year=%s total_tax=%s",
        normalized_code,
        income,
        tax_year,
        total_tax,
    )
    return total_tax


def calculate_equivalent_before_tax_income(
    target_net_income: float,
    *,
    jurisdiction_code: str = "BC",
    tax_year: int = DEFAULT_TAX_YEAR,
) -> float:
    normalized_target = max(target_net_income, 0.0)
    if normalized_target <= 0:
        return 0.0

    lower = normalized_target
    upper = max(normalized_target, 1.0)
    while (
        upper - calculate_tax_approx(
            upper,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
        )
        < normalized_target
        and upper < 10_000_000
    ):
        upper *= 2.0

    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        derived_net_income = midpoint - calculate_tax_approx(
            midpoint,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
        )
        if derived_net_income < normalized_target:
            lower = midpoint
        else:
            upper = midpoint

    equivalent_income = round(upper, 2)
    logger.debug(
        "Calculated equivalent before-tax income: jurisdiction=%s target=%s tax_year=%s equivalent=%s",
        jurisdiction_code,
        target_net_income,
        tax_year,
        equivalent_income,
    )
    return equivalent_income


def calculate_bc_tax_approx(
    income: float,
    tax_year: int = DEFAULT_TAX_YEAR,
) -> float:
    return calculate_tax_approx(
        income,
        jurisdiction_code="BC",
        tax_year=tax_year,
    )
