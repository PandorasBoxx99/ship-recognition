"""Advanced ML endpoints — similarity search, explainability, review queue."""

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.image import Image, ImageAnnotation
from backend.models.ship import Ship

import structlog

log = structlog.get_logger()

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


# ============ SIMILARITY SEARCH ============

@router.post("/similarity/search")
def similarity_search(
    image_path: str = "",
    image_id: int | None = None,
    top_k: int = 10,
    db: Session = Depends(get_db),
):
    """Find visually similar images using ViT embeddings.

    Extracts embedding from the query image, computes cosine similarity
    against all stored embeddings. Falls back to same-type matching if
    embeddings are not available.
    """
    # Determine query image path
    if image_id:
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img:
            raise HTTPException(status_code=404, detail="Image not found")
        image_path = img.file_path

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail="Valid image_path or image_id required")

    try:
        query_embedding = _extract_embedding(image_path)
    except Exception as e:
        log.warning("embedding_extraction_failed", error=str(e))
        # Fallback: classify and find same-type images
        return _fallback_similarity(image_path, top_k, db)

    # Compare against all images with known types
    images = (
        db.query(Image, Ship.ship_type, Ship.name)
        .outerjoin(Ship, Image.ship_id == Ship.id)
        .filter(Image.file_path != image_path)
        .limit(500)  # limit for performance
        .all()
    )

    scored = []
    for img, ship_type, ship_name in images:
        if not img.file_path or not os.path.exists(img.file_path):
            continue
        try:
            emb = _extract_embedding(img.file_path)
            sim = _cosine_similarity(query_embedding, emb)
            scored.append({
                "image_id": img.id,
                "file_path": img.file_path,
                "ship_type": ship_type,
                "ship_name": ship_name,
                "similarity": round(sim, 4),
            })
        except Exception:
            continue

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return {"results": scored[:top_k], "method": "embedding"}


def _extract_embedding(image_path: str) -> list[float]:
    """Extract feature vector from ViT model's penultimate layer."""
    import torch
    from PIL import Image as PILImage

    try:
        from ml_engine import load_model, _model, _processor
        load_model()

        image = PILImage.open(image_path).convert("RGB")
        inputs = _processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = _model(**inputs, output_hidden_states=True)
            # Use CLS token from last hidden state
            embedding = outputs.hidden_states[-1][:, 0, :].squeeze().tolist()

        return embedding
    except Exception:
        raise


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _fallback_similarity(image_path: str, top_k: int, db: Session) -> dict:
    """Fallback: classify image and return same-type images."""
    from backend.services.ml_service import classify_image

    results = classify_image(image_path)
    if isinstance(results, dict) and "error" in results:
        return {"results": [], "method": "fallback", "error": results["error"]}

    if not results:
        return {"results": [], "method": "fallback"}

    predicted_type = results[0]["label"]

    images = (
        db.query(Image, Ship.name)
        .outerjoin(Ship, Image.ship_id == Ship.id)
        .filter(Ship.ship_type == predicted_type)
        .limit(top_k)
        .all()
    )

    return {
        "results": [
            {
                "image_id": img.id,
                "file_path": img.file_path,
                "ship_name": name,
                "ship_type": predicted_type,
                "similarity": None,
            }
            for img, name in images
        ],
        "method": "type_match",
        "predicted_type": predicted_type,
    }


# ============ EXPLAINABILITY (Grad-CAM) ============

