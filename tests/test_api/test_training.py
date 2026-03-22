"""Tests for /api/training endpoints."""

from unittest.mock import patch


@patch("backend.routers.training.ml_service.get_training_status", return_value={
    "running": False,
    "progress": 0,
    "message": "Idle",
})
def test_training_status(mock_status, client):
    resp = client.get("/api/training/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data


def test_training_start_invalid_dir(client):
    resp = client.post("/api/training/start", json={
        "dataset_dir": "/nonexistent/path",
        "epochs": 3,
    })
    assert resp.status_code == 400


@patch("backend.routers.training.ml_service.get_available_datasets", return_value={
    "datasets": [],
    "download_dir": "/tmp",
})
def test_training_datasets(mock_datasets, client):
    resp = client.get("/api/training/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert "datasets" in data
