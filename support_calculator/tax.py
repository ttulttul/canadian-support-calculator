import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

BASE_TAX_YEAR = 2023
DEFAULT_TAX_YEAR = 2023
DEFAULT_EXTRAPOLATION_RATE = 0.025
DEFAULT_BASIC_PERSONAL_AMOUNT_REDUCTION_RATE = 0.15


FEDERAL_TAX_BRACKETS = {
    2023: (
        (0.0, 53_359.0, 15.0),
        (53_359.0, 106_717.0, 20.5),
        (106_717.0, 165_430.0, 26.0),
        (165_430.0, 235_675.0, 29.0),
        (235_675.0, float("inf"), 33.0),
    ),
    2025: (
        (0.0, 57_375.0, 14.5),
        (57_375.0, 114_750.0, 20.5),
        (114_750.0, 177_882.0, 26.0),
        (177_882.0, 253_414.0, 29.0),
        (253_414.0, float("inf"), 33.0),
    ),
    2026: (
        (0.0, 58_523.0, 14.0),
        (58_523.0, 117_046.0, 20.5),
        (117_046.0, 181_440.0, 26.0),
        (181_440.0, 258_275.0, 29.0),
        (258_275.0, float("inf"), 33.0),
    ),
}

PROVINCIAL_TAX_BRACKETS = {
    2023: {
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
    },
    2025: {
        "AB": (
            (0.0, 60_000.0, 8.0),
            (60_000.0, 151_234.0, 10.0),
            (151_234.0, 181_481.0, 12.0),
            (181_481.0, 241_974.0, 13.0),
            (241_974.0, 362_961.0, 14.0),
            (362_961.0, float("inf"), 15.0),
        ),
        "BC": (
            (0.0, 49_279.0, 5.06),
            (49_279.0, 98_560.0, 7.70),
            (98_560.0, 113_158.0, 10.50),
            (113_158.0, 137_407.0, 12.29),
            (137_407.0, 186_306.0, 14.70),
            (186_306.0, 259_829.0, 16.80),
            (259_829.0, float("inf"), 20.50),
        ),
        "MB": (
            (0.0, 47_000.0, 10.80),
            (47_000.0, 100_000.0, 12.75),
            (100_000.0, float("inf"), 17.40),
        ),
        "NB": (
            (0.0, 51_306.0, 9.40),
            (51_306.0, 102_614.0, 14.00),
            (102_614.0, 190_060.0, 16.00),
            (190_060.0, float("inf"), 19.50),
        ),
        "NL": (
            (0.0, 43_198.0, 8.70),
            (43_198.0, 86_395.0, 14.50),
            (86_395.0, 154_244.0, 15.80),
            (154_244.0, 215_943.0, 17.80),
            (215_943.0, 275_870.0, 19.80),
            (275_870.0, 551_739.0, 20.80),
            (551_739.0, float("inf"), 21.30),
        ),
        "NS": (
            (0.0, 30_507.0, 8.79),
            (30_507.0, 61_015.0, 14.95),
            (61_015.0, 95_883.0, 16.67),
            (95_883.0, 154_650.0, 17.50),
            (154_650.0, float("inf"), 21.00),
        ),
        "NT": (
            (0.0, 51_964.0, 5.90),
            (51_964.0, 103_930.0, 8.60),
            (103_930.0, 168_967.0, 12.20),
            (168_967.0, float("inf"), 14.05),
        ),
        "NU": (
            (0.0, 57_375.0, 4.00),
            (57_375.0, 114_750.0, 7.00),
            (114_750.0, 186_160.0, 9.00),
            (186_160.0, float("inf"), 11.50),
        ),
        "ON": (
            (0.0, 52_886.0, 5.05),
            (52_886.0, 105_775.0, 9.15),
            (105_775.0, 150_000.0, 11.16),
            (150_000.0, 220_000.0, 12.16),
            (220_000.0, float("inf"), 13.16),
        ),
        "PE": (
            (0.0, 33_328.0, 9.50),
            (33_328.0, 64_656.0, 13.47),
            (64_656.0, 105_000.0, 16.60),
            (105_000.0, 140_000.0, 17.62),
            (140_000.0, float("inf"), 19.00),
        ),
        "SK": (
            (0.0, 53_463.0, 10.00),
            (53_463.0, 152_750.0, 12.00),
            (152_750.0, float("inf"), 14.00),
        ),
        "YT": (
            (0.0, 57_375.0, 6.40),
            (57_375.0, 114_750.0, 9.00),
            (114_750.0, 177_882.0, 10.90),
            (177_882.0, 500_000.0, 12.80),
            (500_000.0, float("inf"), 15.00),
        ),
    },
    2026: {
        "AB": (
            (0.0, 60_000.0, 8.0),
            (60_000.0, 154_244.0, 10.0),
            (154_244.0, 185_093.0, 12.0),
            (185_093.0, 246_790.0, 13.0),
            (246_790.0, 370_185.0, 14.0),
            (370_185.0, float("inf"), 15.0),
        ),
        "BC": (
            (0.0, 50_197.0, 5.06),
            (50_197.0, 100_392.0, 7.70),
            (100_392.0, 115_158.0, 10.50),
            (115_158.0, 139_220.0, 12.29),
            (139_220.0, 188_325.0, 14.70),
            (188_325.0, 262_475.0, 16.80),
            (262_475.0, float("inf"), 20.50),
        ),
        "MB": (
            (0.0, 47_564.0, 10.80),
            (47_564.0, 101_200.0, 12.75),
            (101_200.0, float("inf"), 17.40),
        ),
        "NB": (
            (0.0, 52_164.0, 9.40),
            (52_164.0, 104_333.0, 14.00),
            (104_333.0, 193_557.0, 16.00),
            (193_557.0, float("inf"), 19.50),
        ),
        "NL": (
            (0.0, 43_794.0, 8.70),
            (43_794.0, 87_589.0, 14.50),
            (87_589.0, 156_381.0, 15.80),
            (156_381.0, 218_324.0, 17.80),
            (218_324.0, 278_229.0, 19.80),
            (278_229.0, 556_457.0, 20.80),
            (556_457.0, float("inf"), 21.30),
        ),
        "NS": (
            (0.0, 31_016.0, 8.79),
            (31_016.0, 62_031.0, 14.95),
            (62_031.0, 97_259.0, 16.67),
            (97_259.0, 156_888.0, 17.50),
            (156_888.0, float("inf"), 21.00),
        ),
        "NT": (
            (0.0, 53_338.0, 5.90),
            (53_338.0, 106_679.0, 8.60),
            (106_679.0, 173_205.0, 12.20),
            (173_205.0, float("inf"), 14.05),
        ),
        "NU": (
            (0.0, 58_523.0, 4.00),
            (58_523.0, 117_046.0, 7.00),
            (117_046.0, 190_739.0, 9.00),
            (190_739.0, float("inf"), 11.50),
        ),
        "ON": (
            (0.0, 53_561.0, 5.05),
            (53_561.0, 107_123.0, 9.15),
            (107_123.0, 150_000.0, 11.16),
            (150_000.0, 220_000.0, 12.16),
            (220_000.0, float("inf"), 13.16),
        ),
        "PE": (
            (0.0, 33_810.0, 9.50),
            (33_810.0, 67_620.0, 13.47),
            (67_620.0, 105_000.0, 16.60),
            (105_000.0, 140_000.0, 17.62),
            (140_000.0, float("inf"), 19.00),
        ),
        "SK": (
            (0.0, 54_463.0, 10.00),
            (54_463.0, 155_625.0, 12.00),
            (155_625.0, float("inf"), 14.00),
        ),
        "YT": (
            (0.0, 58_523.0, 6.40),
            (58_523.0, 117_046.0, 9.00),
            (117_046.0, 181_440.0, 10.90),
            (181_440.0, 500_000.0, 12.80),
            (500_000.0, float("inf"), 15.00),
        ),
    },
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
    2026: 58_523 / 53_359,
}

