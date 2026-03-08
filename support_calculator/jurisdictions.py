import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Jurisdiction:
    code: str
    name: str
    child_support_section_id: int | None = None


NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS: tuple[Jurisdiction, ...] = (
    Jurisdiction(code="AB", name="Alberta", child_support_section_id=1004712),
    Jurisdiction(code="BC", name="British Columbia", child_support_section_id=1004610),
    Jurisdiction(code="MB", name="Manitoba", child_support_section_id=1004576),
    Jurisdiction(code="NB", name="New Brunswick", child_support_section_id=1004542),
    Jurisdiction(
        code="NL",
        name="Newfoundland and Labrador",
        child_support_section_id=1004746,
    ),
    Jurisdiction(code="NS", name="Nova Scotia", child_support_section_id=1004508),
    Jurisdiction(
        code="NT",
        name="Northwest Territories",
        child_support_section_id=1004814,
    ),
    Jurisdiction(code="NU", name="Nunavut", child_support_section_id=1004848),
    Jurisdiction(code="ON", name="Ontario", child_support_section_id=1004440),
    Jurisdiction(
        code="PE",
        name="Prince Edward Island",
        child_support_section_id=1004644,
    ),
    Jurisdiction(code="SK", name="Saskatchewan", child_support_section_id=1004678),
    Jurisdiction(code="YT", name="Yukon", child_support_section_id=1004780),
)

SPOUSAL_SUPPORT_JURISDICTION_CODES: tuple[str, ...] = ("BC",)

JURISDICTIONS_BY_CODE: dict[str, Jurisdiction] = {
    jurisdiction.code: jurisdiction
    for jurisdiction in NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS
}


def child_support_jurisdictions() -> list[Jurisdiction]:
    logger.debug("Listing supported child-support jurisdictions.")
    return list(NON_QUEBEC_CHILD_SUPPORT_JURISDICTIONS)


def spousal_support_jurisdictions() -> list[Jurisdiction]:
    jurisdictions = [
        JURISDICTIONS_BY_CODE[code]
        for code in SPOUSAL_SUPPORT_JURISDICTION_CODES
    ]
    logger.debug("Listing supported spousal-support jurisdictions: %s", jurisdictions)
    return jurisdictions


def get_jurisdiction(code: str) -> Jurisdiction:
    normalized_code = code.upper()
    if normalized_code not in JURISDICTIONS_BY_CODE:
        raise ValueError(f"Unsupported jurisdiction code '{code}'.")

    jurisdiction = JURISDICTIONS_BY_CODE[normalized_code]
    logger.debug("Resolved jurisdiction %s to %s.", code, jurisdiction)
    return jurisdiction
