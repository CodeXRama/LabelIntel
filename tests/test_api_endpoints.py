"""
LabelIntel — Unit & Integration Tests for FastAPI Endpoints
"""

import io
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "LabelIntel" in data["app"]


def test_api_samples_list():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) > 0
    # Samples should include real packaging discovered
    filenames = [s["filename"] for s in samples]
    assert any("mango_juice" in f or "food" in f for f in filenames)


def test_api_upload_invalid_image():
    # Corrupted / invalid file upload should return 400
    corrupt_data = io.BytesIO(b"NOT_AN_IMAGE_STREAM")
    response = client.post(
        "/api/inspections/upload",
        files={"file": ("corrupt.jpg", corrupt_data, "image/jpeg")},
    )
    assert response.status_code == 400


def test_api_list_inspections():
    response = client.get("/api/inspections")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