FEDERAL_BASIC_PERSONAL_AMOUNT = {
    2025: {"max": 16_129.0, "min": 14_538.0, "phaseout_start": 177_882.0, "phaseout_end": 253_414.0},
    2026: {"max": 16_452.0, "min": 14_870.0, "phaseout_start": 181_440.0, "phaseout_end": 258_275.0},
}

FEDERAL_EMPLOYMENT_AMOUNT = {
    2025: 1_433.0,
    2026: 1_474.0,
}

PROVINCIAL_BASIC_PERSONAL_AMOUNT = {
    2025: {
        "AB": 22_323.0,
        "BC": 12_932.0,
        "MB": 15_780.0,
        "NB": 13_396.0,
        "NL": 10_818.0,
        "NS": 11_744.0,
        "NT": 17_842.0,
        "NU": 19_274.0,
        "ON": 12_747.0,
        "PE": 14_650.0,
        "SK": 19_491.0,
        "YT": None,
    },
    2026: {
        "AB": 23_569.0,
        "BC": 13_393.0,
        "MB": 15_969.0,
        "NB": 13_521.0,
        "NL": 10_818.0,
        "NS": 11_744.0,
        "NT": 18_180.0,
        "NU": 19_889.0,
        "ON": 13_150.0,
        "PE": 14_650.0,
        "SK": 19_991.0,
        "YT": None,
    },
}

