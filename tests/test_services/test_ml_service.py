"""Tests for ML service (with mocked ml_engine)."""

from unittest.mock import patch


@patch("ml_engine.classify_image", return_value=[
    {"label": "Container Ship", "confidence": 0.87},
    {"label": "Tanker", "confidence": 0.08},
])
def test_classify_image(mock_engine):
    from backend.services.ml_service import classify_image

    results = classify_image(b"fake_image_data")
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["label"] == "Container Ship"


@patch("ml_engine.get_model_info", return_value={
    "loaded": True,
    "model_name": "vit-ship-classifier",
    "num_labels": 10,
})
def test_get_model_info(mock_engine):
    from backend.services.ml_service import get_model_info

    info = get_model_info()
    assert info["loaded"] is True
    assert info["num_labels"] == 10


@patch("ml_engine.get_training_status", return_value={
    "running": False,
    "progress": 0,
    "message": "Idle",
})
def test_get_training_status(mock_engine):
    from backend.services.ml_service import get_training_status

    status = get_training_status()
    assert status["running"] is False


@patch("ml_engine.get_augment_status", return_value={
    "running": False,
    "progress": 0,
    "message": "Idle",
})
def test_get_augment_status(mock_engine):
    from backend.services.ml_service import get_augment_status

    status = get_augment_status()
    assert status["running"] is False
