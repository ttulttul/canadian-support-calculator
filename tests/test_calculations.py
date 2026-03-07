from pytest import approx

from support_calculator.calculations import calculate_child_support_breakdown
from support_calculator.spousal_support import calculate_spousal_support_estimate
from support_calculator.tables import load_default_child_support_table
from support_calculator.tax import calculate_bc_tax_approx


def test_child_support_table_amount_matches_expected_example():
    table = load_default_child_support_table()

    assert table.amount(3, 200000) == approx(3582.0, rel=1e-4)
    assert table.amount(3, 54078.54) == approx(1105.46, rel=1e-4)


def test_child_support_breakdown_returns_direction_and_annual_values():
    result = calculate_child_support_breakdown(
        num_children=2,
        payor_income=244658,
        recipient_income=30600,
    )

    assert result["direction"] == "payor_to_recipient"
    assert result["netMonthly"] == approx(2782.96, rel=1e-4)
    assert result["netAnnual"] == approx(33395.52, rel=1e-4)


def test_spousal_support_estimate_converges_inside_target_band():
    result = calculate_spousal_support_estimate(
        payor_income=244658,
        recipient_income=30600,
        num_children=2,
    )

    assert 40 <= result["recipientSharePercent"] <= 46
    assert result["estimatedSpousalSupportAnnual"] > 0
    assert result["iterations"] > 1
    assert result["iterations"] < 300
    assert result["history"][-1]["recipientSharePercent"] == result["recipientSharePercent"]


def test_bc_tax_approx_is_progressive():
    low_income_tax = calculate_bc_tax_approx(50_000)
    high_income_tax = calculate_bc_tax_approx(200_000)

    assert low_income_tax == approx(10_144.73, rel=1e-4)
    assert high_income_tax > low_income_tax
