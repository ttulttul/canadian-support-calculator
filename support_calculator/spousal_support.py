import logging

from .benefits import calculate_shared_custody_benefits
from .calculations import calculate_child_support_breakdown
from .tables import (
    ChildSupportTable,
    child_support_table_year_for_tax_year,
    load_default_child_support_table,
)
from .tax import calculate_equivalent_before_tax_income, calculate_tax_profile

logger = logging.getLogger(__name__)

MIDPOINT_TARGET_SHARE = 43.0
EQUALIZATION_TARGET_SHARE = 50.0
VALID_ELIGIBLE_DEPENDANT_CLAIMANTS = {"none", "payor", "recipient"}


def _resolve_registered_children_allocation(
    *,
    payor_registered_children: int | None,
    recipient_registered_children: int | None,
    num_children: int,
) -> tuple[int, int]:
    if payor_registered_children is None and recipient_registered_children is None:
        return num_children, num_children
    if payor_registered_children is None:
        payor_registered_children = max(num_children - recipient_registered_children, 0)
    if recipient_registered_children is None:
        recipient_registered_children = max(num_children - payor_registered_children, 0)
    return payor_registered_children, recipient_registered_children


def _duration_metadata(
    *,
    relationship_years: float | None,
    recipient_age_at_separation: float | None,
    years_until_child_full_time_school: float | None,
    years_until_child_finishes_high_school: float | None,
) -> dict:
    inputs_provided = any(
        value is not None
        for value in (
            relationship_years,
            recipient_age_at_separation,
            years_until_child_full_time_school,
            years_until_child_finishes_high_school,
        )
    )
    if not inputs_provided:
        return {
            "formulaType": "with_child_support_shared_custody",
            "durationType": "indefinite",
            "minYears": None,
            "maxYears": None,
            "inputsProvided": False,
        }

    relationship_value = 0.0 if relationship_years is None else relationship_years
    school_years = (
        0.0 if years_until_child_full_time_school is None else years_until_child_full_time_school
    )
    graduation_years = (
        0.0
        if years_until_child_finishes_high_school is None
        else years_until_child_finishes_high_school
    )
    minimum_duration = max(relationship_value / 2.0, school_years)
    maximum_duration = max(relationship_value, graduation_years)
    if relationship_years is None:
        minimum_duration = school_years or None
        maximum_duration = graduation_years or None

    return {
        "formulaType": "with_child_support_shared_custody",
        "durationType": "indefinite",
        "minYears": None if minimum_duration is None else round(minimum_duration, 2),
        "maxYears": None if maximum_duration is None else round(maximum_duration, 2),
        "inputsProvided": True,
        "recipientAgeAtSeparation": (
            None
            if recipient_age_at_separation is None
            else round(recipient_age_at_separation, 2)
        ),
    }


