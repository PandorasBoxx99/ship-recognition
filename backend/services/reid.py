"""ArcFace fine-tuning for ship re-identification.

Learns a projection on top of frozen DINOv2 features so that images of the SAME
specific ship cluster tightly and DIFFERENT ships are pushed apart (additive
angular margin / ArcFace). Identities come from the v2 `ships` grouping; only
ships with enough images become training classes.

The trained projection is saved to REID_DIR/projection.pt and picked up by
embedding_service.extract() — after which the FAISS gallery must be rebuilt
(the embedding dimension changes from the raw DINOv2 size to REID_EMBED_DIM).

torch is imported lazily so importing this module stays cheap at app startup.
"""

import os
import threading

import structlog

from backend.config import settings

log = structlog.get_logger()

_status = {"running": False, "progress": 0, "message": "Idle"}
_status_lock = threading.Lock()


def build_projection(in_dim: int, out_dim: int):
    """The projection head (defined as a plain Sequential so no nn.Module subclass
    needs torch imported at module load time). Same structure for train + load."""
    from torch import nn

    return nn.Sequential(
        nn.Linear(in_dim, out_dim),
        nn.BatchNorm1d(out_dim),
        nn.ReLU(inplace=True),
        nn.Linear(out_dim, out_dim),
    )


# Re-export under the name embedding_service expects
ProjectionHead = build_projection


def get_status() -> dict:
    with _status_lock:
        return dict(_status)


def _set_status(**kw) -> None:
    with _status_lock:
        _status.update(kw)


def readiness(db, min_images: int | None = None) -> dict:
    """How many ships have enough images to be trainable identities."""
    from collections import Counter

    from backend.models.image import Image

    min_images = min_images or settings.REID_MIN_IMAGES
    rows = (
        db.query(Image.ship_id)
        .filter(Image.ship_id.isnot(None), Image.file_path.isnot(None))
        .all()
    )
    counts = Counter(r[0] for r in rows)
    qualifying = {sid: c for sid, c in counts.items() if c >= min_images}
    return {
        "min_images": min_images,
        "total_ships_with_images": len(counts),
        "qualifying_ships": len(qualifying),
        "usable_images": sum(qualifying.values()),
        "ready": len(qualifying) >= 2,
        "has_trained_model": os.path.exists(os.path.join(settings.REID_DIR, "projection.pt")),
    }


def start_training(min_images: int | None = None, epochs: int | None = None) -> dict:
    """Atomically claim the training flag and launch a background thread."""
    with _status_lock:
        if _status["running"]:
            return {"error": "Training läuft bereits"}
        _status.update(running=True, progress=0, message="Initialisiere...")
    thread = threading.Thread(target=_run_training, args=(min_images, epochs), daemon=True)
    thread.start()
    return {"status": "started"}


