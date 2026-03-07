import logging

from flask import Blueprint, current_app, jsonify, request

from .calculations import calculate_child_support_breakdown
from .spousal_support import calculate_spousal_support_estimate

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


@api_blueprint.get("/health")
def healthcheck():
    logger.debug("Healthcheck requested.")
    return jsonify({"status": "ok"})


@api_blueprint.get("/metadata")
def metadata():
    table = current_app.config["CHILD_SUPPORT_TABLE"]
    logger.info("Providing calculator metadata.")
    return jsonify(
        {
            "jurisdictions": [{"code": "BC", "name": "British Columbia"}],
            "supportedChildren": table.available_children(),
            "defaultTargetRangePercent": {"min": 40, "max": 46},
            "disclaimer": (
                "Child support uses the bundled BC table from the provided notebook. "
                "Spousal support is an estimate based on an approximate BC tax model."
            ),
        }
    )


@api_blueprint.post("/calculate/child-support")
def child_support():
    try:
        payload = _require_json_object()
        jurisdiction = payload.get("jurisdiction", "BC")
        if jurisdiction != "BC":
            raise ValueError("Only British Columbia is supported in this version.")

        result = calculate_child_support_breakdown(
            num_children=_require_integer(payload, "children"),
            payor_income=_require_number(payload, "payorIncome"),
            recipient_income=_require_number(payload, "recipientIncome"),
            table=current_app.config["CHILD_SUPPORT_TABLE"],
        )
    except ValueError as error:
        logger.warning("Invalid child support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated child support for %s children.", result["children"])
    return jsonify(result)


@api_blueprint.post("/calculate/spousal-support")
def spousal_support():
    try:
        payload = _require_json_object()
        jurisdiction = payload.get("jurisdiction", "BC")
        if jurisdiction != "BC":
            raise ValueError("Only British Columbia is supported in this version.")

        target_min_percent = _require_number(payload, "targetMinPercent")
        target_max_percent = _require_number(payload, "targetMaxPercent")
        if target_min_percent >= target_max_percent:
            raise ValueError("'targetMinPercent' must be less than 'targetMaxPercent'.")

        result = calculate_spousal_support_estimate(
            payor_income=_require_number(payload, "payorIncome"),
            recipient_income=_require_number(payload, "recipientIncome"),
            num_children=_require_integer(payload, "children"),
            target_range=(target_min_percent / 100.0, target_max_percent / 100.0),
            table=current_app.config["CHILD_SUPPORT_TABLE"],
        )
    except ValueError as error:
        logger.warning("Invalid spousal support request: %s", error)
        return jsonify({"error": str(error)}), 400

    logger.info("Calculated spousal support estimate for %s children.", result["children"])
    return jsonify(result)
