import logging
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file

from .calculations import calculate_child_support_breakdown
from .jurisdictions import spousal_support_jurisdictions
from .pdf_report import render_support_report_pdf
from .source_references import CALCULATION_SOURCE_REFERENCES, filter_source_references
from .spousal_support import calculate_spousal_support_estimate
from .tables import child_support_table_year_for_tax_year, load_default_child_support_table
from .tax import DEFAULT_TAX_YEAR

logger = logging.getLogger(__name__)
api_blueprint = Blueprint("api", __name__, url_prefix="/api")


def _require_json_object() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def _require_number(payload: dict, key: str) -> float:
    value = payload.get(key)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'{key}' must be a number.") from error

    if number < 0:
        raise ValueError(f"'{key}' must be zero or greater.")
    return number


def _require_integer(payload: dict, key: str) -> int:
    value = payload.get(key)
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'{key}' must be an integer.") from error

    if number <= 0:
        raise ValueError(f"'{key}' must be greater than zero.")
    return number


def _optional_number(payload: dict, key: str) -> float | None:
    value = payload.get(key)
    if value in (None, ""):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'{key}' must be a number.") from error

    if number < 0:
        raise ValueError(f"'{key}' must be zero or greater.")
    return number


def _optional_integer(payload: dict, key: str, *, minimum: int = 0) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'{key}' must be an integer.") from error

    if number < minimum:
        comparator = "greater than zero" if minimum == 1 else f"greater than or equal to {minimum}"
        raise ValueError(f"'{key}' must be {comparator}.")
    return number


def _optional_eligible_dependant_claimant(payload: dict) -> str:
    value = str(payload.get("eligibleDependantClaimant", "none") or "none").lower()
    if value not in {"none", "payor", "recipient"}:
        raise ValueError("'eligibleDependantClaimant' must be one of 'none', 'payor', or 'recipient'.")
    return value


def _optional_tax_year(payload: dict) -> int:
    value = payload.get("taxYear", DEFAULT_TAX_YEAR)
    try:
        tax_year = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("'taxYear' must be an integer.") from error

    if tax_year <= 0:
        raise ValueError("'taxYear' must be greater than zero.")
    return tax_year


def _optional_children_under_six(payload: dict) -> int:
    value = payload.get("childrenUnderSix", 0)
    try:
        children_under_six = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("'childrenUnderSix' must be an integer.") from error

    if children_under_six < 0:
        raise ValueError("'childrenUnderSix' must be zero or greater.")
    return children_under_six


def _child_support_payload(payload: dict) -> dict:
    return {
        "jurisdiction": str(payload.get("jurisdiction", "BC")).upper(),
        "children": _require_integer(payload, "children"),
        "childrenUnderSix": _optional_children_under_six(payload),
        "taxYear": _optional_tax_year(payload),
        "payorIncome": _require_number(payload, "payorIncome"),
        "recipientIncome": _require_number(payload, "recipientIncome"),
    }


def _calculate_child_support_result(payload: dict) -> dict:
    normalized_payload = _child_support_payload(payload)
    table = load_default_child_support_table(
        normalized_payload["jurisdiction"],
        table_year=child_support_table_year_for_tax_year(normalized_payload["taxYear"]),
    )
    result = calculate_child_support_breakdown(
        num_children=normalized_payload["children"],
        payor_income=normalized_payload["payorIncome"],
        recipient_income=normalized_payload["recipientIncome"],
        net_monthly_override=_optional_number(payload, "childSupportOverrideMonthly"),
        table=table,
    )
    result["taxYear"] = normalized_payload["taxYear"]
    logger.debug("Built child support result for payload %s", normalized_payload)
    return result


