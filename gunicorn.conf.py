"""Gunicorn settings tuned for MJPEG streaming + GPU-bound inference.

Two things drive this config:

1. `/webcam_feed`, `/rtsp_feed` and `/video_feed` hold a connection open
   indefinitely. Sync workers would be pinned by a single viewer, so we use
   threaded workers and disable the request timeout.
2. Each worker loads its own copy of the YOLO weights (a few hundred MB), so
   worker count stays low deliberately — scale threads, not processes.
"""

import os

bind = os.getenv("BIND", "0.0.0.0:8000")
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = int(os.getenv("THREADS", "8"))

# Streaming responses never "finish"; a timeout would kill them mid-flight.
timeout = 0
graceful_timeout = 30
keepalive = 5

max_requests = int(os.getenv("MAX_REQUESTS", "0"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
