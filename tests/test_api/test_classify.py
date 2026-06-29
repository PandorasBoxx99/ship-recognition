"""Tests for /api/classify and /api/classifications endpoints."""

import io
from unittest.mock import patch

MOCK_PREDICTIONS = [
    {"label": "Container Ship", "confidence": 0.87},
    {"label": "Tanker", "confidence": 0.08},
    {"label": "Cruise", "confidence": 0.03},
]


@patch("backend.routers.classify.ml_service.classify_image", return_value=MOCK_PREDICTIONS)
def test_classify_upload(mock_classify, client, tmp_path):
    # Create a fake image file
    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    fake_image.name = "test_ship.png"

    resp = client.post(
        "/api/classify",
        files={"image": ("test_ship.png", fake_image, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert "filename" in data
    assert data["predictions"][0]["label"] == "Container Ship"


def test_classify_no_file(client):
    resp = client.post("/api/classify")
    assert resp.status_code == 422  # Missing required file


def test_classify_rejects_non_image(client):
    fake = io.BytesIO(b"not an image at all")
    resp = client.post(
        "/api/classify",
        files={"image": ("notes.txt", fake, "text/plain")},
    )
    assert resp.status_code == 400


def test_classify_rejects_too_large(client, monkeypatch):
    from backend.routers import classify as classify_mod

    monkeypatch.setattr(classify_mod.settings, "MAX_UPLOAD_SIZE_MB", 0)
    fake = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    resp = client.post(
        "/api/classify",
        files={"image": ("big.png", fake, "image/png")},
    )
    assert resp.status_code == 413


@patch("backend.routers.classify.ml_service.classify_image", return_value=MOCK_PREDICTIONS)
@patch("os.path.exists", return_value=True)
def test_classify_existing_ship(mock_exists, mock_classify, client, seeded_db):
    from backend.models.item import Item

    # /api/classify/ship/{id} takes a v1 item id (the scrape/ingestion layer)
    item = seeded_db.query(Item).filter(Item.local_path.isnot(None)).first()

    resp = client.post(f"/api/classify/ship/{item.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ship_id"] == item.id
    assert "predictions" in data


def test_classify_ship_not_found(client):
    resp = client.post("/api/classify/ship/99999")
    assert resp.status_code == 404


@patch("backend.routers.classify.ml_service.get_model_info", return_value={
    "loaded": True,
    "model_name": "vit-ship-classifier",
    "num_labels": 10,
})
def test_model_info(mock_info, client):
    resp = client.get("/api/model/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "loaded" in data or "model_name" in data


def test_get_classifications(client):
    resp = client.get("/api/classifications")
    assert resp.status_code == 200
    data = resp.json()
    assert "classifications" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert isinstance(data["classifications"], list)


def test_get_classifications_pagination(client):
    resp = client.get("/api/classifications?page=1&per_page=5")
    data = resp.json()
    assert data["page"] == 1
    assert len(data["classifications"]) <= 5
