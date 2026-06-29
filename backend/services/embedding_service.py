"""DINOv2 image embeddings + a persistent FAISS gallery for ship re-identification.

DINOv2 encodes each image into a vector; specific ships are recognised by
nearest-neighbour search against a gallery of known-ship embeddings — no
per-ship training. The gallery is a FAISS index persisted to disk
(DATA_DIR/ship_gallery.faiss), so it survives restarts and scales far beyond the
old in-memory Python loop. Vectors are L2-normalised, so inner product == cosine.

Runs on GPU if available, otherwise CPU. Complementary to the ViT classifier
(ship type / Bauart) in ml_engine.py, which is untouched.
"""

import os
import threading

import structlog

from backend.config import settings

log = structlog.get_logger()

# --- DINOv2 model (lazy, thread-safe) ---
_model = None
_processor = None
_device = None
_load_error: str | None = None
_model_lock = threading.Lock()

# --- Persistent FAISS gallery ---
_index = None
_index_lock = threading.Lock()


def _index_path() -> str:
    return os.path.join(settings.DATA_DIR, "ship_gallery.faiss")


def is_available() -> bool:
    """True if DINOv2 can be loaded (or is already loaded)."""
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


def extract(image_path: str) -> list[float]:
    """Return the DINOv2 embedding (CLS/pooled vector) for an image."""
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
        return outputs.pooler_output.squeeze(0).cpu().tolist()


def _normalize(vector):
    """L2-normalise so FAISS inner product equals cosine similarity."""
    import numpy as np

    arr = np.asarray(vector, dtype="float32")
    norm = float(np.linalg.norm(arr))
    if norm > 0:
        arr = arr / norm
    return arr


def _load_index():
    """Load the FAISS index from disk if present (lazy)."""
    global _index
    if _index is not None:
        return _index
    import faiss

    path = _index_path()
    if os.path.exists(path):
        _index = faiss.read_index(path)
        log.info("faiss_index_loaded", ntotal=_index.ntotal)
    return _index


def _ensure_index(dim: int):
    global _index
    import faiss

    if _index is None:
        _load_index()
    if _index is None:
        _index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        log.info("faiss_index_created", dim=dim)
    return _index


def _save_index():
    import faiss

    if _index is not None:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        faiss.write_index(_index, _index_path())


def add_embedding(image_id: int, vector: list[float], save: bool = True) -> None:
    """Add (or replace) one image's embedding in the gallery, keyed by image_id."""
    import numpy as np

    arr = _normalize(vector)
    ids = np.array([image_id], dtype="int64")
    with _index_lock:
        idx = _ensure_index(len(arr))
        try:
            idx.remove_ids(ids)  # dedup: replace any existing vector for this id
        except Exception:
            pass
        idx.add_with_ids(arr.reshape(1, -1), ids)
        if save:
            _save_index()


def add_image(image_path: str, image_id: int, save: bool = True) -> None:
    """Encode an image and add it to the gallery."""
    add_embedding(image_id, extract(image_path), save=save)


def search(vector: list[float], k: int = 10) -> list[tuple[int, float]]:
    """Return [(image_id, cosine_similarity)] for the k nearest gallery images."""
    arr = _normalize(vector).reshape(1, -1)
    with _index_lock:
        idx = _index if _index is not None else _load_index()
        if idx is None or idx.ntotal == 0:
            return []
        sims, ids = idx.search(arr, min(k, idx.ntotal))
    return [(int(i), float(s)) for i, s in zip(ids[0], sims[0]) if i != -1]


def remove(image_id: int, save: bool = True) -> None:
    """Remove an image from the gallery (best-effort)."""
    import numpy as np

    with _index_lock:
        if _index is None:
            _load_index()
        if _index is None:
            return
        try:
            _index.remove_ids(np.array([image_id], dtype="int64"))
            if save:
                _save_index()
        except Exception as e:
            log.warning("faiss_remove_failed", image_id=image_id, error=str(e))


def rebuild(items: list[tuple[int, str]]) -> dict:
    """Recompute embeddings for (image_id, file_path) pairs and rebuild the index."""
    global _index
    import faiss
    import numpy as np

    pending, failed = [], 0
    for image_id, path in items:
        try:
            pending.append((image_id, _normalize(extract(path))))
        except Exception as e:
            failed += 1
            log.warning("reindex_failed", image_id=image_id, error=str(e))

    with _index_lock:
        if pending:
            dim = len(pending[0][1])
            _index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
            vecs = np.stack([v for _, v in pending])
            ids = np.array([i for i, _ in pending], dtype="int64")
            _index.add_with_ids(vecs, ids)
            _save_index()
        size = _index.ntotal if _index is not None else 0
    return {"indexed": len(pending), "failed": failed, "gallery_size": int(size)}


def gallery_size() -> int:
    idx = _index if _index is not None else _load_index()
    return int(idx.ntotal) if idx is not None else 0


def clear_index() -> None:
    """Drop the in-memory index and delete the persisted file."""
    global _index
    with _index_lock:
        _index = None
        path = _index_path()
        if os.path.exists(path):
            os.remove(path)
