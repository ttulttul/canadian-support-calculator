import logging
import os

from support_calculator import create_app

logger = logging.getLogger(__name__)


def main() -> None:
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5001"))
    logger.info("Starting Flask development server on %s:%s", host, port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
