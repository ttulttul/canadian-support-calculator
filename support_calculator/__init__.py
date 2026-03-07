import logging
from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from .api import api_blueprint
from .tables import load_default_child_support_table

logger = logging.getLogger(__name__)


def create_app(config: dict | None = None) -> Flask:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["FRONTEND_DIST"] = frontend_dist
    app.config["CHILD_SUPPORT_TABLE"] = load_default_child_support_table()

    if config:
        app.config.update(config)

    app.register_blueprint(api_blueprint)

    @app.get("/")
    def serve_index():
        if frontend_dist.exists():
            logger.info("Serving frontend index from %s", frontend_dist)
            return send_from_directory(frontend_dist, "index.html")

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

        if not frontend_dist.exists():
            abort(404)

        candidate = frontend_dist / path
        if candidate.is_file():
            return send_from_directory(frontend_dist, path)

        return send_from_directory(frontend_dist, "index.html")

    return app
