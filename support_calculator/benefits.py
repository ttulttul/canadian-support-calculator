import logging

from .tax import resolve_tax_year_index_factor

logger = logging.getLogger(__name__)

FEDERAL_BENEFIT_LABELS = {
    "canadaChildBenefitAnnual": "Canada child benefit",
    "gstHstCreditAnnual": "GST/HST credit",
}

PROVINCIAL_BENEFIT_LABELS = {
    "BC": {
        "bcFamilyBenefitAnnual": "B.C. family benefit",
        "bcClimateActionCreditAnnual": "B.C. climate action credit",
    }
}

CCB_CHILD_COUNT_CAP = 4

CCB_CONFIGS = {
    2021: {
        "under_6": 6_997.0,
        "age_6_to_17": 5_903.0,
        "threshold_1": 32_797.0,
        "threshold_2": 71_060.0,
        "step_1_rates": {1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23},
        "step_2_bases": {1: 2_678.0, 2: 5_166.0, 3: 7_270.0, 4: 8_801.0},
        "step_2_rates": {1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095},
    },
    2022: {
        "under_6": 7_437.0,
        "age_6_to_17": 6_275.0,
        "threshold_1": 34_863.0,
        "threshold_2": 75_537.0,
        "step_1_rates": {1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23},
        "step_2_bases": {1: 2_847.0, 2: 5_490.0, 3: 7_726.0, 4: 9_352.0},
        "step_2_rates": {1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095},
    },
    2023: {
        "under_6": 7_787.0,
        "age_6_to_17": 6_570.0,
        "threshold_1": 36_502.0,
        "threshold_2": 79_087.0,
        "step_1_rates": {1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23},
        "step_2_bases": {1: 2_981.0, 2: 5_749.0, 3: 8_091.0, 4: 9_795.0},
        "step_2_rates": {1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095},
    },
    2024: {
        "under_6": 7_997.0,
        "age_6_to_17": 6_748.0,
        "threshold_1": 37_487.0,
        "threshold_2": 81_222.0,
        "step_1_rates": {1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23},
        "step_2_bases": {1: 3_061.0, 2: 5_904.0, 3: 8_310.0, 4: 10_059.0},
        "step_2_rates": {1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095},
    },
}

GST_HST_CONFIGS = {
    2021: {
        "base_credit": 306.0,
        "child_credit": 161.0,
        "single_supplement": 161.0,
        "single_supplement_threshold": 9_919.0,
        "phaseout_threshold": 39_826.0,
    },
    2022: {
        "base_credit": 325.0,
        "child_credit": 171.0,
        "single_supplement": 171.0,
        "single_supplement_threshold": 10_544.0,
        "phaseout_threshold": 42_335.0,
    },
    2023: {
        "base_credit": 340.0,
        "child_credit": 179.0,
        "single_supplement": 179.0,
        "single_supplement_threshold": 11_039.0,
        "phaseout_threshold": 44_324.0,
    },
    2024: {
        "base_credit": 349.0,
        "child_credit": 184.0,
        "single_supplement": 184.0,
        "single_supplement_threshold": 11_337.0,
        "phaseout_threshold": 45_521.0,
    },
}

BC_FAMILY_BENEFIT_CONFIGS = {
    2022: {
        "max_first_child": 1_750.0,
        "max_second_child": 1_100.0,
        "max_additional_child": 900.0,
        "min_first_child": 775.0,
        "min_second_child": 750.0,
        "min_additional_child": 725.0,
        "max_threshold": 27_354.0,
        "phaseout_threshold": 87_533.0,
        "single_parent_supplement": 500.0,
    },
    2023: {
        "max_first_child": 2_188.0,
        "max_second_child": 1_375.0,
        "max_additional_child": 1_125.0,
        "min_first_child": 969.0,
        "min_second_child": 937.0,
        "min_additional_child": 906.0,
        "max_threshold": 35_902.0,
        "phaseout_threshold": 114_887.0,
        "single_parent_supplement": 500.0,
    },
    2024: {
        "max_first_child": 1_750.0,
        "max_second_child": 1_100.0,
        "max_additional_child": 900.0,
        "min_first_child": 775.0,
        "min_second_child": 750.0,
        "min_additional_child": 725.0,
        "max_threshold": 29_526.0,
        "phaseout_threshold": 94_483.0,
        "single_parent_supplement": 500.0,
    },
}