@router.post("/explain")
def explain_prediction(
    image_path: str = "",
    image_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Generate Grad-CAM heatmap showing what the model focuses on.

    Returns base64-encoded heatmap overlay image and prediction details.
    """
    if image_id:
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img:
            raise HTTPException(status_code=404, detail="Image not found")
        image_path = img.file_path

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail="Valid image_path or image_id required")

    try:
        heatmap_b64, prediction, confidence = _generate_gradcam(image_path)
        return {
            "heatmap_base64": heatmap_b64,
            "prediction": prediction,
            "confidence": confidence,
            "image_path": image_path,
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Grad-CAM dependencies not available: {e}")
    except Exception as e:
        log.error("gradcam_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Grad-CAM generation failed: {e}")


def _generate_gradcam(image_path: str) -> tuple[str, str, float]:
    """Generate Grad-CAM heatmap for a ViT model prediction."""
    import base64
    import io
    import numpy as np
    import torch
    from PIL import Image as PILImage

    from ml_engine import load_model, _model, _processor

    load_model()

    image = PILImage.open(image_path).convert("RGB")
    inputs = _processor(images=image, return_tensors="pt")

    # Forward pass with gradients
    _model.eval()
    inputs["pixel_values"].requires_grad_(True)
    outputs = _model(**inputs)
    logits = outputs.logits

    # Get predicted class
    pred_idx = logits.argmax(dim=-1).item()
    confidence = torch.softmax(logits, dim=-1)[0, pred_idx].item()
    pred_label = _model.config.id2label.get(pred_idx, str(pred_idx))

    # Backward pass for gradients
    _model.zero_grad()
    logits[0, pred_idx].backward()

    # Get gradient w.r.t. input pixels
    gradients = inputs["pixel_values"].grad[0]
    # Average across channels, take absolute value
    saliency = gradients.abs().mean(dim=0).detach().numpy()

    # Normalize to 0-255
    saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-8)
    saliency = (saliency * 255).astype(np.uint8)

    # Resize to original image size
    heatmap = PILImage.fromarray(saliency).resize(image.size, PILImage.BILINEAR)

    # Create colored overlay
    import colorsys
    heatmap_colored = PILImage.new("RGBA", image.size)
    heatmap_array = np.array(heatmap)
    colored = np.zeros((*heatmap_array.shape, 4), dtype=np.uint8)
    for y in range(heatmap_array.shape[0]):
        for x in range(heatmap_array.shape[1]):
            val = heatmap_array[y, x] / 255.0
            r, g, b = colorsys.hsv_to_rgb(0.7 - val * 0.7, 1.0, 1.0)
            colored[y, x] = [int(r * 255), int(g * 255), int(b * 255), int(val * 150)]
    heatmap_colored = PILImage.fromarray(colored, "RGBA")

    # Overlay on original
    composite = image.convert("RGBA")
    composite = PILImage.alpha_composite(composite, heatmap_colored)

    # Encode to base64
    buf = io.BytesIO()
    composite.convert("RGB").save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return b64, pred_label, confidence


# ============ HUMAN-IN-THE-LOOP REVIEW QUEUE ============

@router.get("/review/queue")
def review_queue(
    limit: int = 20,
    min_confidence: float = 0.0,
    max_confidence: float = 0.7,
    db: Session = Depends(get_db),
):
    """Get images needing human review (low confidence or unreviewed)."""
    from backend.models.ml import InferenceLog

    # Images with low confidence predictions
    low_confidence = (
        db.query(
            InferenceLog.image_id,
            InferenceLog.input_path,
            InferenceLog.top_prediction,
            InferenceLog.confidence,
            InferenceLog.created_at,
        )
        .filter(
            InferenceLog.confidence >= min_confidence,
            InferenceLog.confidence <= max_confidence,
        )
        .order_by(InferenceLog.confidence.asc())
        .limit(limit)
        .all()
    )

    # Images with pending review status
    pending_review = (
        db.query(Image)
        .filter(Image.review_status == "pending")
        .limit(limit)
        .all()
    )

    return {
        "low_confidence": [
            {
                "image_id": r.image_id,
                "input_path": r.input_path,
                "prediction": r.top_prediction,
                "confidence": r.confidence,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in low_confidence
        ],
        "pending_review": [
            {
                "image_id": img.id,
                "file_path": img.file_path,
                "label_status": img.label_status,
                "review_status": img.review_status,
            }
            for img in pending_review
        ],
    }


class ReviewDecision(BaseModel):
    image_id: int
    decision: str  # "approve", "reject", "correct"
    correct_label: str | None = None
    reviewer: str = "human"
    notes: str = ""


@router.post("/review/decide")
def review_decide(req: ReviewDecision, db: Session = Depends(get_db)):
    """Submit a review decision for an image."""
    img = db.query(Image).filter(Image.id == req.image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    if req.decision == "approve":
        img.review_status = "approved"
        img.label_status = "reviewed"
    elif req.decision == "reject":
        img.review_status = "rejected"
    elif req.decision == "correct":
        img.review_status = "corrected"
        img.label_status = "reviewed"
        # Store correction as annotation
        annotation = ImageAnnotation(
            image_id=req.image_id,
            annotation_type="label_correction",
            bbox_json=json.dumps({"correct_label": req.correct_label, "notes": req.notes}),
            reviewer=req.reviewer,
        )
        db.add(annotation)
    else:
        raise HTTPException(status_code=400, detail="Decision must be: approve, reject, or correct")

    db.commit()
    return {"status": "reviewed", "image_id": req.image_id, "decision": req.decision}


@router.get("/review/stats")
def review_stats(db: Session = Depends(get_db)):
    """Get review queue statistics."""
    total = db.query(func.count()).select_from(Image).scalar() or 0
    approved = db.query(func.count()).select_from(Image).filter(Image.review_status == "approved").scalar() or 0
    rejected = db.query(func.count()).select_from(Image).filter(Image.review_status == "rejected").scalar() or 0
    corrected = db.query(func.count()).select_from(Image).filter(Image.review_status == "corrected").scalar() or 0
    pending = db.query(func.count()).select_from(Image).filter(Image.review_status == "pending").scalar() or 0
    unreviewed = total - approved - rejected - corrected - pending

    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "corrected": corrected,
        "pending": pending,
        "unreviewed": unreviewed,
    }