def _run_training(min_images: int | None, epochs: int | None) -> None:
    from collections import defaultdict

    import numpy as np

    from backend.database import SessionLocal
    from backend.models.image import Image
    from backend.services import embedding_service

    min_images = min_images or settings.REID_MIN_IMAGES
    epochs = epochs or settings.REID_EPOCHS
    db = SessionLocal()
    try:
        rows = (
            db.query(Image.ship_id, Image.file_path)
            .filter(Image.ship_id.isnot(None), Image.file_path.isnot(None))
            .all()
        )
        groups: dict = defaultdict(list)
        for ship_id, file_path in rows:
            if file_path and os.path.exists(file_path):
                groups[ship_id].append(file_path)
        groups = {sid: fps for sid, fps in groups.items() if len(fps) >= min_images}

        if len(groups) < 2:
            _set_status(
                running=False, progress=0,
                message=f"Zu wenig Daten: {len(groups)} Schiffe mit >= {min_images} Bildern "
                        f"(mind. 2 noetig).",
            )
            return

        classes = {sid: idx for idx, sid in enumerate(groups)}
        feats, labels = [], []
        total = sum(len(v) for v in groups.values())
        done = 0
        for sid, fps in groups.items():
            for fp in fps:
                try:
                    feats.append(embedding_service.extract_raw(fp))
                    labels.append(classes[sid])
                except Exception as e:
                    log.warning("reid_feature_failed", path=fp, error=str(e))
                done += 1
                _set_status(progress=int(done / total * 50), message=f"Features {done}/{total}")

        if len(feats) < 2:
            _set_status(running=False, progress=0, message="Keine Features extrahierbar.")
            return

        result = _train_on_features(
            np.asarray(feats, dtype="float32"),
            labels,
            out_dim=settings.REID_EMBED_DIM,
            epochs=epochs,
            scale=settings.REID_ARCFACE_SCALE,
            margin=settings.REID_ARCFACE_MARGIN,
            lr=settings.REID_LEARNING_RATE,
            on_epoch=lambda e, tot, loss: _set_status(
                progress=50 + int(e / tot * 50), message=f"Epoche {e}/{tot}  loss={loss:.4f}"
            ),
        )

        # Activate the new projection and invalidate the (now wrong-dim) gallery
        embedding_service.reload_projection()
        embedding_service.clear_index()
        _set_status(
            running=False, progress=100,
            message=f"Fertig: {result['num_classes']} Schiffe, {result['samples']} Bilder, "
                    f"loss={result['final_loss']:.4f}. Bitte Galerie neu aufbauen.",
            **result,
        )
        log.info("reid_training_complete", **result)
    except Exception as e:
        _set_status(running=False, progress=0, message=f"Fehler: {e}")
        log.error("reid_training_failed", error=str(e))
    finally:
        db.close()


def _train_on_features(
    features, labels, *, out_dim, epochs, scale, margin, lr, on_epoch=None
) -> dict:
    """Train the projection + ArcFace head on precomputed feature vectors.

    Kept separate from DB/DINOv2 so it can be unit-tested with synthetic data.
    """
    import math

    import numpy as np
    import torch
    import torch.nn.functional as F  # noqa: N812
    from torch import nn

    device = "cuda" if torch.cuda.is_available() else "cpu"
    feats = torch.tensor(np.asarray(features, dtype="float32"), device=device)
    labs = torch.tensor(np.asarray(labels, dtype="int64"), device=device)
    in_dim = int(feats.shape[1])
    num_classes = int(labs.max().item()) + 1

    proj = build_projection(in_dim, out_dim).to(device).train()

    class ArcFace(nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = nn.Parameter(torch.empty(num_classes, out_dim))
            nn.init.xavier_uniform_(self.weight)
            self.cos_m, self.sin_m = math.cos(margin), math.sin(margin)
            self.th = math.cos(math.pi - margin)
            self.mm = math.sin(math.pi - margin) * margin

        def forward(self, x, target):
            cos = F.linear(F.normalize(x), F.normalize(self.weight)).clamp(-1 + 1e-7, 1 - 1e-7)
            sin = torch.sqrt(1.0 - cos.pow(2))
            phi = cos * self.cos_m - sin * self.sin_m  # cos(theta + margin)
            phi = torch.where(cos > self.th, phi, cos - self.mm)
            onehot = F.one_hot(target, num_classes).float()
            return scale * (onehot * phi + (1.0 - onehot) * cos)

    head = ArcFace().to(device)
    opt = torch.optim.Adam(list(proj.parameters()) + list(head.parameters()), lr=lr)
    ce = nn.CrossEntropyLoss()

    n = feats.shape[0]
    batch = min(64, n)
    final_loss = 0.0
    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        total, steps = 0.0, 0
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            if idx.numel() < 2:  # BatchNorm needs > 1 sample
                continue
            logits = head(proj(feats[idx]), labs[idx])
            loss = ce(logits, labs[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss.item())
            steps += 1
        final_loss = total / steps if steps else final_loss
        if on_epoch:
            on_epoch(epoch + 1, epochs, final_loss)

    os.makedirs(settings.REID_DIR, exist_ok=True)
    torch.save(
        {"state_dict": proj.to("cpu").state_dict(), "in_dim": in_dim, "out_dim": out_dim},
        os.path.join(settings.REID_DIR, "projection.pt"),
    )
    return {"num_classes": num_classes, "samples": int(n), "final_loss": float(final_loss)}