CPP_CONFIG = {
    2023: {
        "basic_exemption": 3_500.0,
        "ympe": 66_600.0,
        "yame": None,
        "base_rate": 0.0495,
        "first_additional_rate": 0.01,
        "second_additional_rate": 0.0,
    },
    2024: {
        "basic_exemption": 3_500.0,
        "ympe": 68_500.0,
        "yame": 73_200.0,
        "base_rate": 0.0495,
        "first_additional_rate": 0.01,
        "second_additional_rate": 0.04,
    },
    2025: {
        "basic_exemption": 3_500.0,
        "ympe": 71_300.0,
        "yame": 81_200.0,
        "base_rate": 0.0495,
        "first_additional_rate": 0.01,
        "second_additional_rate": 0.04,
    },
    2026: {
        "basic_exemption": 3_500.0,
        "ympe": 72_500.0,
        "yame": 82_700.0,
        "base_rate": 0.0495,
        "first_additional_rate": 0.01,
        "second_additional_rate": 0.04,
    },
}

EI_CONFIG = {
    2023: {"max_insurable_earnings": 61_500.0, "rate": 0.0163},
    2024: {"max_insurable_earnings": 63_200.0, "rate": 0.0166},
    2025: {"max_insurable_earnings": 65_700.0, "rate": 0.0164},
    2026: {"max_insurable_earnings": 67_400.0, "rate": 0.0163},
}

BC_TAX_REDUCTION = {
    2025: {"maximum": 562.0, "threshold": 25_020.0, "phaseout_end": 40_807.0},
    2026: {"maximum": 575.0, "threshold": 25_570.0, "phaseout_end": 41_722.0},
}

ONTARIO_TAX_REDUCTION = {
    2025: {"base_amount": 294.0, "threshold_1": 5_710.0, "threshold_2": 7_307.0},
    2026: {"base_amount": 300.0, "threshold_1": 5_818.0, "threshold_2": 7_446.0},
}

ONTARIO_HEALTH_PREMIUM_BRACKETS = (
    (20_000.0, 25_000.0, 0.06, 0.0),
    (25_000.0, 36_000.0, 0.06, 300.0),
    (36_000.0, 38_500.0, 0.25, 300.0),
    (38_500.0, 48_000.0, 0.25, 450.0),
    (48_000.0, 48_600.0, 0.25, 600.0),
    (48_600.0, 72_000.0, 0.25, 750.0),
    (72_000.0, 72_600.0, 0.25, 1_000.0),
    (72_600.0, 200_000.0, 0.25, 1_050.0),
    (200_000.0, 200_600.0, 0.25, 1_050.0),
    (200_600.0, float("inf"), 0.0, 900.0),
)