def calculate_spousal_support_estimate(
    *,
    payor_income: float,
    recipient_income: float,
    payor_spousal_income: float | None = None,
    recipient_spousal_income: float | None = None,
    child_support_override_monthly: float | None = None,
    fixed_total_support_annual: float | None = None,
    num_children: int,
    tax_year: int,
    children_under_six: int = 0,
    target_range: tuple[float, float] = (0.40, 0.46),
    max_iterations: int = 300,
    step: float = 500.0,
    tolerance: float = 0.5,
    table: ChildSupportTable | None = None,
    relationship_years: float | None = None,
    recipient_age_at_separation: float | None = None,
    years_until_child_full_time_school: float | None = None,
    years_until_child_finishes_high_school: float | None = None,
    payor_registered_children: int | None = None,
    recipient_registered_children: int | None = None,
    payor_household_adults: int = 1,
    recipient_household_adults: int = 1,
    payor_children_under_six: int | None = None,
    recipient_children_under_six: int | None = None,
    eligible_dependant_claimant: str = "none",
) -> dict:
    if payor_income < 0 or recipient_income < 0:
        raise ValueError("Income values must be zero or greater.")
    if children_under_six < 0 or children_under_six > num_children:
        raise ValueError("'childrenUnderSix' must be between zero and the total number of children.")
    if relationship_years is not None and relationship_years < 0:
        raise ValueError("'relationshipYears' must be zero or greater.")
    if recipient_age_at_separation is not None and recipient_age_at_separation < 0:
        raise ValueError("'recipientAgeAtSeparation' must be zero or greater.")
    if years_until_child_full_time_school is not None and years_until_child_full_time_school < 0:
        raise ValueError("'yearsUntilChildFullTimeSchool' must be zero or greater.")
    if (
        years_until_child_finishes_high_school is not None
        and years_until_child_finishes_high_school < 0
    ):
        raise ValueError("'yearsUntilChildFinishesHighSchool' must be zero or greater.")
    if payor_household_adults <= 0 or recipient_household_adults <= 0:
        raise ValueError("Household adult counts must be greater than zero.")

    target_min, target_max = target_range
    if not 0 < target_min < target_max < 1:
        raise ValueError("Target range must be between 0 and 1.")

    normalized_eligible_dependant_claimant = str(eligible_dependant_claimant or "none").lower()
    if normalized_eligible_dependant_claimant not in VALID_ELIGIBLE_DEPENDANT_CLAIMANTS:
        raise ValueError(
            "'eligibleDependantClaimant' must be one of 'none', 'payor', or 'recipient'."
        )

    active_table = table or load_default_child_support_table(
        table_year=child_support_table_year_for_tax_year(tax_year)
    )
    jurisdiction_code = active_table.jurisdiction_code
    active_payor_spousal_income = (
        payor_income if payor_spousal_income is None else payor_spousal_income
    )
    active_recipient_spousal_income = (
        recipient_income if recipient_spousal_income is None else recipient_spousal_income
    )
    child_support = calculate_child_support_breakdown(
        num_children=num_children,
        payor_income=payor_income,
        recipient_income=recipient_income,
        net_monthly_override=child_support_override_monthly,
        table=active_table,
    )
    (
        normalized_payor_registered_children,
        normalized_recipient_registered_children,
    ) = _resolve_registered_children_allocation(
        payor_registered_children=payor_registered_children,
        recipient_registered_children=recipient_registered_children,
        num_children=num_children,
    )
    payor_claim_eligible_dependant = normalized_eligible_dependant_claimant == "payor"
    recipient_claim_eligible_dependant = normalized_eligible_dependant_claimant == "recipient"
    if payor_claim_eligible_dependant and payor_household_adults != 1:
        raise ValueError(
            "The payor can only claim the eligible dependant credit in a single-adult household."
        )
    if recipient_claim_eligible_dependant and recipient_household_adults != 1:
        raise ValueError(
            "The recipient can only claim the eligible dependant credit in a single-adult household."
        )
    if payor_claim_eligible_dependant and normalized_payor_registered_children <= 0:
        raise ValueError(
            "The payor cannot claim the eligible dependant credit without any registered children."
        )
    if recipient_claim_eligible_dependant and normalized_recipient_registered_children <= 0:
        raise ValueError(
            "The recipient cannot claim the eligible dependant credit without any registered children."
        )
    ndi_child_support = calculate_child_support_breakdown(
        num_children=num_children,
        payor_income=active_payor_spousal_income,
        recipient_income=active_recipient_spousal_income,
        net_monthly_override=child_support_override_monthly,
        table=active_table,
    )
    actual_net_child_support_annual = child_support["netAnnual"]
    formula_payor_child_support_annual = ndi_child_support["payorAnnual"]
    formula_recipient_child_support_annual = ndi_child_support["recipientAnnual"]
    target_min_percent = target_min * 100.0
    target_max_percent = target_max * 100.0
    target_midpoint = MIDPOINT_TARGET_SHARE

    logger.info(
        "Starting shared-custody SSAG range estimate: payor=%s recipient=%s spousal_payor=%s spousal_recipient=%s children=%s override_child=%s",
        payor_income,
        recipient_income,
        active_payor_spousal_income,
        active_recipient_spousal_income,
        num_children,
        child_support_override_monthly,
    )

    def calculate_financial_state(*, spousal_support_annual: float) -> dict:
        current_payor_taxable_income = max(payor_income - spousal_support_annual, 0.0)
        current_recipient_taxable_income = recipient_income + spousal_support_annual
        payor_tax_profile = calculate_tax_profile(
            current_payor_taxable_income,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
            claim_eligible_dependant=payor_claim_eligible_dependant,
        )
        recipient_tax_profile = calculate_tax_profile(
            current_recipient_taxable_income,
            jurisdiction_code=jurisdiction_code,
            tax_year=tax_year,
            claim_eligible_dependant=recipient_claim_eligible_dependant,
        )
        payor_tax = payor_tax_profile["totalDeductions"]
        recipient_tax = recipient_tax_profile["totalDeductions"]
        benefits = calculate_shared_custody_benefits(
            jurisdiction_code=jurisdiction_code,
            payor_adjusted_family_net_income=current_payor_taxable_income,
            recipient_adjusted_family_net_income=current_recipient_taxable_income,
            num_children=num_children,
            children_under_six=children_under_six,
            tax_year=tax_year,
            payor_registered_children=payor_registered_children,
            recipient_registered_children=recipient_registered_children,
            payor_household_adults=payor_household_adults,
            recipient_household_adults=recipient_household_adults,
            payor_children_under_six=payor_children_under_six,
            recipient_children_under_six=recipient_children_under_six,
        )
        payor_benefits = benefits["payor"]["totalAnnual"]
        recipient_benefits = benefits["recipient"]["totalAnnual"]

        actual_ndi_payor = (
            payor_income
            - payor_tax
            - spousal_support_annual
            - actual_net_child_support_annual
            + payor_benefits
        )
        actual_ndi_recipient = (
            recipient_income
            - recipient_tax
            + spousal_support_annual
            + actual_net_child_support_annual
            + recipient_benefits
        )
        formula_ndi_payor = (
            active_payor_spousal_income
            - payor_tax
            - spousal_support_annual
            - formula_payor_child_support_annual
            + payor_benefits
        )
        formula_ndi_recipient = (
            active_recipient_spousal_income
            - recipient_tax
            + spousal_support_annual
            - formula_recipient_child_support_annual
            + recipient_benefits
        )
        actual_total_ndi = actual_ndi_payor + actual_ndi_recipient
        formula_total_ndi = formula_ndi_payor + formula_ndi_recipient
        actual_share = (
            EQUALIZATION_TARGET_SHARE
            if actual_total_ndi <= 0
            else (actual_ndi_recipient / actual_total_ndi) * 100.0
        )
        formula_share = (
            EQUALIZATION_TARGET_SHARE
            if formula_total_ndi <= 0
            else (formula_ndi_recipient / formula_total_ndi) * 100.0
        )

        return {
            "payorTaxableIncome": current_payor_taxable_income,
            "recipientTaxableIncome": current_recipient_taxable_income,
            "payorTaxProfile": payor_tax_profile,
            "recipientTaxProfile": recipient_tax_profile,
            "payorTax": payor_tax,
            "recipientTax": recipient_tax,
            "benefits": benefits,
            "payorBenefitsAnnual": payor_benefits,
            "recipientBenefitsAnnual": recipient_benefits,
            "actualNdiPayor": actual_ndi_payor,
            "actualNdiRecipient": actual_ndi_recipient,
            "actualRecipientSharePercent": actual_share,
            "formulaNdiPayor": formula_ndi_payor,
            "formulaNdiRecipient": formula_ndi_recipient,
            "formulaRecipientSharePercent": formula_share,
        }

    def snapshot(iteration: int, spousal_support_annual: float, state: dict, current_step: float) -> dict:
        return {
            "iteration": iteration,
            "spousalSupportAnnual": round(spousal_support_annual, 2),
            "netChildSupportAnnual": round(ndi_child_support["netAnnual"], 2),
            "payorBenefitsAnnual": round(state["payorBenefitsAnnual"], 2),
            "recipientBenefitsAnnual": round(state["recipientBenefitsAnnual"], 2),
            "ndiPayor": round(state["actualNdiPayor"], 2),
            "ndiRecipient": round(state["actualNdiRecipient"], 2),
            "recipientSharePercent": round(state["formulaRecipientSharePercent"], 2),
            "actualRecipientSharePercent": round(state["actualRecipientSharePercent"], 2),
            "step": round(current_step, 2),
        }

    def solve_support_for_share(
        *,
        target_share_percent: float,
        share_key: str,
        capture_history: bool,
    ) -> tuple[float, dict, list[dict]]:
        lower = 0.0
        upper = max(active_payor_spousal_income, payor_income, 1.0)
        lower_state = calculate_financial_state(spousal_support_annual=lower)
        upper_state = calculate_financial_state(spousal_support_annual=upper)
        while upper_state[share_key] < target_share_percent and upper < 2_000_000:
            upper *= 1.5
            upper_state = calculate_financial_state(spousal_support_annual=upper)

        local_history: list[dict] = []
        current_step = step
        previous_delta: float | None = None
        final_support = lower
        final_state = lower_state
        for iteration in range(max_iterations):
            midpoint = (lower + upper) / 2.0
            state = calculate_financial_state(spousal_support_annual=midpoint)
            current_share = state[share_key]
            delta = current_share - target_share_percent
            if capture_history:
                local_history.append(snapshot(iteration, midpoint, state, current_step))

            final_support = midpoint
            final_state = state
            if abs(delta) <= tolerance or abs(upper - lower) <= 1.0:
                break

            if delta < 0:
                lower = midpoint
            else:
                upper = midpoint

            if previous_delta is not None and (previous_delta * delta) < 0:
                current_step = max(1.0, current_step / 2.0)
            previous_delta = delta

        return round(final_support, 2), final_state, local_history

    low_support_annual, low_state, _ = solve_support_for_share(
        target_share_percent=target_min_percent,
        share_key="formulaRecipientSharePercent",
        capture_history=False,
    )
    mid_support_annual, mid_state, mid_history = solve_support_for_share(
        target_share_percent=target_midpoint,
        share_key="formulaRecipientSharePercent",
        capture_history=True,
    )
    high_support_annual, high_state, _ = solve_support_for_share(
        target_share_percent=target_max_percent,
        share_key="formulaRecipientSharePercent",
        capture_history=False,
    )
    equalization_support_annual, equalization_state, _ = solve_support_for_share(
        target_share_percent=EQUALIZATION_TARGET_SHARE,
        share_key="actualRecipientSharePercent",
        capture_history=False,
    )
    low_end_extended_to_equalization = equalization_support_annual > low_support_annual
    if low_end_extended_to_equalization:
        low_support_annual = equalization_support_annual
        low_state = equalization_state

    range_results = {
        "formulaType": "with_child_support_shared_custody",
        "lowAnnual": round(low_support_annual, 2),
        "midAnnual": round(mid_support_annual, 2),
        "highAnnual": round(high_support_annual, 2),
        "lowMonthly": round(low_support_annual / 12.0, 2),
        "midMonthly": round(mid_support_annual / 12.0, 2),
        "highMonthly": round(high_support_annual / 12.0, 2),
        "lowEndExtendedToEqualization": low_end_extended_to_equalization,
        "equalizationAnnual": round(equalization_support_annual, 2),
        "equalizationMonthly": round(equalization_support_annual / 12.0, 2),
    }

    if fixed_total_support_annual is None:
        estimated_spousal_support_annual = mid_support_annual
        final_financial_state = mid_state
        history = mid_history
        selected_range_point = "mid"
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
        estimated_spousal_support_annual = (
            fixed_total_support_annual - actual_net_child_support_annual
        )
        final_financial_state = calculate_financial_state(
            spousal_support_annual=estimated_spousal_support_annual
        )
        history = [snapshot(0, estimated_spousal_support_annual, final_financial_state, 0.0)]
        selected_range_point = "fixed_total_override"

    payor_tax_before_support_profile = calculate_tax_profile(
        payor_income,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
        claim_eligible_dependant=payor_claim_eligible_dependant,
    )
    recipient_tax_before_support_profile = calculate_tax_profile(
        recipient_income,
        jurisdiction_code=jurisdiction_code,
        tax_year=tax_year,
        claim_eligible_dependant=recipient_claim_eligible_dependant,
    )
    payor_tax_before_support_deduction = payor_tax_before_support_profile["totalDeductions"]
    recipient_tax_before_support_inclusion = recipient_tax_before_support_profile["totalDeductions"]
    payor_tax = final_financial_state["payorTax"]
    recipient_tax = final_financial_state["recipientTax"]
    payor_tax_deduction_benefit = max(payor_tax_before_support_deduction - payor_tax, 0.0)
    recipient_tax_support_cost = max(recipient_tax - recipient_tax_before_support_inclusion, 0.0)
    actual_net_income_payor = final_financial_state["actualNdiPayor"]
    actual_net_income_recipient = final_financial_state["actualNdiRecipient"]
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
    duration = _duration_metadata(
        relationship_years=relationship_years,
        recipient_age_at_separation=recipient_age_at_separation,
        years_until_child_full_time_school=years_until_child_full_time_school,
        years_until_child_finishes_high_school=years_until_child_finishes_high_school,
    )
    assumptions = {
        "formulaType": "with_child_support_shared_custody",
        "targetRangePercent": {
            "min": round(target_min_percent, 2),
            "mid": round(target_midpoint, 2),
            "max": round(target_max_percent, 2),
            "equalization": EQUALIZATION_TARGET_SHARE,
        },
        "selectedRangePoint": selected_range_point,
        "eligibleDependantClaimant": normalized_eligible_dependant_claimant,
        "benefits": final_financial_state["benefits"]["assumptions"],
        "durationInputsProvided": duration["inputsProvided"],
        "childSupportTableYear": child_support["tableYear"],
    }
    overrides = {
        "childSupport": {
            "overrideApplied": child_support["overrideApplied"],
            "guidelineNetMonthly": round(child_support["guidelineNetMonthly"], 2),
            "guidelineNetAnnual": round(child_support["guidelineNetAnnual"], 2),
            "appliedNetMonthly": round(child_support["netMonthly"], 2),
            "appliedNetAnnual": round(child_support["netAnnual"], 2),
        },
        "spousalSupport": {
            "fixedTotalSupportApplied": fixed_total_support_annual is not None,
            "fixedTotalSupportAnnual": (
                None if fixed_total_support_annual is None else round(fixed_total_support_annual, 2)
            ),
            "selectedRangePoint": selected_range_point,
            "selectedAnnual": round(estimated_spousal_support_annual, 2),
            "selectedMonthly": round(estimated_spousal_support_annual / 12.0, 2),
        },
        "incomeAdjustments": {
            "separateSpousalIncomesApplied": (
                payor_spousal_income is not None or recipient_spousal_income is not None
            ),
            "payorActualIncome": round(payor_income, 2),
            "recipientActualIncome": round(recipient_income, 2),
            "payorSpousalIncome": round(active_payor_spousal_income, 2),
            "recipientSpousalIncome": round(active_recipient_spousal_income, 2),
        },
    }
    calculation_trace = {
        "traceVersion": 1,
        "assumptions": assumptions,
        "overrides": overrides,
        "childSupport": {
            "actual": child_support,
            "formulaNdi": ndi_child_support,
        },
        "ssag": {
            "range": range_results,
            "selectedRangePoint": selected_range_point,
            "estimatedAnnual": round(estimated_spousal_support_annual, 2),
            "estimatedMonthly": round(estimated_spousal_support_annual / 12.0, 2),
            "duration": duration,
            "iterations": len(history),
            "history": history,
        },
        "tax": {
            "payorBeforeSupport": payor_tax_before_support_profile,
            "payorAfterSupport": final_financial_state["payorTaxProfile"],
            "recipientBeforeSupport": recipient_tax_before_support_profile,
            "recipientAfterSupport": final_financial_state["recipientTaxProfile"],
        },
        "benefits": final_financial_state["benefits"],
        "finalState": {
            "payorTaxableIncome": round(final_financial_state["payorTaxableIncome"], 2),
            "recipientTaxableIncome": round(final_financial_state["recipientTaxableIncome"], 2),
            "payorTax": round(payor_tax, 2),
            "recipientTax": round(recipient_tax, 2),
            "payorBenefitsAnnual": round(final_financial_state["payorBenefitsAnnual"], 2),
            "recipientBenefitsAnnual": round(final_financial_state["recipientBenefitsAnnual"], 2),
            "ndiPayor": round(final_financial_state["actualNdiPayor"], 2),
            "ndiRecipient": round(final_financial_state["actualNdiRecipient"], 2),
            "formulaRecipientSharePercent": round(
                final_financial_state["formulaRecipientSharePercent"],
                2,
            ),
            "actualRecipientSharePercent": round(
                final_financial_state["actualRecipientSharePercent"],
                2,
            ),
        },
        "equivalentBeforeTaxIncome": {
            "payor": round(payor_equivalent_before_tax_income, 2),
            "recipient": round(recipient_equivalent_before_tax_income, 2),
        },
    }

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
        "relationshipYears": None if relationship_years is None else round(relationship_years, 2),
        "recipientAgeAtSeparation": (
            None
            if recipient_age_at_separation is None
            else round(recipient_age_at_separation, 2)
        ),
        "eligibleDependantClaimant": normalized_eligible_dependant_claimant,
        "payorRegisteredChildren": normalized_payor_registered_children,
        "recipientRegisteredChildren": normalized_recipient_registered_children,
        "payorHouseholdAdults": payor_household_adults,
        "recipientHouseholdAdults": recipient_household_adults,
        "payorChildrenUnderSix": (
            None if payor_children_under_six is None else int(payor_children_under_six)
        ),
        "recipientChildrenUnderSix": (
            None if recipient_children_under_six is None else int(recipient_children_under_six)
        ),
        "yearsUntilChildFullTimeSchool": (
            None
            if years_until_child_full_time_school is None
            else round(years_until_child_full_time_school, 2)
        ),
        "yearsUntilChildFinishesHighSchool": (
            None
            if years_until_child_finishes_high_school is None
            else round(years_until_child_finishes_high_school, 2)
        ),
        "childSupportOverrideMonthly": (
            None
            if child_support_override_monthly is None
            else round(child_support_override_monthly, 2)
        ),
        "fixedTotalSupportAnnual": (
            None if fixed_total_support_annual is None else round(fixed_total_support_annual, 2)
        ),
        "targetRangePercent": {
            "min": round(target_min_percent, 2),
            "max": round(target_max_percent, 2),
        },
        "assumptions": assumptions,
        "overrides": overrides,
        "spousalSupportRange": range_results,
        "duration": duration,
        "estimatedSpousalSupportAnnual": round(estimated_spousal_support_annual, 2),
        "estimatedSpousalSupportMonthly": round(estimated_spousal_support_annual / 12.0, 2),
        "childSupport": child_support,
        "ndiChildSupport": ndi_child_support,
        "payorTaxableIncome": round(final_financial_state["payorTaxableIncome"], 2),
        "recipientTaxableIncome": round(final_financial_state["recipientTaxableIncome"], 2),
        "payorTaxProfile": final_financial_state["payorTaxProfile"],
        "recipientTaxProfile": final_financial_state["recipientTaxProfile"],
        "payorTaxBeforeSupportProfile": payor_tax_before_support_profile,
        "payorTaxBeforeSupportDeduction": round(payor_tax_before_support_deduction, 2),
        "payorTax": round(payor_tax, 2),
        "payorTaxDeductionBenefit": round(payor_tax_deduction_benefit, 2),
        "recipientTaxBeforeSupportProfile": recipient_tax_before_support_profile,
        "recipientTaxBeforeSupportInclusion": round(recipient_tax_before_support_inclusion, 2),
        "recipientTax": round(recipient_tax, 2),
        "recipientTaxSupportCost": round(recipient_tax_support_cost, 2),
        "benefits": final_financial_state["benefits"],
        "actualNetIncomePayor": round(actual_net_income_payor, 2),
        "actualNetIncomeRecipient": round(actual_net_income_recipient, 2),
        "payorEquivalentBeforeTaxIncome": round(payor_equivalent_before_tax_income, 2),
        "recipientEquivalentBeforeTaxIncome": round(
            recipient_equivalent_before_tax_income,
            2,
        ),
        "ndiPayor": round(final_financial_state["actualNdiPayor"], 2),
        "ndiRecipient": round(final_financial_state["actualNdiRecipient"], 2),
        "recipientSharePercent": round(
            final_financial_state["formulaRecipientSharePercent"],
            2,
        ),
        "actualRecipientSharePercent": round(
            final_financial_state["actualRecipientSharePercent"],
            2,
        ),
        "iterations": len(history),
        "history": history,
        "calculationTrace": calculation_trace,
    }
