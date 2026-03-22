"""Tests for /api/augment endpoints."""

from unittest.mock import patch


def test_augment_invalid_dir(client):
    resp = client.post("/api/augment", json={
        "source_dir": "/nonexistent/path",
        "num_per_image": 5,
    })
    assert resp.status_code == 400


@patch("backend.routers.augmentation.ml_service.get_augment_status", return_value={
    "running": False,
    "progress": 0,
    "message": "Idle",
})
def test_augment_status(mock_status, client):
    resp = client.get("/api/augment/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