ALBERTA_SUPPLEMENTAL_CREDIT_THRESHOLD = {
    2025: 4_800.0,
    2026: 4_896.0,
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
    if normalized_code not in PROVINCIAL_TAX_BRACKETS[BASE_TAX_YEAR]:
        raise ValueError(f"Unsupported jurisdiction code '{jurisdiction_code}'.")
    return normalized_code


def _year_table(
    tables: dict[int, object],
    tax_year: int,
    *,
    scaler: Callable | None = None,
) -> object:
    if tax_year in tables:
        return tables[tax_year]

    known_years = sorted(tables)
    if tax_year < known_years[0]:
        source_year = known_years[0]
    else:
        source_year = known_years[-1]

    if scaler is None:
        raise ValueError(f"No scaled tax data is available for tax year {tax_year}.")

    logger.info("Scaling tax data from %s to %s.", source_year, tax_year)
    return scaler(tables[source_year], source_year, tax_year)


def _scale_scalar(value: float, source_year: int, target_year: int) -> float:
    source_factor = resolve_tax_year_index_factor(source_year)
    target_factor = resolve_tax_year_index_factor(target_year)
    return round(value * (target_factor / source_factor), 2)


def _scale_brackets(
    brackets: tuple[tuple[float, float, float], ...],
    source_year: int,
    target_year: int,
) -> tuple[tuple[float, float, float], ...]:
    factor = resolve_tax_year_index_factor(target_year) / resolve_tax_year_index_factor(source_year)
    scaled = []
    for lower, upper, rate in brackets:
        scaled.append(
            (
                round(lower * factor, 2),
                float("inf") if upper == float("inf") else round(upper * factor, 2),
                rate,
            )
        )
    return tuple(scaled)


def _scale_jurisdiction_table(
    values_by_code: dict[str, float | None],
    source_year: int,
    target_year: int,
) -> dict[str, float | None]:
    scaled = {}
    for code, value in values_by_code.items():
        if value is None:
            scaled[code] = None
            continue
        scaled[code] = _scale_scalar(value, source_year, target_year)
    return scaled


def indexed_federal_tax_brackets(
    tax_year: int,
) -> tuple[tuple[float, float, float], ...]:
    brackets = _year_table(FEDERAL_TAX_BRACKETS, tax_year, scaler=_scale_brackets)
    logger.debug("Built federal tax brackets for %s: %s", tax_year, brackets)
    return brackets


def indexed_provincial_tax_brackets(
    jurisdiction_code: str,
    tax_year: int,
) -> tuple[tuple[float, float, float], ...]:
    normalized_code = _normalize_jurisdiction_code(jurisdiction_code)
    table = _year_table(
        PROVINCIAL_TAX_BRACKETS,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            code: _scale_brackets(brackets, source_year, target_year)
            for code, brackets in values.items()
        },
    )
    brackets = table[normalized_code]
    logger.debug(
        "Built provincial tax brackets for %s in %s: %s",
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


def _lowest_rate(brackets: tuple[tuple[float, float, float], ...]) -> float:
    return brackets[0][2] / 100.0


def _federal_basic_personal_amount(taxable_income: float, tax_year: int) -> float:
    config = _year_table(
        FEDERAL_BASIC_PERSONAL_AMOUNT,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            key: _scale_scalar(value, source_year, target_year)
            for key, value in values.items()
        },
    )
    if taxable_income <= config["phaseout_start"]:
        return config["max"]
    if taxable_income >= config["phaseout_end"]:
        return config["min"]
    reduction_ratio = (
        (taxable_income - config["phaseout_start"])
        / (config["phaseout_end"] - config["phaseout_start"])
    )
    amount = config["max"] - ((config["max"] - config["min"]) * reduction_ratio)
    return round(amount, 2)


def _federal_employment_amount(tax_year: int) -> float:
    return _year_table(FEDERAL_EMPLOYMENT_AMOUNT, tax_year, scaler=_scale_scalar)


def _provincial_basic_personal_amount(
    jurisdiction_code: str,
    taxable_income: float,
    tax_year: int,
) -> float:
    normalized_code = _normalize_jurisdiction_code(jurisdiction_code)
    values_by_code = _year_table(
        PROVINCIAL_BASIC_PERSONAL_AMOUNT,
        tax_year,
        scaler=_scale_jurisdiction_table,
    )
    if normalized_code == "YT":
        return _federal_basic_personal_amount(taxable_income, tax_year)
    if normalized_code == "MB" and tax_year >= 2025:
        maximum = values_by_code[normalized_code]
        if taxable_income <= 200_000.0:
            return float(maximum)
        if taxable_income >= 400_000.0:
            return 0.0
        reduction_ratio = (taxable_income - 200_000.0) / 200_000.0
        return round(maximum * (1.0 - reduction_ratio), 2)
    if normalized_code == "NS" and tax_year >= 2025:
        if taxable_income <= 75_000.0:
            return float(values_by_code[normalized_code])
        return 8_744.0
    return float(values_by_code[normalized_code])


def _cpp_config(tax_year: int) -> dict[str, float | None]:
    return _year_table(
        CPP_CONFIG,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            key: (
                None
                if value is None
                else _scale_scalar(value, source_year, target_year)
            )
            for key, value in values.items()
        },
    )


def _ei_config(tax_year: int) -> dict[str, float]:
    return _year_table(
        EI_CONFIG,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            "max_insurable_earnings": _scale_scalar(
                values["max_insurable_earnings"],
                source_year,
                target_year,
            ),
            "rate": values["rate"],
        },
    )


