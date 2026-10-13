"""Upload and detection routes."""

import logging

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    render_template,
    request,
    send_file,
)

from app.services.detection import detect_image, detect_video
from app.utils.files import classify, resolve_within, safe_upload_name

logger = logging.getLogger(__name__)

bp = Blueprint("detection", __name__)


@bp.route("/dashboard", methods=["GET", "POST"])
def predict_img():
    """Render the dashboard and, on POST, run detection over the upload.

    The endpoint keeps its original name (`predict_img`) and URL because the
    dashboard template references both.
    """
    if request.method == "GET":
        return render_template("dashboard.html")

    cfg = current_app.config
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash("No file was selected.", "error")
        return render_template("dashboard.html"), 400

    kind = classify(upload.filename, cfg["IMAGE_EXTENSIONS"], cfg["VIDEO_EXTENSIONS"])
    if kind is None:
        allowed = sorted(cfg["IMAGE_EXTENSIONS"] | cfg["VIDEO_EXTENSIONS"])
        flash(f"Unsupported file type. Allowed: {', '.join(allowed)}.", "error")
        return render_template("dashboard.html"), 400

    stored_name = safe_upload_name(upload.filename)
    source_path = cfg["UPLOAD_DIR"] / stored_name
    upload.save(source_path)
    logger.info("Stored upload %s (%s)", stored_name, kind)

    try:
        if kind == "image":
            output_name, detections = detect_image(
                source_path,
                cfg["OUTPUT_DIR"],
                cfg["MODELS_DIR"] / cfg["IMAGE_MODEL"],
                cfg["CONFIDENCE_THRESHOLD"],
                cfg["IOU_THRESHOLD"],
                cfg["DEVICE"],
            )
            return render_template(
                "dashboard.html",
                image_path=output_name,
                media_type="image",
                detections=detections,
            )

        output_name, frames, total = detect_video(
            source_path,
            cfg["OUTPUT_DIR"],
            cfg["MODELS_DIR"] / cfg["VIDEO_MODEL"],
            cfg["CONFIDENCE_THRESHOLD"],
            cfg["IOU_THRESHOLD"],
            cfg["DEVICE"],
        )
        return render_template(
            "dashboard.html",
            video_path=output_name,
            media_type="video",
            frame_count=frames,
            detection_count=total,
        )
    except FileNotFoundError as exc:
        logger.exception("Model weights missing")
        flash(str(exc), "error")
        return render_template("dashboard.html"), 500
    except (ValueError, IOError) as exc:
        logger.exception("Detection failed for %s", stored_name)
        flash(f"Could not process that file: {exc}", "error")
        return render_template("dashboard.html"), 400


@bp.get("/results/<path:filename>")
def result_file(filename):
    """Serve an annotated result, refusing any path outside the output dir."""
    path = resolve_within(current_app.config["OUTPUT_DIR"], filename)
    if path is None:
        abort(404)
    return send_file(path)
