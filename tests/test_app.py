"""Smoke tests that exercise routing and validation without loading weights."""

import io

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_index_renders(client):
    assert client.get("/").status_code == 200


def test_dashboard_get_renders(client):
    assert client.get("/dashboard").status_code == 200


def test_upload_without_file_is_rejected(client):
    response = client.post("/dashboard", data={})
    assert response.status_code == 400


def test_unsupported_extension_is_rejected(client):
    data = {"file": (io.BytesIO(b"not really a file"), "payload.exe")}
    response = client.post("/dashboard", data=data, content_type="multipart/form-data")
    assert response.status_code == 400


def test_result_path_traversal_is_blocked(client):
    response = client.get("/results/..%2f..%2frequirements.txt")
    assert response.status_code == 404


def test_rtsp_feed_requires_configuration(client, monkeypatch):
    monkeypatch.setenv("RTSP_URL", "")
    assert client.get("/rtsp_feed").status_code == 503
