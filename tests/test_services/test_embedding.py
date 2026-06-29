"""Tests for the FAISS gallery and similarity confidence logic (no DINOv2 load)."""

from backend.routers.advanced import _assess_confidence
from backend.services import embedding_service


def _row(sim, ship_id=1, name="Ever Given", stype="Container Ship"):
    return {"similarity": sim, "ship_id": ship_id, "ship_name": name, "ship_type": stype}


# --- confidence / open-set logic ---


def test_confidence_confident_match():
    scored = [_row(0.91), _row(0.40, ship_id=2, name="Other")]
    best = _assess_confidence(scored)
    assert best["confident"] is True
    assert best["ship_name"] == "Ever Given"
    assert best["confidence"] == 0.91
    assert best["margin"] == 0.51


def test_confidence_below_threshold_is_open_set():
    best = _assess_confidence([_row(0.45), _row(0.40)])
    assert best["confident"] is False


def test_confidence_ambiguous_low_margin():
    best = _assess_confidence([_row(0.80, ship_id=1), _row(0.79, ship_id=2)])
    assert best["confident"] is False


def test_confidence_no_gallery():
    best = _assess_confidence([])
    assert best["confident"] is False
    assert best["reason"] == "no_gallery_images"


# --- FAISS persistent gallery (fake vectors, no model) ---


def test_faiss_add_and_search(tmp_path, monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "DATA_DIR", str(tmp_path))
    embedding_service.clear_index()
    embedding_service.add_embedding(10, [1.0, 0.0, 0.0, 0.0])
    embedding_service.add_embedding(20, [0.0, 1.0, 0.0, 0.0])

    res = embedding_service.search([0.9, 0.1, 0.0, 0.0], k=2)
    assert res[0][0] == 10  # nearest neighbour is id 10
    assert res[0][1] > res[1][1]
    assert embedding_service.gallery_size() == 2


def test_faiss_persistence_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "DATA_DIR", str(tmp_path))
    embedding_service.clear_index()
    embedding_service.add_embedding(5, [1.0, 0.0, 0.0])

    # Simulate a restart: drop the in-memory index, force reload from disk
    embedding_service._index = None
    assert embedding_service.gallery_size() == 1
    res = embedding_service.search([1.0, 0.0, 0.0], k=1)
    assert res[0][0] == 5


def test_faiss_empty_returns_no_match(tmp_path, monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "DATA_DIR", str(tmp_path))
    embedding_service.clear_index()
    assert embedding_service.search([1.0, 0.0], k=3) == []