def calculate_payroll_deductions(
    income: float,
    *,
    tax_year: int = DEFAULT_TAX_YEAR,
) -> dict[str, float]:
    employment_income = max(income, 0.0)
    cpp_config = _cpp_config(tax_year)
    pensionable_earnings = max(
        min(employment_income, float(cpp_config["ympe"])) - float(cpp_config["basic_exemption"]),
        0.0,
    )
    base_cpp = pensionable_earnings * float(cpp_config["base_rate"])
    additional_cpp = pensionable_earnings * float(cpp_config["first_additional_rate"])
    if cpp_config["yame"] is not None and float(cpp_config["yame"]) > float(cpp_config["ympe"]):
        second_band_earnings = max(
            min(employment_income, float(cpp_config["yame"])) - float(cpp_config["ympe"]),
            0.0,
        )
        additional_cpp += second_band_earnings * float(cpp_config["second_additional_rate"])

    ei_config = _ei_config(tax_year)
    ei_premium = min(employment_income, ei_config["max_insurable_earnings"]) * ei_config["rate"]

    payroll = {
        "baseCppContribution": round(base_cpp, 2),
        "additionalCppContribution": round(additional_cpp, 2),
        "totalCppContribution": round(base_cpp + additional_cpp, 2),
        "eiPremium": round(ei_premium, 2),
        "payrollDeductions": round(base_cpp + additional_cpp + ei_premium, 2),
    }
    logger.debug("Calculated payroll deductions for %s in %s: %s", income, tax_year, payroll)
    return payroll


def _bc_tax_reduction(net_provincial_tax: float, taxable_income: float, tax_year: int) -> float:
    config = _year_table(
        BC_TAX_REDUCTION,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            key: _scale_scalar(value, source_year, target_year)
            for key, value in values.items()
        },
    )
    if taxable_income <= config["threshold"]:
        return min(config["maximum"], net_provincial_tax)
    reduction = config["maximum"] - ((taxable_income - config["threshold"]) * 0.036)
    return round(max(min(reduction, net_provincial_tax), 0.0), 2)


def _ontario_tax_reduction(net_provincial_tax: float, taxable_income: float, tax_year: int) -> float:
    config = _year_table(
        ONTARIO_TAX_REDUCTION,
        tax_year,
        scaler=lambda values, source_year, target_year: {
            key: _scale_scalar(value, source_year, target_year)
            for key, value in values.items()
        },
    )
    if taxable_income <= config["threshold_1"]:
        reduction = config["base_amount"] * 2.0
    elif taxable_income <= config["threshold_2"]:
        reduction = config["base_amount"] * 2.0 - ((taxable_income - config["threshold_1"]) * 0.06)
    else:
        reduction = config["base_amount"] - ((taxable_income - config["threshold_2"]) * 0.06)
    return round(max(min(reduction, net_provincial_tax), 0.0), 2)


def _ontario_health_premium(taxable_income: float) -> float:
    if taxable_income <= 20_000.0:
        return 0.0
    for lower, upper, rate, base in ONTARIO_HEALTH_PREMIUM_BRACKETS:
        if taxable_income <= upper:
            premium = base + max(taxable_income - lower, 0.0) * rate
            return round(min(premium, 900.0), 2)
    return 900.0


def _alberta_supplemental_credit(
    provincial_claim_credit: float,
    provincial_payroll_credit: float,
    tax_year: int,
) -> float:
    threshold = _year_table(
        ALBERTA_SUPPLEMENTAL_CREDIT_THRESHOLD,
        tax_year,
        scaler=_scale_scalar,
    )
    extra_credit_base = max((provincial_claim_credit + provincial_payroll_credit) - threshold, 0.0)
    return round(extra_credit_base * 0.25, 2)


