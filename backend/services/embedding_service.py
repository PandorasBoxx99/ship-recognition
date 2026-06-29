"""DINOv2 image-embedding service for visual similarity / ship re-identification.

DINOv2 is used purely as a feature extractor: each image is encoded into a vector,
and specific ships are recognised by nearest-neighbour matching against a gallery
(no per-ship training needed). Runs on GPU if available, otherwise CPU.

This is complementary to the ViT classifier (ship type / Bauart), which is left
untouched in ml_engine.py.
"""

import threading

import structlog

from backend.config import settings

log = structlog.get_logger()

# Lazy singletons guarded by locks (consistent with the rest of the codebase).
_model = None
_processor = None
_device = None
_load_error: str | None = None
_model_lock = threading.Lock()

# In-memory embedding cache: file_path -> vector. Avoids recomputing the (heavy)
# DINOv2 forward pass for gallery images on every search. Lost on restart;
# warm it with reindex_gallery().
_cache: dict[str, list[float]] = {}
_cache_lock = threading.Lock()


def is_available() -> bool:
    """True if DINOv2 could be loaded (or is already loaded)."""
    return _load_model()


def _load_model() -> bool:
    """Lazy-load DINOv2 once, thread-safe (double-checked locking)."""
    global _model, _processor, _device, _load_error
    if _model is not None:
        return True
    with _model_lock:
        if _model is not None:
            return True
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel

            name = settings.EMBEDDING_MODEL
            _device = "cuda" if torch.cuda.is_available() else "cpu"
            log.info("loading_dinov2", model=name, device=_device)
            _processor = AutoImageProcessor.from_pretrained(name)
            _model = AutoModel.from_pretrained(name).to(_device)
            _model.eval()
            _load_error = None
            log.info("dinov2_loaded", device=_device)
            return True
        except Exception as e:
            _load_error = str(e)
            log.error("dinov2_load_failed", error=str(e))
            return False


def extract(image_path: str, use_cache: bool = True) -> list[float]:
    """Return the DINOv2 embedding (CLS/pooled vector) for an image."""
    if use_cache:
        with _cache_lock:
            cached = _cache.get(image_path)
        if cached is not None:
            return cached

    if not _load_model():
        raise RuntimeError(_load_error or "DINOv2 not available")

    import torch
    from PIL import Image as PILImage

    with PILImage.open(image_path) as im:
        image = im.convert("RGB")
    inputs = _processor(images=image, return_tensors="pt").to(_device)
    with torch.no_grad():
        outputs = _model(**inputs)
        # pooler_output is the CLS token after layernorm — a solid global descriptor
        vector = outputs.pooler_output.squeeze(0).cpu().tolist()

    if use_cache:
        with _cache_lock:
            _cache[image_path] = vector
    return vector


def reindex_gallery(image_paths: list[str]) -> dict:
    """Precompute and cache embeddings for a set of gallery images."""
    indexed, failed = 0, 0
    for path in image_paths:
        try:
            extract(path, use_cache=True)
            indexed += 1
        except Exception as e:
            failed += 1
            log.warning("reindex_failed", path=path, error=str(e))
    return {"indexed": indexed, "failed": failed, "cached_total": len(_cache)}


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
