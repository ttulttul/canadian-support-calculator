from pytest import approx

from support_calculator.benefits import calculate_shared_custody_benefits
from support_calculator.calculations import calculate_child_support_breakdown
from support_calculator.spousal_support import calculate_spousal_support_estimate
from support_calculator.tables import load_default_child_support_table
from support_calculator.tax import calculate_bc_tax_approx


def test_child_support_table_amount_matches_expected_example():
    table = load_default_child_support_table()

    assert table.amount(3, 200000) == approx(3582.0, rel=1e-4)
    assert table.amount(3, 54078.54) == approx(1106.0, rel=1e-4)
    assert table.amount(7, 200000) == approx(5297.0, rel=1e-4)


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
    assert result["ndiChildSupport"]["netAnnual"] == result["childSupport"]["netAnnual"]
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
        payor_adjusted_family_net_income=40_000,
        recipient_adjusted_family_net_income=25_000,
        num_children=2,
        children_under_six=1,
        tax_year=2023,
    )

    assert result["payor"]["totalAnnual"] == approx(9_851.92, rel=1e-4)
    assert result["recipient"]["totalAnnual"] == approx(10_170.0, rel=1e-4)
    assert result["recipient"]["canadaChildBenefitAnnual"] > result["payor"]["canadaChildBenefitAnnual"]


def test_bc_tax_approx_is_progressive():
    low_income_tax = calculate_bc_tax_approx(50_000, tax_year=2023)
    high_income_tax = calculate_bc_tax_approx(200_000, tax_year=2023)

    assert low_income_tax == approx(10_144.73, rel=1e-4)
    assert high_income_tax > low_income_tax


def test_tax_year_changes_indexed_tax_result():
    assert calculate_bc_tax_approx(50_000, tax_year=2019) > calculate_bc_tax_approx(50_000, tax_year=2025)
