from pytest import approx

from support_calculator.benefits import calculate_shared_custody_benefits
from support_calculator.calculations import calculate_child_support_breakdown
from support_calculator.spousal_support import calculate_spousal_support_estimate
from support_calculator.tables import (
    load_default_child_support_registry,
    load_default_child_support_table,
)
from support_calculator.tax import (
    calculate_bc_tax_approx,
    calculate_tax_approx,
    calculate_tax_profile,
)


def test_child_support_registry_loads_all_non_quebec_jurisdictions():
    registry = load_default_child_support_registry()

    assert registry.supported_jurisdictions() == [
        {"code": "AB", "name": "Alberta"},
        {"code": "BC", "name": "British Columbia"},
        {"code": "MB", "name": "Manitoba"},
        {"code": "NB", "name": "New Brunswick"},
        {"code": "NL", "name": "Newfoundland and Labrador"},
        {"code": "NS", "name": "Nova Scotia"},
        {"code": "NT", "name": "Northwest Territories"},
        {"code": "NU", "name": "Nunavut"},
        {"code": "ON", "name": "Ontario"},
        {"code": "PE", "name": "Prince Edward Island"},
        {"code": "SK", "name": "Saskatchewan"},
        {"code": "YT", "name": "Yukon"},
    ]
    assert registry.supported_children() == [1, 2, 3, 4, 5, 6, 7]


def test_child_support_table_amount_matches_expected_example():
    table = load_default_child_support_table()

    assert table.amount(3, 200000) == approx(3582.0, rel=1e-4)
    assert table.amount(3, 54078.54) == approx(1106.0, rel=1e-4)
    assert table.amount(7, 200000) == approx(5297.0, rel=1e-4)


def test_child_support_tables_vary_by_jurisdiction():
    alberta_table = load_default_child_support_table("AB")
    ontario_table = load_default_child_support_table("ON")
    newfoundland_table = load_default_child_support_table("NL")

    assert alberta_table.amount(3, 200000) == approx(3594.0, rel=1e-4)
    assert ontario_table.amount(3, 200000) == approx(3428.0, rel=1e-4)
    assert newfoundland_table.amount(3, 200000) == approx(3442.0, rel=1e-4)


def test_child_support_uses_updated_2025_tables_for_later_tax_years():
    table = load_default_child_support_table("BC", table_year=2025)

    assert table.amount(2, 175000) == approx(2535.0, rel=1e-4)
    assert table.amount(2, 20000) == approx(219.0, rel=1e-4)


def test_child_support_breakdown_returns_direction_and_annual_values():
    result = calculate_child_support_breakdown(
        num_children=2,
        payor_income=244658,
        recipient_income=30600,
    )

    assert result["direction"] == "payor_to_recipient"
    assert result["netMonthly"] == approx(2782.96, rel=1e-4)
    assert result["netAnnual"] == approx(33395.52, rel=1e-4)
    assert result["recipientTableIncome"] == 30600


def test_child_support_breakdown_can_apply_net_transfer_override():
    result = calculate_child_support_breakdown(
        num_children=2,
        payor_income=175000,
        recipient_income=20000,
        net_monthly_override=2548,
        table=load_default_child_support_table("BC", table_year=2025),
    )

    assert result["tableYear"] == 2025
    assert result["guidelineNetMonthly"] == approx(2316.0, rel=1e-4)
    assert result["netMonthly"] == approx(2548.0, rel=1e-4)
    assert result["overrideApplied"] is True


def test_spousal_support_estimate_converges_inside_target_band():
    result = calculate_spousal_support_estimate(
        payor_income=244658,
        recipient_income=30600,
        num_children=2,
        children_under_six=0,
        tax_year=2025,
    )

    assert 40 <= result["recipientSharePercent"] <= 46
    assert result["estimatedSpousalSupportAnnual"] > 0
    assert result["iterations"] > 1
    assert result["iterations"] < 300
    assert result["taxYear"] == 2025
    assert result["payorTaxBeforeSupportDeduction"] > result["payorTax"]
    assert result["payorTaxDeductionBenefit"] > 0
    assert result["recipientTax"] > result["recipientTaxBeforeSupportInclusion"]
    assert result["recipientTaxSupportCost"] > 0
    assert result["benefits"]["recipient"]["totalAnnual"] > 0
    assert result["benefits"]["jurisdiction"] == "BC"
    assert result["benefits"]["lineItems"][0]["label"] == "Canada child benefit"
    assert result["ndiChildSupport"]["netAnnual"] == result["childSupport"]["netAnnual"]
    assert result["childSupport"]["tableYear"] == 2025
    assert result["assumptions"]["selectedRangePoint"] == "mid"
    assert result["overrides"]["childSupport"]["overrideApplied"] is False
    assert result["calculationTrace"]["traceVersion"] == 1
    assert result["calculationTrace"]["ssag"]["selectedRangePoint"] == "mid"
    assert result["calculationTrace"]["ssag"]["estimatedAnnual"] == result["estimatedSpousalSupportAnnual"]
    assert result["calculationTrace"]["tax"]["payorAfterSupport"] == result["payorTaxProfile"]
    assert result["calculationTrace"]["benefits"] == result["benefits"]
    assert result["payorTaxableIncome"] == approx(
        result["payorIncome"] - result["estimatedSpousalSupportAnnual"],
        rel=1e-4,
    )
    assert result["history"][-1]["recipientSharePercent"] == result["recipientSharePercent"]


