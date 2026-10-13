FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

# opencv-python needs libGL and libglib even in headless containers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py run.py gunicorn.conf.py ./

# Model weights and runtime data are mounted at deploy time, not baked in.
VOLUME ["/srv/app/models", "/srv/app/data"]

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /srv/app/data/uploads /srv/app/data/outputs \
    && chown -R appuser:appuser /srv/app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
