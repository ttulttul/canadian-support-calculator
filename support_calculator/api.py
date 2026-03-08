import logging

from flask import Blueprint, current_app, jsonify, request

from .calculations import calculate_child_support_breakdown
from .jurisdictions import spousal_support_jurisdictions
from .spousal_support import calculate_spousal_support_estimate
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
            "defaultTargetRangePercent": {"min": 40, "max": 46},
            "defaultTaxYear": DEFAULT_TAX_YEAR,
            "disclaimer": (
                "Child support uses bundled 2017 federal tables for all non-Quebec provinces "
                "and territories. Spousal support currently uses an indexed approximation of the "
                "2023 combined BC tax model plus annualized shared-custody family benefits and credits."
            ),
            "benefitAssumptions": (
                "Benefit estimates assume both parents are single households in a shared-custody "
                "offset scenario. Enter the count of children under age 6 for the Canada Child Benefit."
            ),
            "spousalSupportAssumptions": (
                "Spousal support is currently available only for British Columbia in this version."
            ),
        }
    )


@api_blueprint.post("/calculate/child-support")
def child_support():
    try:
        payload = _require_json_object()
        jurisdiction = str(payload.get("jurisdiction", "BC")).upper()
        table = current_app.config["CHILD_SUPPORT_TABLES"].for_jurisdiction(jurisdiction)

        result = calculate_child_support_breakdown(
            num_children=_require_integer(payload, "children"),
            payor_income=_require_number(payload, "payorIncome"),
            recipient_income=_require_number(payload, "recipientIncome"),
            table=table,
        )
        result["taxYear"] = _optional_tax_year(payload)
    except ValueError as error:
        logger.warning("Invalid child support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated child support for %s children.", result["children"])
    return jsonify(result)


@api_blueprint.post("/calculate/spousal-support")
def spousal_support():
    try:
        payload = _require_json_object()
        jurisdiction = str(payload.get("jurisdiction", "BC")).upper()
        if jurisdiction != "BC":
            raise ValueError(
                "Spousal support is currently supported only for British Columbia."
            )

        target_min_percent = _require_number(payload, "targetMinPercent")
        target_max_percent = _require_number(payload, "targetMaxPercent")
        if target_min_percent >= target_max_percent:
            raise ValueError("'targetMinPercent' must be less than 'targetMaxPercent'.")

        result = calculate_spousal_support_estimate(
            payor_income=_require_number(payload, "payorIncome"),
            recipient_income=_require_number(payload, "recipientIncome"),
            payor_spousal_income=_optional_number(payload, "payorSpousalIncome"),
            recipient_spousal_income=_optional_number(payload, "recipientSpousalIncome"),
            fixed_total_support_annual=_optional_number(payload, "fixedTotalSupportAnnual"),
            num_children=_require_integer(payload, "children"),
            children_under_six=_optional_children_under_six(payload),
            tax_year=_optional_tax_year(payload),
            target_range=(target_min_percent / 100.0, target_max_percent / 100.0),
            table=current_app.config["CHILD_SUPPORT_TABLES"].for_jurisdiction(jurisdiction),
        )
    except ValueError as error:
        logger.warning("Invalid spousal support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated spousal support estimate for %s children.", result["children"])
    return jsonify(result)
