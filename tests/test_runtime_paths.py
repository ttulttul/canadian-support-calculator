import sys
from pathlib import Path

from support_calculator import create_app
from support_calculator.runtime_paths import DATA_DIR_ENV_VAR, FRONTEND_DIST_ENV_VAR, data_dir, frontend_dist_dir


def test_frontend_dist_dir_defaults_to_source_tree(monkeypatch):
    monkeypatch.delenv(FRONTEND_DIST_ENV_VAR, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    resolved = frontend_dist_dir()

    assert resolved.name == "dist"
    assert resolved.parent.name == "frontend"


def test_frontend_dist_dir_uses_env_override(monkeypatch, tmp_path):
    custom_dist = tmp_path / "dist"
    custom_dist.mkdir()
    monkeypatch.setenv(FRONTEND_DIST_ENV_VAR, str(custom_dist))

    assert frontend_dist_dir() == custom_dist.resolve()


def test_data_dir_uses_bundle_root_when_frozen(monkeypatch, tmp_path):
    bundle_root = tmp_path / "bundle"
    bundled_data = bundle_root / "support_calculator" / "data"
    bundled_data.mkdir(parents=True)
    monkeypatch.delenv(DATA_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)

    assert data_dir() == bundled_data


def test_create_app_serves_custom_frontend_dist(tmp_path):
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<html><body>desktop</body></html>", encoding="utf-8")
    app = create_app({"TESTING": True, "FRONTEND_DIST": frontend_dist})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"desktop" in response.data