def test_spousal_support_estimate_can_use_separate_spousal_incomes():
    result = calculate_spousal_support_estimate(
        payor_income=244658,
        recipient_income=30600,
        payor_spousal_income=190000,
        recipient_spousal_income=45000,
        num_children=2,
        children_under_six=0,
        tax_year=2025,
    )

    assert result["payorIncome"] == 244658
    assert result["recipientIncome"] == 30600
    assert result["payorSpousalIncome"] == 190000
    assert result["recipientSpousalIncome"] == 45000
    assert result["childSupport"]["payorIncome"] == 244658
    assert result["childSupport"]["recipientIncome"] == 30600
    assert result["ndiChildSupport"]["payorIncome"] == 190000
    assert result["ndiChildSupport"]["recipientIncome"] == 45000
    assert result["history"][-1]["netChildSupportAnnual"] == result["ndiChildSupport"]["netAnnual"]
    assert result["payorTaxableIncome"] == approx(
        result["payorIncome"] - result["estimatedSpousalSupportAnnual"],
        rel=1e-4,
    )
    assert result["recipientTaxableIncome"] == approx(
        result["recipientIncome"] + result["estimatedSpousalSupportAnnual"],
        rel=1e-4,
    )
    expected_benefits = calculate_shared_custody_benefits(
        jurisdiction_code="BC",
        payor_adjusted_family_net_income=result["payorTaxableIncome"],
        recipient_adjusted_family_net_income=result["recipientTaxableIncome"],
        num_children=2,
        children_under_six=0,
        tax_year=2025,
    )
    assert result["benefits"] == expected_benefits
    assert result["actualNetIncomePayor"] == approx(
        result["payorIncome"]
        - result["payorTax"]
        - result["estimatedSpousalSupportAnnual"]
        - result["childSupport"]["netAnnual"]
        + result["benefits"]["payor"]["totalAnnual"],
        rel=1e-4,
    )
    assert result["actualNetIncomeRecipient"] == approx(
        result["recipientIncome"]
        - result["recipientTax"]
        + result["estimatedSpousalSupportAnnual"]
        + result["childSupport"]["netAnnual"]
        + result["benefits"]["recipient"]["totalAnnual"],
        rel=1e-4,
    )


def test_spousal_support_estimate_can_use_fixed_total_support():
    result = calculate_spousal_support_estimate(
        payor_income=244658,
        recipient_income=30600,
        payor_spousal_income=190000,
        recipient_spousal_income=45000,
        fixed_total_support_annual=50_000,
        num_children=2,
        children_under_six=0,
        tax_year=2025,
    )

    assert result["fixedTotalSupportAnnual"] == 50_000
    assert result["iterations"] == 1
    assert result["history"][0]["iteration"] == 0
    assert result["ndiChildSupport"] == result["childSupport"]
    assert result["estimatedSpousalSupportAnnual"] == approx(
        50_000 - result["childSupport"]["netAnnual"],
        rel=1e-4,
    )
    assert result["assumptions"]["selectedRangePoint"] == "fixed_total_override"
    assert result["overrides"]["spousalSupport"]["fixedTotalSupportApplied"] is True
    assert result["calculationTrace"]["ssag"]["selectedRangePoint"] == "fixed_total_override"
    assert result["actualNetIncomePayor"] == approx(
        result["payorIncome"]
        - result["payorTax"]
        - result["estimatedSpousalSupportAnnual"]
        - result["childSupport"]["netAnnual"]
        + result["benefits"]["payor"]["totalAnnual"],
        rel=1e-4,
    )