def calculate_tax_profile(
    income: float,
    *,
    jurisdiction_code: str = "BC",
    tax_year: int = DEFAULT_TAX_YEAR,
    employment_income: float | None = None,
) -> dict[str, float | int | str]:
    normalized_code = _normalize_jurisdiction_code(jurisdiction_code)
    normalized_income = max(income, 0.0)
    active_employment_income = normalized_income if employment_income is None else max(
        employment_income,
        0.0,
    )
    payroll = calculate_payroll_deductions(active_employment_income, tax_year=tax_year)
    taxable_income = max(normalized_income - payroll["additionalCppContribution"], 0.0)

    federal_brackets = indexed_federal_tax_brackets(tax_year)
    provincial_brackets = indexed_provincial_tax_brackets(normalized_code, tax_year)
    federal_tax_before_credits = _calculate_progressive_tax(taxable_income, federal_brackets)
    provincial_tax_before_credits = _calculate_progressive_tax(taxable_income, provincial_brackets)

    federal_lowest_rate = _lowest_rate(federal_brackets)
    provincial_lowest_rate = _lowest_rate(provincial_brackets)
    federal_basic_personal_amount = _federal_basic_personal_amount(taxable_income, tax_year)
    provincial_basic_personal_amount = _provincial_basic_personal_amount(
        normalized_code,
        taxable_income,
        tax_year,
    )
    employment_amount = min(active_employment_income, _federal_employment_amount(tax_year))
    federal_claim_credit = federal_basic_personal_amount * federal_lowest_rate
    federal_payroll_credit = (payroll["baseCppContribution"] + payroll["eiPremium"]) * federal_lowest_rate
    federal_employment_credit = employment_amount * federal_lowest_rate
    federal_non_refundable_credits = (
        federal_claim_credit + federal_payroll_credit + federal_employment_credit
    )

    provincial_claim_credit = provincial_basic_personal_amount * provincial_lowest_rate
    provincial_payroll_credit = (
        payroll["baseCppContribution"] + payroll["eiPremium"]
    ) * provincial_lowest_rate
    provincial_employment_credit = employment_amount * provincial_lowest_rate if normalized_code == "YT" else 0.0
    provincial_non_refundable_credits = (
        provincial_claim_credit + provincial_payroll_credit + provincial_employment_credit
    )

    if normalized_code == "AB" and tax_year >= 2025:
        provincial_non_refundable_credits += _alberta_supplemental_credit(
            provincial_claim_credit,
            provincial_payroll_credit,
            tax_year,
        )

    net_federal_tax = max(federal_tax_before_credits - federal_non_refundable_credits, 0.0)
    net_provincial_tax = max(
        provincial_tax_before_credits - provincial_non_refundable_credits,
        0.0,
    )

    provincial_tax_reduction = 0.0
    if normalized_code == "BC":
        provincial_tax_reduction = _bc_tax_reduction(net_provincial_tax, taxable_income, tax_year)
    elif normalized_code == "ON":
        provincial_tax_reduction = _ontario_tax_reduction(net_provincial_tax, taxable_income, tax_year)

    provincial_surtax = _ontario_health_premium(taxable_income) if normalized_code == "ON" else 0.0
    income_tax = max(net_federal_tax + net_provincial_tax - provincial_tax_reduction + provincial_surtax, 0.0)
    total_deductions = income_tax + payroll["payrollDeductions"]

    profile = {
        "jurisdiction": normalized_code,
        "taxYear": tax_year,
        "income": round(normalized_income, 2),
        "employmentIncome": round(active_employment_income, 2),
        "taxableIncome": round(taxable_income, 2),
        "federalTaxBeforeCredits": round(federal_tax_before_credits, 2),
        "provincialTaxBeforeCredits": round(provincial_tax_before_credits, 2),
        "federalNonRefundableCredits": round(federal_non_refundable_credits, 2),
        "provincialNonRefundableCredits": round(provincial_non_refundable_credits, 2),
        "federalBasicPersonalAmount": round(federal_basic_personal_amount, 2),
        "provincialBasicPersonalAmount": round(provincial_basic_personal_amount, 2),
        "employmentAmount": round(employment_amount, 2),
        "provincialTaxReduction": round(provincial_tax_reduction, 2),
        "provincialSurtax": round(provincial_surtax, 2),
        "incomeTax": round(income_tax, 2),
        "baseCppContribution": payroll["baseCppContribution"],
        "additionalCppContribution": payroll["additionalCppContribution"],
        "totalCppContribution": payroll["totalCppContribution"],
        "eiPremium": payroll["eiPremium"],
        "payrollDeductions": payroll["payrollDeductions"],
        "totalDeductions": round(total_deductions, 2),
    }
    logger.debug(
        "Calculated tax profile: jurisdiction=%s income=%s tax_year=%s profile=%s",
        normalized_code,
        income,
        tax_year,
        profile,
    )
    return profile


def calculate_tax_approx(
    income: float,
    *,
    jurisdiction_code: str = "BC",
    tax_year: int = DEFAULT_TAX_YEAR,
) -> float:
    total_deductions = calculate_tax_profile(
        income,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
    )["totalDeductions"]
    logger.debug(
        "Calculated approximate total deductions: jurisdiction=%s income=%s tax_year=%s total=%s",
        jurisdiction_code,
        income,
        tax_year,
        total_deductions,
    )
    return float(total_deductions)


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
