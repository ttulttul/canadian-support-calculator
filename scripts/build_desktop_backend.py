import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def frontend_dist_dir() -> Path:
    return project_root() / "frontend" / "dist"


def build_output_root() -> Path:
    return project_root() / "dist" / "backend-bundle"


def ensure_xcode_license_ready() -> None:
    logger.info("Checking Xcode license status required by PyInstaller on macOS.")
    result = subprocess.run(
        ["xcodebuild", "-license", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return

    if result.returncode == 69:
        raise RuntimeError(
            "Xcode command-line tools are installed but the license has not been accepted. "
            "Run `sudo xcodebuild -license` once on this Mac before building desktop releases."
        )

    raise RuntimeError(
        "Unable to verify Xcode tooling for desktop packaging. "
        f"`xcodebuild -license check` exited with status {result.returncode}: "
        f"{(result.stderr or result.stdout).strip()}"
    )


def run() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    root = project_root()
    frontend_dist = frontend_dist_dir()
    if not frontend_dist.exists():
        raise FileNotFoundError(
            f"Expected built frontend assets at {frontend_dist}. Run `npm run frontend:build` first."
        )
    ensure_xcode_license_ready()

    output_root = build_output_root()
    if output_root.exists():
        logger.info("Removing previous desktop backend bundle at %s", output_root)
        shutil.rmtree(output_root)

    command = [
        "uv",
        "run",
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "support_calculator_backend.spec",
    ]
    logger.info("Building desktop backend bundle with command: %s", command)
    subprocess.run(command, cwd=root, check=True)

    produced_bundle = root / "dist" / "support-calculator-backend"
    if not produced_bundle.exists():
        raise FileNotFoundError(f"PyInstaller did not produce {produced_bundle}")

    logger.info("Moving backend bundle from %s to %s", produced_bundle, output_root)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(produced_bundle), str(output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
