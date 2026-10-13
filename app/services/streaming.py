"""MJPEG stream generators for webcam, RTSP and rendered video files."""

import logging
import time
from pathlib import Path

import cv2

from app.services.models import load_model

logger = logging.getLogger(__name__)

BOUNDARY = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"


def _encode(frame, quality):
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return None
    return buffer.tobytes()


def _mjpeg(payload):
    return BOUNDARY + payload + b"\r\n\r\n"


def stream_file(video_path, quality=80, delay=0.04):
    """Replay an already-rendered video file as an MJPEG stream."""
    path = Path(video_path)
    if not path.is_file():
        logger.warning("stream_file: %s does not exist", path)
        return

    capture = cv2.VideoCapture(str(path))
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            payload = _encode(frame, quality)
            if payload is None:
                continue
            yield _mjpeg(payload)
            time.sleep(delay)
    finally:
        capture.release()


def stream_source(source, weights, conf, iou, device=None, skip_frames=2, quality=80):
    """Run live detection on `source` (webcam index or RTSP URL) as MJPEG.

    `skip_frames` runs inference on every Nth frame; set it to 1 to process
    every frame. The capture device is always released, including when the
    client disconnects and the generator is closed early.

    As with `detect_video`, no `cv2.imshow` call is made here — the original
    code opened a desktop window per frame, which cannot work on a server.
    """
    model = load_model(weights)
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        logger.error("Could not open stream source: %r", source)
        return

    skip = max(1, int(skip_frames))
    index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            index += 1
            if index % skip != 0:
                continue

            result = model.predict(
                source=frame, conf=conf, iou=iou, device=device, verbose=False
            )[0]
            payload = _encode(result.plot(), quality)
            if payload is None:
                continue
            yield _mjpeg(payload)
    except GeneratorExit:
        logger.info("Client disconnected from stream %r", source)
        raise
    finally:
        capture.release()
