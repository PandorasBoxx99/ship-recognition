"""Tests for the OCR cross-check logic (no EasyOCR model needed)."""

from backend.services import ocr_service


def test_text_matches_by_imo():
    r = ocr_service.text_matches_ship("EVER GIVEN  9811000", name="Ever Given", imo="9811000")
    assert r["match"] is True
    assert r["matched_on"] == "imo"  # IMO digits checked before the name


def test_text_matches_by_name():
    r = ocr_service.text_matches_ship("the ship EVER GIVEN sails", name="Ever Given")
    assert r["match"] is True
    assert r["matched_on"] == "name"


def test_text_no_match():
    r = ocr_service.text_matches_ship("random unrelated text", name="Queen Mary", imo="1234567")
    assert r["match"] is False
    assert r["matched_on"] is None


def test_extract_text_graceful_when_unavailable(monkeypatch):
    monkeypatch.setattr(ocr_service, "_load_reader", lambda: False)
    monkeypatch.setattr(ocr_service, "_load_error", "EasyOCR nicht installiert")
    out = ocr_service.extract_text("/does/not/matter.jpg")
    assert out["available"] is False
    assert out["text"] == ""
