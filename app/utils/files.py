"""Filesystem helpers for uploads and detection results."""

import time
import unicodedata
from pathlib import Path

from werkzeug.utils import secure_filename


def extension_of(filename):
    """Lowercase extension without the dot, or '' when there is none."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def classify(filename, image_exts, video_exts):
    """Return 'image', 'video' or None for an uploaded filename."""
    ext = extension_of(filename)
    if ext in image_exts:
        return "image"
    if ext in video_exts:
        return "video"
    return None


def safe_upload_name(filename):
    """Build a collision-free, traversal-safe name for an uploaded file.

    `secure_filename` strips directory separators and exotic characters, but it
    can return an empty string for names that are entirely non-ASCII, so we fall
    back to a timestamp. A timestamp prefix also stops one upload clobbering
    another when two users send the same filename.
    """
    normalised = unicodedata.normalize("NFKD", filename or "")
    cleaned = secure_filename(normalised)
    if not cleaned:
        cleaned = "upload"
    return f"{int(time.time() * 1000)}_{cleaned}"


def resolve_within(root, relative):
    """Resolve `relative` under `root`, refusing to escape it.

    Guards the result-serving route against `../` traversal. Returns None when
    the path escapes the root or does not exist.
    """
    root = Path(root).resolve()
    try:
        candidate = (root / relative).resolve()
    except (OSError, ValueError):
        return None
    if root not in candidate.parents and candidate != root:
        return None
    return candidate if candidate.is_file() else None


def ensure_dirs(*paths):
    """Create each directory (and parents) if missing."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)
