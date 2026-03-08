import logging
from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from .api import api_blueprint
from .runtime_paths import frontend_dist_dir
from .tables import load_default_child_support_registry, load_default_child_support_table

logger = logging.getLogger(__name__)


def create_app(config: dict | None = None) -> Flask:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    if config:
        app.config.update(config)

    if "FRONTEND_DIST" in app.config:
        app.config["FRONTEND_DIST"] = Path(app.config["FRONTEND_DIST"])
    else:
        app.config["FRONTEND_DIST"] = frontend_dist_dir()

    if "CHILD_SUPPORT_TABLES" not in app.config:
        app.config["CHILD_SUPPORT_TABLES"] = load_default_child_support_registry()

    if "CHILD_SUPPORT_TABLE" not in app.config:
        app.config["CHILD_SUPPORT_TABLE"] = load_default_child_support_table()

    app.register_blueprint(api_blueprint)

    @app.get("/")
    def serve_index():
        active_frontend_dist = Path(app.config["FRONTEND_DIST"])
        if active_frontend_dist.exists():
            logger.info("Serving frontend index from %s", active_frontend_dist)
            return send_from_directory(active_frontend_dist, "index.html")

        logger.info("Frontend build not found; returning API status payload.")
        return jsonify(
            {
                "name": "Canadian Support Calculator API",
                "frontendBuilt": False,
                "message": "Build the frontend to serve the SPA from Flask.",
            }
        )

    @app.get("/<path:path>")
    def serve_frontend(path: str):
        if path.startswith("api/"):
            abort(404)

        active_frontend_dist = Path(app.config["FRONTEND_DIST"])
        if not active_frontend_dist.exists():
            abort(404)

        candidate = active_frontend_dist / path
        if candidate.is_file():
            return send_from_directory(active_frontend_dist, path)

        return send_from_directory(active_frontend_dist, "index.html")

    return app
