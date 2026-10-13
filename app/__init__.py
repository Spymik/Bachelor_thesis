"""Application factory for the Paw-Patrol detection service."""

import logging
import os

from flask import Flask

from app.config import get_config
from app.utils.files import ensure_dirs

__version__ = "1.0.0"


def configure_logging(level=None):
    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def create_app(config_name=None):
    """Build and return a configured Flask application.

    Templates and static files live inside the package; `static_url_path` is
    pinned to "/static" because several templates hardcode that prefix.
    """
    # Load .env before anything reads the environment. Real environment
    # variables always win over the file.
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:  # python-dotenv is optional at runtime
        pass

    configure_logging()

    cfg = get_config(config_name)
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    # from_object copies every UPPERCASE attribute, instance or class.
    app.config.from_object(cfg)

    ensure_dirs(app.config["UPLOAD_DIR"], app.config["OUTPUT_DIR"])

    from app.routes import detection, pages, streams

    app.register_blueprint(pages.bp)
    app.register_blueprint(detection.bp)
    app.register_blueprint(streams.bp)

    app.logger.info(
        "Paw-Patrol %s started (env=%s, models=%s)",
        __version__,
        config_name or os.getenv("APP_ENV", "development"),
        app.config["MODELS_DIR"],
    )
    return app
