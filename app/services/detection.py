"""Detection on still images and recorded video files."""

import logging
from pathlib import Path

import cv2

from app.services.models import load_model

logger = logging.getLogger(__name__)


def _summarise(result):
    """Turn one ultralytics Result into a plain list of detection dicts."""
    detections = []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return detections

    names = getattr(result, "names", {}) or {}
    for box in boxes:
        class_id = int(box.cls[0])
        detections.append(
            {
                "label": names.get(class_id, str(class_id)),
                "confidence": round(float(box.conf[0]), 4),
                "box": [round(float(v), 2) for v in box.xyxy[0].tolist()],
            }
        )
    return detections


def detect_image(source_path, output_dir, weights, conf, iou, device=None):
    """Run detection on one image and write the annotated copy to `output_dir`.

    Returns (output_filename, detections).
    """
    model = load_model(weights)
    image = cv2.imread(str(source_path))
    if image is None:
        raise ValueError(f"Could not decode image: {Path(source_path).name}")

    results = model.predict(
        source=image, conf=conf, iou=iou, device=device, verbose=False
    )
    result = results[0]

    output_name = f"{Path(source_path).stem}_detected.jpg"
    output_path = Path(output_dir) / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(output_path), result.plot()):
        raise IOError(f"Failed to write result image to {output_path}")

    detections = _summarise(result)
    logger.info("Image %s -> %d detection(s)", Path(source_path).name, len(detections))
    return output_name, detections


def detect_video(source_path, output_dir, weights, conf, iou, device=None):
    """Run detection over every frame of a video, writing an annotated copy.

    Returns (output_filename, frame_count, total_detections). Unlike the
    original implementation this never calls `cv2.imshow`, which would try to
    open a desktop window on the server and crash in a headless container.
    """
    model = load_model(weights)
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {Path(source_path).name}")

    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0

        output_name = f"{Path(source_path).stem}_detected.mp4"
        output_path = Path(output_dir) / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            raise IOError(f"Could not open video writer for {output_path}")

        frames = 0
        total = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                result = model.predict(
                    source=frame, conf=conf, iou=iou, device=device, verbose=False
                )[0]
                writer.write(result.plot())
                total += len(_summarise(result))
                frames += 1
        finally:
            writer.release()
    finally:
        capture.release()

    logger.info("Video %s -> %d frames, %d detection(s)",
                Path(source_path).name, frames, total)
    return output_name, frames, total
