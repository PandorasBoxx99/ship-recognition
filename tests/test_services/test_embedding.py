"""Tests for the DINOv2 embedding service and similarity confidence logic."""

from backend.routers.advanced import _assess_confidence
from backend.services import embedding_service


def _row(sim, ship_id=1, name="Ever Given", stype="Container Ship"):
    return {"similarity": sim, "ship_id": ship_id, "ship_name": name, "ship_type": stype}


def test_confidence_confident_match():
    scored = [_row(0.91), _row(0.40, ship_id=2, name="Other")]
    best = _assess_confidence(scored)
    assert best["confident"] is True
    assert best["ship_name"] == "Ever Given"
    assert best["confidence"] == 0.91
    assert best["margin"] == 0.51


def test_confidence_below_threshold_is_open_set():
    # Top similarity under the threshold -> not a confident match (unknown ship)
    scored = [_row(0.45), _row(0.40)]
    best = _assess_confidence(scored)
    assert best["confident"] is False


def test_confidence_ambiguous_low_margin():
    # High similarity but two ships almost tied -> not confident
    scored = [_row(0.80, ship_id=1), _row(0.79, ship_id=2)]
    best = _assess_confidence(scored)
    assert best["confident"] is False


def test_confidence_no_gallery():
    best = _assess_confidence([])
    assert best["confident"] is False
    assert best["reason"] == "no_gallery_images"


def test_embedding_cache_hit_skips_model(monkeypatch):
    # A cached embedding must be returned without loading the model
    monkeypatch.setitem(embedding_service._cache, "/tmp/x.jpg", [0.1, 0.2, 0.3])
    called = {"load": False}

    def _fail_load():
        called["load"] = True
        return False

    monkeypatch.setattr(embedding_service, "_load_model", _fail_load)
    assert embedding_service.extract("/tmp/x.jpg") == [0.1, 0.2, 0.3]
    assert called["load"] is False
