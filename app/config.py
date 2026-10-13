"""Configuration for the Paw-Patrol detection service.

Every tunable is read from the environment so the same image can run in dev,
staging and production without code changes. See `.env.example` for the full
list and their defaults.

Values are resolved in `__init__`, not in the class body, so that the
environment is read when the app is *created* rather than when this module is
first imported. That makes the settings testable — a fixture can set env vars
after import and still have them take effect.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _path(name, default):
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default


class Config:
    """Base configuration shared by every environment."""

    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False

    IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "webp"}
    VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

    def __init__(self):
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key")

        # Filesystem layout
        self.MODELS_DIR = _path("MODELS_DIR", BASE_DIR / "models")
        self.DATA_DIR = _path("DATA_DIR", BASE_DIR / "data")
        self.UPLOAD_DIR = self.DATA_DIR / "uploads"
        self.OUTPUT_DIR = self.DATA_DIR / "outputs"

        # Model weights, resolved inside MODELS_DIR
        self.IMAGE_MODEL = os.getenv("IMAGE_MODEL", "mix.pt")
        self.VIDEO_MODEL = os.getenv("VIDEO_MODEL", "wildlide.pt")
        self.STREAM_MODEL = os.getenv("STREAM_MODEL", "wildlide.pt")

        # Inference
        self.CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
        self.IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))
        self.DEVICE = os.getenv("DEVICE") or None  # None lets ultralytics choose

        # Uploads
        self.MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "256")) * 1024 * 1024

        # Live sources
        self.RTSP_URL = os.getenv("RTSP_URL", "")
        self.WEBCAM_INDEX = int(os.getenv("WEBCAM_INDEX", "0"))
        self.STREAM_SKIP_FRAMES = int(os.getenv("STREAM_SKIP_FRAMES", "2"))
        self.STREAM_JPEG_QUALITY = int(os.getenv("STREAM_JPEG_QUALITY", "80"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
        if self.SECRET_KEY == "dev-only-insecure-key":
            raise RuntimeError(
                "SECRET_KEY must be set to a real value in production. Generate one "
                'with: python -c "import secrets; print(secrets.token_hex(32))"'
            )


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name=None):
    """Return a config instance for `name`, falling back to $APP_ENV."""
    name = (name or os.getenv("APP_ENV", "development")).lower()
    if name not in _CONFIGS:
        raise ValueError(f"Unknown APP_ENV {name!r}; expected one of {sorted(_CONFIGS)}")
    return _CONFIGS[name]()