BC_CLIMATE_ACTION_CONFIGS = {
    2021: {
        "adult": 447.0,
        "second_adult_or_first_child": 223.5,
        "additional_child": 111.5,
        "single_threshold": 39_115.0,
        "family_threshold": 50_170.0,
    },
    2022: {
        "adult": 504.0,
        "second_adult_or_first_child": 252.0,
        "additional_child": 126.0,
        "single_threshold": 41_071.0,
        "family_threshold": 57_288.0,
    },
    2023: {
        "adult": 504.0,
        "second_adult_or_first_child": 252.0,
        "additional_child": 126.0,
        "single_threshold": 41_071.0,
        "family_threshold": 57_288.0,
    },
}


def _year_scaled_config(configs: dict[int, dict[str, float]], tax_year: int) -> dict[str, float]:
    if tax_year in configs:
        return configs[tax_year]

    known_years = sorted(configs)
    if tax_year < known_years[0]:
        source_year = known_years[0]
    else:
        source_year = known_years[-1]

    source_factor = resolve_tax_year_index_factor(source_year)
    target_factor = resolve_tax_year_index_factor(tax_year)
    scale = target_factor / source_factor

    logger.info(
        "Scaling benefit configuration from %s to %s with factor %.6f",
        source_year,
        tax_year,
        scale,
    )
    scaled_config = {}
    for key, value in configs[source_year].items():
        if isinstance(value, dict):
            if key.endswith("_rates"):
                scaled_config[key] = value.copy()
            else:
                scaled_config[key] = {
                    nested_key: round(nested_value * scale, 2)
                    for nested_key, nested_value in value.items()
                }
        elif isinstance(value, (int, float)):
            scaled_config[key] = round(value * scale, 2)
        else:
            scaled_config[key] = value

    return scaled_config


def calculate_canada_child_benefit(
    *,
    adjusted_family_net_income: float,
    num_children: int,
    children_under_six: int,
    tax_year: int,
) -> float:
    if num_children <= 0:
        return 0.0

    config = _year_scaled_config(CCB_CONFIGS, tax_year)
    capped_child_count = min(num_children, CCB_CHILD_COUNT_CAP)
    children_over_six = num_children - children_under_six
    maximum_benefit = (
        config["under_6"] * children_under_six
        + config["age_6_to_17"] * children_over_six
    )
    threshold_1 = config["threshold_1"]
    threshold_2 = config["threshold_2"]

    if adjusted_family_net_income <= threshold_1:
        reduction = 0.0
    elif adjusted_family_net_income <= threshold_2:
        reduction = (
            adjusted_family_net_income - threshold_1
        ) * config["step_1_rates"][capped_child_count]
    else:
        reduction = config["step_2_bases"][capped_child_count] + (
            adjusted_family_net_income - threshold_2
        ) * config["step_2_rates"][capped_child_count]

    benefit = max(maximum_benefit - reduction, 0.0)
    logger.debug(
        "Calculated CCB: afni=%s children=%s under_6=%s tax_year=%s benefit=%s",
        adjusted_family_net_income,
        num_children,
        children_under_six,
        tax_year,
        benefit,
    )
    return round(benefit, 2)


def calculate_gst_hst_credit(
    *,
    adjusted_family_net_income: float,
    registered_children: int,
    household_adults: int = 1,
    tax_year: int,
) -> float:
    config = _year_scaled_config(GST_HST_CONFIGS, tax_year)
    if household_adults > 1:
        subtotal = config["base_credit"] * 2 + config["child_credit"] * registered_children
    elif registered_children > 0:
        subtotal = (
            config["base_credit"] * 2
            + config["child_credit"] * max(registered_children - 1, 0)
            + config["single_supplement"]
        )
    else:
        single_supplement = min(
            config["single_supplement"],
            max(adjusted_family_net_income - config["single_supplement_threshold"], 0.0) * 0.02,
        )
        subtotal = config["base_credit"] + single_supplement

    reduction = max(adjusted_family_net_income - config["phaseout_threshold"], 0.0) * 0.05
    credit = max(subtotal - reduction, 0.0)
    logger.debug(
        "Calculated GST/HST credit: afni=%s children=%s tax_year=%s credit=%s",
        adjusted_family_net_income,
        registered_children,
        tax_year,
        credit,
    )
    return round(credit, 2)


