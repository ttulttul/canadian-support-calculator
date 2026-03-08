import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

FRONTEND_DIST_ENV_VAR = "SUPPORT_CALCULATOR_FRONTEND_DIST"
DATA_DIR_ENV_VAR = "SUPPORT_CALCULATOR_DATA_DIR"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    return _package_root().parent


def _bundle_root() -> Path | None:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        resolved = Path(bundle_root)
        logger.debug("Detected PyInstaller bundle root at %s", resolved)
        return resolved
    return None


def frontend_dist_dir() -> Path:
    override = os.getenv(FRONTEND_DIST_ENV_VAR)
    if override:
        resolved = Path(override).expanduser().resolve()
        logger.info("Using frontend dist override from %s: %s", FRONTEND_DIST_ENV_VAR, resolved)
        return resolved

    bundle_root = _bundle_root()
    if bundle_root is not None:
        resolved = bundle_root / "support_calculator" / "frontend_dist"
        logger.debug("Resolved bundled frontend dist directory at %s", resolved)
        return resolved

    resolved = _project_root() / "frontend" / "dist"
    logger.debug("Resolved source frontend dist directory at %s", resolved)
    return resolved


def data_dir() -> Path:
    override = os.getenv(DATA_DIR_ENV_VAR)
    if override:
        resolved = Path(override).expanduser().resolve()
        logger.info("Using data directory override from %s: %s", DATA_DIR_ENV_VAR, resolved)
        return resolved

    bundle_root = _bundle_root()
    if bundle_root is not None:
        resolved = bundle_root / "support_calculator" / "data"
        logger.debug("Resolved bundled data directory at %s", resolved)
        return resolved

    resolved = _package_root() / "data"
    logger.debug("Resolved source data directory at %s", resolved)
    return resolved