def test_shared_custody_benefits_include_low_income_credits():
    result = calculate_shared_custody_benefits(
        jurisdiction_code="BC",
        payor_adjusted_family_net_income=40_000,
        recipient_adjusted_family_net_income=25_000,
        num_children=2,
        children_under_six=1,
        tax_year=2023,
    )

    assert result["payor"]["totalAnnual"] == approx(9_851.92, rel=1e-4)
    assert result["recipient"]["totalAnnual"] == approx(10_170.0, rel=1e-4)
    assert result["recipient"]["canadaChildBenefitAnnual"] > result["payor"]["canadaChildBenefitAnnual"]
    assert [item["label"] for item in result["lineItems"]] == [
        "Canada child benefit",
        "GST/HST credit",
        "B.C. family benefit",
        "B.C. climate action credit",
    ]


def test_shared_custody_benefits_skip_bc_specific_credits_outside_bc():
    result = calculate_shared_custody_benefits(
        jurisdiction_code="ON",
        payor_adjusted_family_net_income=40_000,
        recipient_adjusted_family_net_income=25_000,
        num_children=2,
        children_under_six=1,
        tax_year=2023,
    )

    assert result["jurisdiction"] == "ON"
    assert [item["label"] for item in result["lineItems"]] == [
        "Canada child benefit",
        "GST/HST credit",
    ]
    assert "bcFamilyBenefitAnnual" not in result["payor"]
    assert "bcClimateActionCreditAnnual" not in result["recipient"]


def test_shared_custody_benefits_support_explicit_child_allocation():
    default_result = calculate_shared_custody_benefits(
        jurisdiction_code="BC",
        payor_adjusted_family_net_income=40_000,
        recipient_adjusted_family_net_income=25_000,
        num_children=2,
        children_under_six=1,
        tax_year=2025,
    )
    explicit_result = calculate_shared_custody_benefits(
        jurisdiction_code="BC",
        payor_adjusted_family_net_income=40_000,
        recipient_adjusted_family_net_income=25_000,
        num_children=2,
        children_under_six=1,
        tax_year=2025,
        payor_registered_children=0,
        recipient_registered_children=2,
        payor_household_adults=2,
        recipient_household_adults=1,
        payor_children_under_six=0,
        recipient_children_under_six=1,
    )

    assert default_result["assumptions"]["explicitAllocation"] is False
    assert explicit_result["assumptions"]["explicitAllocation"] is True
    assert explicit_result["assumptions"]["payorRegisteredChildren"] == 0
    assert explicit_result["assumptions"]["recipientRegisteredChildren"] == 2
    assert explicit_result["assumptions"]["payorHouseholdAdults"] == 2
    assert explicit_result["assumptions"]["recipientChildrenUnderSix"] == 1
    assert explicit_result["payor"]["canadaChildBenefitAnnual"] == 0
    assert (
        explicit_result["recipient"]["canadaChildBenefitAnnual"]
        > default_result["recipient"]["canadaChildBenefitAnnual"]
    )
    assert explicit_result["recipient"]["totalAnnual"] > default_result["recipient"]["totalAnnual"]
    assert explicit_result["payor"]["totalAnnual"] < default_result["payor"]["totalAnnual"]


def test_bc_tax_approx_is_progressive():
    low_income_tax = calculate_bc_tax_approx(50_000, tax_year=2023)
    high_income_tax = calculate_bc_tax_approx(200_000, tax_year=2023)

    assert low_income_tax == approx(9_937.24, rel=1e-4)
    assert high_income_tax > low_income_tax


def test_tax_year_changes_indexed_tax_result():
    assert calculate_bc_tax_approx(50_000, tax_year=2019) > calculate_bc_tax_approx(50_000, tax_year=2025)


def test_tax_approx_varies_by_jurisdiction():
    bc_tax = calculate_tax_approx(200_000, jurisdiction_code="BC", tax_year=2023)
    on_tax = calculate_tax_approx(200_000, jurisdiction_code="ON", tax_year=2023)
    ab_tax = calculate_tax_approx(200_000, jurisdiction_code="AB", tax_year=2023)

    assert bc_tax == approx(66_190.89, rel=1e-4)
    assert on_tax == approx(64_683.93, rel=1e-4)
    assert ab_tax == approx(64_721.25, rel=1e-4)
    assert bc_tax > on_tax > 0