def _bc_family_benefit_child_amount(
    *,
    count: int,
    first_child_amount: float,
    second_child_amount: float,
    additional_child_amount: float,
) -> float:
    if count <= 0:
        return 0.0
    if count == 1:
        return first_child_amount
    if count == 2:
        return first_child_amount + second_child_amount
    return (
        first_child_amount
        + second_child_amount
        + additional_child_amount * (count - 2)
    )


def calculate_bc_family_benefit(
    *,
    adjusted_family_net_income: float,
    registered_children: int,
    household_adults: int = 1,
    tax_year: int,
) -> float:
    if registered_children <= 0:
        return 0.0

    config = _year_scaled_config(BC_FAMILY_BENEFIT_CONFIGS, tax_year)
    maximum_child_amount = _bc_family_benefit_child_amount(
        count=registered_children,
        first_child_amount=config["max_first_child"],
        second_child_amount=config["max_second_child"],
        additional_child_amount=config["max_additional_child"],
    )
    guaranteed_minimum_amount = _bc_family_benefit_child_amount(
        count=registered_children,
        first_child_amount=config["min_first_child"],
        second_child_amount=config["min_second_child"],
        additional_child_amount=config["min_additional_child"],
    )

    maximum_total = maximum_child_amount + (
        config["single_parent_supplement"] if household_adults == 1 else 0.0
    )
    if adjusted_family_net_income <= config["max_threshold"]:
        benefit = maximum_total
    elif adjusted_family_net_income <= config["phaseout_threshold"]:
        benefit = max(
            maximum_total
            - (adjusted_family_net_income - config["max_threshold"]) * 0.04,
            guaranteed_minimum_amount,
        )
    else:
        benefit = max(
            guaranteed_minimum_amount
            - (adjusted_family_net_income - config["phaseout_threshold"]) * 0.04,
            0.0,
        )

    logger.debug(
        "Calculated BC family benefit: afni=%s children=%s tax_year=%s benefit=%s",
        adjusted_family_net_income,
        registered_children,
        tax_year,
        benefit,
    )
    return round(benefit, 2)


def calculate_bc_climate_action_credit(
    *,
    adjusted_family_net_income: float,
    registered_children: int,
    household_adults: int = 1,
    tax_year: int,
) -> float:
    if tax_year >= 2024:
        logger.debug("BC climate action credit is zero for tax year %s.", tax_year)
        return 0.0

    config = _year_scaled_config(BC_CLIMATE_ACTION_CONFIGS, tax_year)
    if household_adults > 1 or registered_children > 0:
        threshold = config["family_threshold"]
        maximum_credit = config["adult"]
        if household_adults > 1:
            maximum_credit += config["second_adult_or_first_child"]
            maximum_credit += config["additional_child"] * registered_children
        elif registered_children > 0:
            maximum_credit += config["second_adult_or_first_child"]
            maximum_credit += config["additional_child"] * max(registered_children - 1, 0)
    else:
        threshold = config["single_threshold"]
        maximum_credit = config["adult"]

    credit = max(maximum_credit - max(adjusted_family_net_income - threshold, 0.0) * 0.02, 0.0)
    logger.debug(
        "Calculated BC climate action credit: afni=%s children=%s tax_year=%s credit=%s",
        adjusted_family_net_income,
        registered_children,
        tax_year,
        credit,
    )
    return round(credit, 2)


def _round_benefit_breakdown(values: dict[str, float]) -> dict[str, float]:
    rounded = {key: round(value, 2) for key, value in values.items()}
    rounded["totalAnnual"] = round(sum(values.values()), 2)
    return rounded


def _modeled_benefit_labels(
    *,
    jurisdiction_code: str,
    include_climate_credit: bool,
) -> list[dict[str, str]]:
    line_items = [
        {"key": key, "label": label}
        for key, label in FEDERAL_BENEFIT_LABELS.items()
    ]
    for key, label in PROVINCIAL_BENEFIT_LABELS.get(jurisdiction_code, {}).items():
        if key == "bcClimateActionCreditAnnual" and not include_climate_credit:
            continue
        line_items.append({"key": key, "label": label})

    return line_items


def _normalized_registered_children(
    *,
    payor_registered_children: int | None,
    recipient_registered_children: int | None,
    num_children: int,
) -> tuple[int, int, bool]:
    if payor_registered_children is None and recipient_registered_children is None:
        return num_children, num_children, False

    if payor_registered_children is None:
        payor_registered_children = max(num_children - recipient_registered_children, 0)
    if recipient_registered_children is None:
        recipient_registered_children = max(num_children - payor_registered_children, 0)

    if payor_registered_children < 0 or recipient_registered_children < 0:
        raise ValueError("Registered child counts must be zero or greater.")
    if payor_registered_children > num_children or recipient_registered_children > num_children:
        raise ValueError("Registered child counts cannot exceed the total number of children.")
    if payor_registered_children + recipient_registered_children != num_children:
        raise ValueError(
            "Explicit registered child allocations must add up to the total number of children."
        )

    return payor_registered_children, recipient_registered_children, True


