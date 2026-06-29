"""OCR verification channel for ship recognition (EasyOCR).

OCR reads text on the hull (ship name / IMO number) and is used ONLY as a
parallel cross-check on top of the visual DINOv2 similarity — the visual
recognition itself is never altered by OCR.

EasyOCR is an optional dependency: if it is not installed, OCR degrades
gracefully (available=False) and the visual result is returned unchanged.
torch/EasyOCR are imported lazily so the app starts without them.
"""

import re
import threading

import structlog

from backend.config import settings

log = structlog.get_logger()

_reader = None
_load_error: str | None = None
_reader_lock = threading.Lock()


def is_available() -> bool:
    return _load_reader()


def _load_reader() -> bool:
    """Lazy-load the EasyOCR reader once, thread-safe."""
    global _reader, _load_error
    if _reader is not None:
        return True
    with _reader_lock:
        if _reader is not None:
            return True
        try:
            import easyocr
            import torch

            gpu = torch.cuda.is_available()
            log.info("loading_easyocr", langs=settings.OCR_LANGUAGES, gpu=gpu)
            # verbose=False avoids EasyOCR's progress bar (its block chars crash
            # the Windows cp1252 console with a UnicodeEncodeError on first download)
            _reader = easyocr.Reader(settings.OCR_LANGUAGES, gpu=gpu, verbose=False)
            _load_error = None
            return True
        except Exception as e:
            _load_error = str(e)
            log.warning("ocr_unavailable", error=str(e))
            return False


def extract_text(image_path: str) -> dict:
    """Run OCR on an image; returns {available, text, tokens} or a graceful error."""
    if not _load_reader():
        return {
            "available": False,
            "text": "",
            "error": _load_error or "EasyOCR nicht installiert (pip install easyocr)",
        }
    try:
        tokens = _reader.readtext(image_path, detail=0)
        return {"available": True, "text": " ".join(tokens), "tokens": tokens}
    except Exception as e:
        return {"available": False, "text": "", "error": str(e)}


def _alnum(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def text_matches_ship(
    text: str, *, name: str | None = None, imo: str | None = None, mmsi: str | None = None
) -> dict:
    """Check whether OCR text confirms a candidate ship (by IMO/MMSI digits or name)."""
    digits_in_text = re.sub(r"\D", "", text or "")
    for key, value in (("imo", imo), ("mmsi", mmsi)):
        digits = re.sub(r"\D", "", str(value or ""))
        if digits and len(digits) >= 5 and digits in digits_in_text:
            return {"match": True, "matched_on": key}

    norm_text = _alnum(text)
    norm_name = _alnum(name)
    if len(norm_name) >= 3 and norm_name in norm_text:
        return {"match": True, "matched_on": "name"}

    return {"match": False, "matched_on": None}