def test_tax_profile_breaks_out_income_tax_and_payroll_deductions():
    profile = calculate_tax_profile(50_000, jurisdiction_code="BC", tax_year=2023)

    assert profile["incomeTax"] == approx(6_355.49, rel=1e-4)
    assert profile["totalCppContribution"] == approx(2_766.75, rel=1e-4)
    assert profile["eiPremium"] == approx(815.0, rel=1e-4)
    assert profile["payrollDeductions"] == approx(3_581.75, rel=1e-4)
    assert profile["totalDeductions"] == approx(9_937.24, rel=1e-4)
    assert profile["taxableIncome"] == approx(49_535.0, rel=1e-4)


def test_tax_profile_can_apply_eligible_dependant_credit():
    baseline = calculate_tax_profile(50_000, jurisdiction_code="BC", tax_year=2025)
    claimant = calculate_tax_profile(
        50_000,
        jurisdiction_code="BC",
        tax_year=2025,
        claim_eligible_dependant=True,
    )

    assert claimant["eligibleDependantClaimed"] is True
    assert claimant["federalEligibleDependantAmount"] > 0
    assert claimant["provincialEligibleDependantAmount"] > 0
    assert claimant["federalEligibleDependantCredit"] > 0
    assert claimant["provincialEligibleDependantCredit"] > 0
    assert claimant["totalDeductions"] < baseline["totalDeductions"]


def test_spousal_support_estimate_supports_ontario():
    result = calculate_spousal_support_estimate(
        payor_income=244658,
        recipient_income=30600,
        num_children=2,
        children_under_six=0,
        tax_year=2025,
        table=load_default_child_support_table("ON"),
    )

    assert result["jurisdiction"] == "ON"
    assert 40 <= result["recipientSharePercent"] <= 46
    assert result["estimatedSpousalSupportAnnual"] > 0
    assert [item["label"] for item in result["benefits"]["lineItems"]] == [
        "Canada child benefit",
        "GST/HST credit",
    ]


def test_spousal_support_estimate_returns_range_and_duration_metadata():
    result = calculate_spousal_support_estimate(
        payor_income=175000,
        recipient_income=20000,
        child_support_override_monthly=2548,
        num_children=2,
        tax_year=2026,
        relationship_years=14.5,
        recipient_age_at_separation=46,
        years_until_child_full_time_school=1,
        years_until_child_finishes_high_school=14,
    )

    assert result["spousalSupportRange"]["lowAnnual"] < result["spousalSupportRange"]["midAnnual"]
    assert result["spousalSupportRange"]["midAnnual"] < result["spousalSupportRange"]["highAnnual"]
    assert result["duration"]["durationType"] == "indefinite"
    assert result["duration"]["minYears"] == approx(7.25, rel=1e-4)
    assert result["duration"]["maxYears"] == approx(14.5, rel=1e-4)
    assert result["childSupport"]["overrideApplied"] is True


def test_spousal_support_can_model_claimant_and_household_allocation():
    baseline = calculate_spousal_support_estimate(
        payor_income=175000,
        recipient_income=20000,
        num_children=2,
        children_under_six=1,
        tax_year=2025,
    )
    allocated = calculate_spousal_support_estimate(
        payor_income=175000,
        recipient_income=20000,
        num_children=2,
        children_under_six=1,
        tax_year=2025,
        payor_registered_children=0,
        recipient_registered_children=2,
        payor_household_adults=2,
        recipient_household_adults=1,
        payor_children_under_six=0,
        recipient_children_under_six=1,
        eligible_dependant_claimant="recipient",
    )

    assert allocated["eligibleDependantClaimant"] == "recipient"
    assert allocated["payorRegisteredChildren"] == 0
    assert allocated["recipientRegisteredChildren"] == 2
    assert allocated["benefits"]["assumptions"]["explicitAllocation"] is True
    assert allocated["recipientTaxProfile"]["eligibleDependantClaimed"] is True
    assert allocated["payorTaxProfile"]["eligibleDependantClaimed"] is False
    assert allocated["recipientTax"] < baseline["recipientTax"]
    assert allocated["benefits"]["recipient"]["totalAnnual"] > baseline["benefits"]["recipient"]["totalAnnual"]
    assert allocated["benefits"]["payor"]["totalAnnual"] < baseline["benefits"]["payor"]["totalAnnual"]
    assert allocated["assumptions"]["benefits"]["explicitAllocation"] is True
    assert allocated["overrides"]["incomeAdjustments"]["separateSpousalIncomesApplied"] is False
    assert allocated["calculationTrace"]["assumptions"]["eligibleDependantClaimant"] == "recipient"