def _allocated_under_six(
    *,
    total_children_under_six: int,
    payor_registered_children: int,
    recipient_registered_children: int,
    payor_children_under_six: int | None,
    recipient_children_under_six: int | None,
) -> tuple[int, int]:
    if payor_children_under_six is not None and recipient_children_under_six is not None:
        if payor_children_under_six < 0 or recipient_children_under_six < 0:
            raise ValueError("Allocated children under 6 must be zero or greater.")
        if payor_children_under_six > payor_registered_children:
            raise ValueError("Payor children under 6 cannot exceed the payor's registered children.")
        if recipient_children_under_six > recipient_registered_children:
            raise ValueError(
                "Recipient children under 6 cannot exceed the recipient's registered children."
            )
        if payor_children_under_six + recipient_children_under_six != total_children_under_six:
            raise ValueError(
                "Explicit children under 6 allocations must add up to the total number of children under 6."
            )
        return payor_children_under_six, recipient_children_under_six

    if payor_children_under_six is not None:
        if payor_children_under_six < 0:
            raise ValueError("Payor children under 6 must be zero or greater.")
        if payor_children_under_six > min(total_children_under_six, payor_registered_children):
            raise ValueError("Payor children under 6 cannot exceed the payor's registered children.")
        recipient_children_under_six = max(total_children_under_six - payor_children_under_six, 0)
        return payor_children_under_six, recipient_children_under_six
    if recipient_children_under_six is not None:
        if recipient_children_under_six < 0:
            raise ValueError("Recipient children under 6 must be zero or greater.")
        if recipient_children_under_six > min(
            total_children_under_six,
            recipient_registered_children,
        ):
            raise ValueError(
                "Recipient children under 6 cannot exceed the recipient's registered children."
            )
        payor_children_under_six = max(total_children_under_six - recipient_children_under_six, 0)
        return payor_children_under_six, recipient_children_under_six

    total_registered = payor_registered_children + recipient_registered_children
    if total_registered <= 0 or total_children_under_six <= 0:
        return 0, 0

    payor_allocation = round(total_children_under_six * (payor_registered_children / total_registered))
    payor_allocation = min(payor_allocation, total_children_under_six, payor_registered_children)
    recipient_allocation = min(
        total_children_under_six - payor_allocation,
        recipient_registered_children,
    )
    return payor_allocation, recipient_allocation


