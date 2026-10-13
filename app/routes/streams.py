"""Live and replayed MJPEG stream routes."""

import logging

from flask import Blueprint, Response, abort, current_app, request

from app.services.streaming import stream_file, stream_source

logger = logging.getLogger(__name__)

bp = Blueprint("streams", __name__)

MJPEG = "multipart/x-mixed-replace; boundary=frame"


def _stream_config():
    cfg = current_app.config
    return {
        "weights": cfg["MODELS_DIR"] / cfg["STREAM_MODEL"],
        "conf": cfg["CONFIDENCE_THRESHOLD"],
        "iou": cfg["IOU_THRESHOLD"],
        "device": cfg["DEVICE"],
        "skip_frames": cfg["STREAM_SKIP_FRAMES"],
        "quality": cfg["STREAM_JPEG_QUALITY"],
    }


@bp.get("/video_feed")
def video_feed():
    """Replay the most recently rendered detection video."""
    name = request.args.get("name")
    output_dir = current_app.config["OUTPUT_DIR"]

    if name:
        from app.utils.files import resolve_within

        path = resolve_within(output_dir, name)
        if path is None:
            abort(404)
    else:
        videos = sorted(
            output_dir.glob("*_detected.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not videos:
            abort(404, description="No rendered detection video available yet.")
        path = videos[0]

    return Response(
        stream_file(path, current_app.config["STREAM_JPEG_QUALITY"]),
        mimetype=MJPEG,
    )


@bp.get("/webcam_feed")
def webcam_feed():
    """Live detection on the server's local camera."""
    return Response(
        stream_source(current_app.config["WEBCAM_INDEX"], **_stream_config()),
        mimetype=MJPEG,
    )


@bp.get("/rtsp_feed")
def rtsp_feed():
    """Live detection on the configured RTSP camera."""
    url = current_app.config["RTSP_URL"]
    if not url:
        abort(503, description="RTSP_URL is not configured.")
    return Response(stream_source(url, **_stream_config()), mimetype=MJPEG)
