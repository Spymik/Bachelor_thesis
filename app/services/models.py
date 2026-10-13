"""Lazy, process-wide YOLO model registry.

Loading a YOLO checkpoint costs hundreds of milliseconds and a few hundred MB
of RAM. The original implementation constructed a new `YOLO(...)` *inside the
per-frame loop*, which re-read the weights from disk for every single frame.
Models are cached here and reused for the life of the process instead.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_models = {}
_lock = threading.Lock()


def load_model(weights_path):
    """Return a cached YOLO model for `weights_path`, loading it on first use.

    Thread-safe: Flask serves requests from multiple threads and each stream
    generator runs in its own, so two concurrent first-hits must not both load.
    """
    key = str(weights_path)
    model = _models.get(key)
    if model is not None:
        return model

    with _lock:
        # Re-check inside the lock; another thread may have loaded it already.
        model = _models.get(key)
        if model is not None:
            return model

        from ultralytics import YOLO  # imported lazily to keep startup cheap

        if not _exists(weights_path):
            raise FileNotFoundError(
                f"Model weights not found: {weights_path}. "
                "Place the .pt file in the models/ directory or point "
                "IMAGE_MODEL / VIDEO_MODEL / STREAM_MODEL at an existing file."
            )

        logger.info("Loading YOLO weights: %s", weights_path)
        model = YOLO(str(weights_path))
        _models[key] = model
        return model


def _exists(path):
    from pathlib import Path

    return Path(path).is_file()


def clear_cache():
    """Drop all cached models. Used by tests."""
    with _lock:
        _models.clear()