def _calculate_spousal_support_result(payload: dict) -> dict:
    normalized_payload = _child_support_payload(payload)
    target_min_percent = _require_number(payload, "targetMinPercent")
    target_max_percent = _require_number(payload, "targetMaxPercent")
    if target_min_percent >= target_max_percent:
        raise ValueError("'targetMinPercent' must be less than 'targetMaxPercent'.")

    result = calculate_spousal_support_estimate(
        payor_income=normalized_payload["payorIncome"],
        recipient_income=normalized_payload["recipientIncome"],
        payor_spousal_income=_optional_number(payload, "payorSpousalIncome"),
        recipient_spousal_income=_optional_number(payload, "recipientSpousalIncome"),
        child_support_override_monthly=_optional_number(payload, "childSupportOverrideMonthly"),
        fixed_total_support_annual=_optional_number(payload, "fixedTotalSupportAnnual"),
        relationship_years=_optional_number(payload, "relationshipYears"),
        recipient_age_at_separation=_optional_number(payload, "recipientAgeAtSeparation"),
        years_until_child_full_time_school=_optional_number(
            payload,
            "yearsUntilChildFullTimeSchool",
        ),
        years_until_child_finishes_high_school=_optional_number(
            payload,
            "yearsUntilChildFinishesHighSchool",
        ),
        payor_registered_children=_optional_integer(payload, "payorRegisteredChildren", minimum=0),
        recipient_registered_children=_optional_integer(
            payload,
            "recipientRegisteredChildren",
            minimum=0,
        ),
        payor_household_adults=_optional_integer(payload, "payorHouseholdAdults", minimum=1) or 1,
        recipient_household_adults=(
            _optional_integer(payload, "recipientHouseholdAdults", minimum=1) or 1
        ),
        payor_children_under_six=_optional_integer(payload, "payorChildrenUnderSix", minimum=0),
        recipient_children_under_six=_optional_integer(
            payload,
            "recipientChildrenUnderSix",
            minimum=0,
        ),
        eligible_dependant_claimant=_optional_eligible_dependant_claimant(payload),
        num_children=normalized_payload["children"],
        children_under_six=normalized_payload["childrenUnderSix"],
        tax_year=normalized_payload["taxYear"],
        target_range=(target_min_percent / 100.0, target_max_percent / 100.0),
        table=load_default_child_support_table(
            normalized_payload["jurisdiction"],
            table_year=child_support_table_year_for_tax_year(normalized_payload["taxYear"]),
        ),
    )
    logger.debug("Built spousal support result for payload %s", normalized_payload)
    return result


@api_blueprint.get("/health")
def healthcheck():
    logger.debug("Healthcheck requested.")
    return jsonify({"status": "ok"})


@api_blueprint.get("/metadata")
def metadata():
    registry = current_app.config["CHILD_SUPPORT_TABLES"]
    logger.info("Providing calculator metadata.")
    return jsonify(
        {
            "jurisdictions": registry.supported_jurisdictions(),
            "spousalSupportJurisdictions": [
                {"code": jurisdiction.code, "name": jurisdiction.name}
                for jurisdiction in spousal_support_jurisdictions()
            ],
            "supportedChildren": registry.supported_children(),
            "supportedChildrenNote": "Six and seven children use the federal six-or-more table.",
            "sourceReferences": CALCULATION_SOURCE_REFERENCES,
            "defaultTargetRangePercent": {"min": 40, "max": 46},
            "defaultTaxYear": DEFAULT_TAX_YEAR,
            "disclaimer": (
                "Child support uses the 2017 federal tables before tax year 2025 and the "
                "updated October 1, 2025 federal tables for tax year 2025 onward. Spousal support uses a payroll-aware annual tax model with "
                "federal and provincial tax brackets, basic credits, CPP, EI, and annualized "
                "shared-custody family benefits."
            ),
            "benefitAssumptions": (
                "Benefit estimates default to single-household shared-custody, but can also model "
                "explicit child allocations, household adult counts, and under-6 allocations. "
                "Federal Canada Child Benefit and GST/HST credit are modeled for all supported "
                "jurisdictions; B.C. family benefits are included for British Columbia."
            ),
            "spousalSupportAssumptions": (
                "Spousal support is available for all supported non-Quebec jurisdictions and uses "
                "a with-child shared-custody SSAG-style range model with low, mid, and high "
                "estimates derived from formula NDI, plus duration metadata when relationship "
                "inputs are provided. Tax profiles can optionally apply a claimant-selected "
                "eligible dependant credit. The JSON response includes a structured calculation "
                "trace for audit and regression review."
            ),
        }
    )


@api_blueprint.post("/calculate/child-support")
def child_support():
    try:
        payload = _require_json_object()
        result = _calculate_child_support_result(payload)
    except ValueError as error:
        logger.warning("Invalid child support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated child support for %s children.", result["children"])
    return jsonify(result)


@api_blueprint.post("/calculate/spousal-support")
def spousal_support():
    try:
        payload = _require_json_object()
        result = _calculate_spousal_support_result(payload)
    except ValueError as error:
        logger.warning("Invalid spousal support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated spousal support estimate for %s children.", result["children"])
    return jsonify(result)


@api_blueprint.post("/export/report.pdf")
def export_report():
    try:
        payload = _require_json_object()
        child_support_result = _calculate_child_support_result(payload)
        spousal_support_result = _calculate_spousal_support_result(payload)
        pdf_bytes = render_support_report_pdf(
            scenario=_child_support_payload(payload),
            child_support=child_support_result,
            spousal_support=spousal_support_result,
            source_references=filter_source_references(
                has_child_support=True,
                has_spousal_support=True,
                benefit_line_items=spousal_support_result["benefits"]["lineItems"],
            ),
        )
    except ValueError as error:
        logger.warning("Invalid PDF export request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Generated PDF report for %s children.", child_support_result["children"])
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="canadian-support-calculator-report.pdf",
    )
