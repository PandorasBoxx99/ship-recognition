"""Tests for ArcFace re-id training (synthetic features, no DINOv2 needed)."""

import numpy as np
import pytest

from backend.services import embedding_service, reid


@pytest.fixture(autouse=True)
def _reset_projection():
    embedding_service._projection = None
    yield
    embedding_service._projection = None


def test_arcface_trains_and_projection_applies(tmp_path, monkeypatch):
    monkeypatch.setattr(reid.settings, "REID_DIR", str(tmp_path))

    # Two well-separated clusters in 32-dim feature space -> easy to separate
    rng = np.random.RandomState(0)
    c0 = rng.normal(0, 0.1, size=(20, 32)) + np.array([5.0] + [0.0] * 31)
    c1 = rng.normal(0, 0.1, size=(20, 32)) + np.array([0.0, 5.0] + [0.0] * 30)
    feats = np.vstack([c0, c1]).astype("float32")
    labels = [0] * 20 + [1] * 20

    result = reid._train_on_features(
        feats, labels, out_dim=8, epochs=5, scale=30.0, margin=0.5, lr=1e-3
    )
    assert result["num_classes"] == 2
    assert result["samples"] == 40
    assert result["final_loss"] is not None

    # The saved projection loads and maps a raw 32-d vector to the 8-d embedding
    embedding_service.reload_projection()
    assert embedding_service.has_finetuned_model() is True
    out = embedding_service.apply_projection([float(x) for x in feats[0]])
    assert len(out) == 8


def test_apply_projection_noop_without_model(tmp_path, monkeypatch):
    monkeypatch.setattr(reid.settings, "REID_DIR", str(tmp_path))
    embedding_service._projection = None
    raw = [0.1, 0.2, 0.3]
    assert embedding_service.apply_projection(raw) == raw  # untrained -> unchanged


def test_reid_readiness_endpoint(client):
    resp = client.get("/api/advanced/reid/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "qualifying_ships" in data
    assert "ready" in data
    assert data["ready"] is False  # seed DB has no v2 ship images