def calculate_shared_custody_benefits(
    *,
    jurisdiction_code: str,
    payor_adjusted_family_net_income: float,
    recipient_adjusted_family_net_income: float,
    num_children: int,
    children_under_six: int,
    tax_year: int,
    payor_registered_children: int | None = None,
    recipient_registered_children: int | None = None,
    payor_household_adults: int = 1,
    recipient_household_adults: int = 1,
    payor_children_under_six: int | None = None,
    recipient_children_under_six: int | None = None,
) -> dict:
    if num_children <= 0:
        raise ValueError("Number of children must be greater than zero.")

    if children_under_six < 0 or children_under_six > num_children:
        raise ValueError("'childrenUnderSix' must be between zero and the total number of children.")
    if payor_household_adults <= 0 or recipient_household_adults <= 0:
        raise ValueError("Household adult counts must be greater than zero.")

    normalized_code = str(jurisdiction_code or "BC").upper()
    (
        normalized_payor_registered_children,
        normalized_recipient_registered_children,
        explicit_allocation,
    ) = _normalized_registered_children(
        payor_registered_children=payor_registered_children,
        recipient_registered_children=recipient_registered_children,
        num_children=num_children,
    )
    if explicit_allocation:
        (
            normalized_payor_children_under_six,
            normalized_recipient_children_under_six,
        ) = _allocated_under_six(
            total_children_under_six=children_under_six,
            payor_registered_children=normalized_payor_registered_children,
            recipient_registered_children=normalized_recipient_registered_children,
            payor_children_under_six=payor_children_under_six,
            recipient_children_under_six=recipient_children_under_six,
        )
    else:
        normalized_payor_children_under_six = children_under_six
        normalized_recipient_children_under_six = children_under_six

    payor_full = {
        "canadaChildBenefitAnnual": calculate_canada_child_benefit(
            adjusted_family_net_income=payor_adjusted_family_net_income,
            num_children=normalized_payor_registered_children,
            children_under_six=normalized_payor_children_under_six,
            tax_year=tax_year,
        ),
        "gstHstCreditAnnual": calculate_gst_hst_credit(
            adjusted_family_net_income=payor_adjusted_family_net_income,
            registered_children=normalized_payor_registered_children,
            household_adults=payor_household_adults,
            tax_year=tax_year,
        ),
    }
    recipient_full = {
        "canadaChildBenefitAnnual": calculate_canada_child_benefit(
            adjusted_family_net_income=recipient_adjusted_family_net_income,
            num_children=normalized_recipient_registered_children,
            children_under_six=normalized_recipient_children_under_six,
            tax_year=tax_year,
        ),
        "gstHstCreditAnnual": calculate_gst_hst_credit(
            adjusted_family_net_income=recipient_adjusted_family_net_income,
            registered_children=normalized_recipient_registered_children,
            household_adults=recipient_household_adults,
            tax_year=tax_year,
        ),
    }

    if normalized_code == "BC":
        payor_full["bcFamilyBenefitAnnual"] = calculate_bc_family_benefit(
            adjusted_family_net_income=payor_adjusted_family_net_income,
            registered_children=normalized_payor_registered_children,
            household_adults=payor_household_adults,
            tax_year=tax_year,
        )
        payor_full["bcClimateActionCreditAnnual"] = calculate_bc_climate_action_credit(
            adjusted_family_net_income=payor_adjusted_family_net_income,
            registered_children=normalized_payor_registered_children,
            household_adults=payor_household_adults,
            tax_year=tax_year,
        )
        recipient_full["bcFamilyBenefitAnnual"] = calculate_bc_family_benefit(
            adjusted_family_net_income=recipient_adjusted_family_net_income,
            registered_children=normalized_recipient_registered_children,
            household_adults=recipient_household_adults,
            tax_year=tax_year,
        )
        recipient_full["bcClimateActionCreditAnnual"] = calculate_bc_climate_action_credit(
            adjusted_family_net_income=recipient_adjusted_family_net_income,
            registered_children=normalized_recipient_registered_children,
            household_adults=recipient_household_adults,
            tax_year=tax_year,
        )

    if explicit_allocation:
        payor = _round_benefit_breakdown(payor_full)
        recipient = _round_benefit_breakdown(recipient_full)
    else:
        shared_multiplier = 0.5
        payor = _round_benefit_breakdown(
            {key: value * shared_multiplier for key, value in payor_full.items()}
        )
        recipient = _round_benefit_breakdown(
            {key: value * shared_multiplier for key, value in recipient_full.items()}
        )
    logger.info(
        "Calculated shared-custody benefits: jurisdiction=%s tax_year=%s children=%s under_6=%s payor_children=%s recipient_children=%s payor_total=%s recipient_total=%s",
        normalized_code,
        tax_year,
        num_children,
        children_under_six,
        normalized_payor_registered_children,
        normalized_recipient_registered_children,
        payor["totalAnnual"],
        recipient["totalAnnual"],
    )
    include_climate_credit = (
        payor.get("bcClimateActionCreditAnnual", 0.0) > 0
        or recipient.get("bcClimateActionCreditAnnual", 0.0) > 0
    )
    return {
        "jurisdiction": normalized_code,
        "assumptions": {
            "sharedCustody": True,
            "singleHouseholds": payor_household_adults == 1 and recipient_household_adults == 1,
            "childrenUnderSix": children_under_six,
            "explicitAllocation": explicit_allocation,
            "payorRegisteredChildren": normalized_payor_registered_children,
            "recipientRegisteredChildren": normalized_recipient_registered_children,
            "payorHouseholdAdults": payor_household_adults,
            "recipientHouseholdAdults": recipient_household_adults,
            "payorChildrenUnderSix": normalized_payor_children_under_six,
            "recipientChildrenUnderSix": normalized_recipient_children_under_six,
        },
        "lineItems": _modeled_benefit_labels(
            jurisdiction_code=normalized_code,
            include_climate_credit=include_climate_credit,
        ),
        "payor": payor,
        "recipient": recipient,
    }
