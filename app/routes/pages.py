"""Static page routes."""

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/healthz")
def healthz():
    """Liveness probe for load balancers and container orchestrators."""
    return {"status": "ok"}, 200
