# Paw-Patrol

Object detection web service built on **YOLOv8** and **Flask**. Upload an image
or video and get it back annotated, or point it at a webcam or RTSP camera for
live detection streamed over MJPEG.

Two model heads are supported out of the box: a wildlife detector
(`wildlide.pt`) and a general/crack detector (`mix.pt`).

---

## Requirements

- Python 3.10
- `libgl1` and `libglib2.0-0` on Linux (OpenCV needs them even headless)
- A CUDA-capable GPU is optional; inference falls back to CPU

## Quick start

```bash
git clone git@github.com:anjisnu07/Paw-Patrol.git
cd Paw-Patrol

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
python run.py
```

Open <http://127.0.0.1:5000>.

Model weights belong in `models/`. Only `wildlide.pt` is tracked in git; place
`mix.pt` there yourself, or point `IMAGE_MODEL` at whatever you do have.

## Project layout

```
Paw-Patrol/
├── app/
│   ├── __init__.py          # create_app() application factory
│   ├── config.py            # environment-driven settings
│   ├── routes/
│   │   ├── pages.py         # /, /healthz
│   │   ├── detection.py     # /dashboard, /results/<file>
│   │   └── streams.py       # /video_feed, /webcam_feed, /rtsp_feed
│   ├── services/
│   │   ├── models.py        # cached YOLO loading
│   │   ├── detection.py     # image and video inference
│   │   └── streaming.py     # MJPEG frame generators
│   ├── utils/files.py       # upload naming, path-traversal guards
│   ├── templates/
│   └── static/
├── models/                  # .pt weights
├── data/
│   ├── uploads/             # incoming files (gitignored)
│   └── outputs/             # annotated results (gitignored)
├── tests/
├── wsgi.py                  # production entrypoint
├── run.py                   # development entrypoint
├── gunicorn.conf.py
└── Dockerfile
```

The split is deliberate: routes only parse requests and render, services hold
the inference logic and know nothing about Flask, and every filesystem path and
threshold comes from config rather than being hardcoded mid-function.

## Routes

| Method     | Path                | Purpose                                     |
| ---------- | ------------------- | ------------------------------------------- |
| `GET`      | `/`                 | Landing page                                |
| `GET`      | `/dashboard`        | Upload form                                 |
| `POST`     | `/dashboard`        | Run detection on the uploaded image/video   |
| `GET`      | `/results/<file>`   | Serve an annotated result                   |
| `GET`      | `/video_feed`       | Replay a rendered detection video as MJPEG  |
| `GET`      | `/webcam_feed`      | Live detection on the server's camera       |
| `GET`      | `/rtsp_feed`        | Live detection on `RTSP_URL`                |
| `GET`      | `/healthz`          | Liveness probe                              |

## Configuration

All settings come from the environment; `.env` is read at startup and real
environment variables take precedence. See `.env.example` for the complete
list. The ones worth knowing:

| Variable               | Default             | Notes                                          |
| ---------------------- | ------------------- | ---------------------------------------------- |
| `APP_ENV`              | `development`       | `development` / `production` / `testing`       |
| `SECRET_KEY`           | dev placeholder     | **Startup fails in production if left unset**  |
| `MODELS_DIR`           | `./models`          | Where `.pt` files are resolved from            |
| `DATA_DIR`             | `./data`            | Parent of `uploads/` and `outputs/`            |
| `IMAGE_MODEL`          | `mix.pt`            | Weights used for still images                  |
| `VIDEO_MODEL`          | `wildlide.pt`       | Weights used for uploaded video                |
| `STREAM_MODEL`         | `wildlide.pt`       | Weights used for webcam and RTSP               |
| `CONFIDENCE_THRESHOLD` | `0.25`              | Minimum score to keep a detection              |
| `DEVICE`               | auto                | `cpu`, `0`, `0,1`; blank lets ultralytics pick |
| `MAX_UPLOAD_MB`        | `256`               | Rejected above this size                       |
| `RTSP_URL`             | empty               | `/rtsp_feed` returns 503 until this is set     |
| `STREAM_SKIP_FRAMES`   | `2`                 | Infer on every Nth frame                       |

RTSP credentials go in `RTSP_URL`, never in source.

## Running in production

Never use `run.py` for real traffic — it's the Flask development server.

```bash
export APP_ENV=production
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
gunicorn --config gunicorn.conf.py wsgi:app
```

On Windows, where gunicorn is unavailable:

```powershell
waitress-serve --listen=0.0.0.0:8000 wsgi:app
```

`gunicorn.conf.py` uses threaded workers with the request timeout disabled,
because the MJPEG endpoints hold connections open indefinitely and sync workers
would be pinned by a single viewer. Each worker loads its own copy of the
weights, so scale `THREADS` before `WEB_CONCURRENCY`.

### Docker

```bash
docker build -t paw-patrol .
docker run -p 8000:8000 \
  -e SECRET_KEY=... \
  -v "$(pwd)/models:/srv/app/models" \
  -v "$(pwd)/data:/srv/app/data" \
  paw-patrol
```

Weights and runtime data are mounted rather than baked into the image, so it
stays small and the weights can be rotated without a rebuild.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers routing, upload validation and the path-traversal guard. It
deliberately avoids loading real weights, so it runs without a GPU or any `.pt`
file present.

## Notes on the rewrite

This started as a single 277-line `webapp.py`. Behaviour that changed, and why:

- **`cv2.imshow` calls were removed.** The original opened a desktop window per
  frame from inside request handlers, which cannot work on a headless server.
- **Models are cached.** `YOLO(...)` was previously constructed *inside* the
  per-frame loop, re-reading weights from disk for every frame.
- **Uploads are sanitised.** Filenames went to `os.path.join` unchecked; they
  now pass through `secure_filename` with a timestamp prefix, and results are
  served through a path-traversal guard.
- **The catch-all `/<path:filename>` route is gone.** It shadowed every other
  route and ignored its own argument, always serving `files[0]`.
- **RTSP credentials moved to config.** They were hardcoded in the source.
- **The debug server no longer binds `0.0.0.0` by default**, and `debug=True`
  is tied to `APP_ENV` instead of always being on.
- **TensorFlow was dropped.** It was imported but never called, and cost ~500 MB
  of wheels. Detection runs on PyTorch via ultralytics.
- **PNG, JPEG, WebP and more video formats are accepted.** Only `.jpg` and
  `.mp4` worked before.
