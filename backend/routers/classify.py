"""Classification endpoints."""

import json
import os
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

import structlog

log = structlog.get_logger()

from backend.config import settings
from backend.database import get_db
from backend.models.classification import Classification
from backend.models.item import Item
from backend.services import ml_service

router = APIRouter(prefix="/api", tags=["classification"])


@router.post("/classify")
async def classify_upload(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Classify an uploaded ship image."""
    if not image.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    image_data = await image.read()

    # Save upload for reference
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}"
    save_path = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(image_data)

    results = ml_service.classify_image(image_data)

    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=500, detail=results["error"])

    # Save to DB
    if results:
        db.add(
            Classification(
                image_path=save_path,
                predicted_type=results[0]["label"],
                confidence=results[0]["confidence"],
                all_predictions=json.dumps(results),
            )
        )
        db.commit()

    return {"predictions": results, "image_path": save_path, "filename": filename}


@router.post("/classify/ship/{ship_id}")
def classify_ship(ship_id: int, db: Session = Depends(get_db)):
    """Classify an existing ship from the database."""
    item = db.query(Item).filter(Item.id == ship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ship not found")

    if not item.local_path or not os.path.exists(item.local_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    results = ml_service.classify_image(item.local_path)

    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=500, detail=results["error"])

    if results:
        item.ship_type = results[0]["label"]
        db.add(
            Classification(
                item_id=ship_id,
                image_path=item.local_path,
                predicted_type=results[0]["label"],
                confidence=results[0]["confidence"],
                all_predictions=json.dumps(results),
            )
        )
        db.commit()

    return {"ship_id": ship_id, "predictions": results}


# --- Batch classification ---
_batch_status = {"running": False, "progress": 0, "total": 0, "message": "Idle"}


def _run_batch_classify(item_ids: list[int]):
    """Background thread for batch classification."""
    from backend.database import SessionLocal
    from backend.models.item import Item

    global _batch_status
    db = SessionLocal()
    try:
        _batch_status["running"] = True
        _batch_status["total"] = len(item_ids)
        _batch_status["progress"] = 0
        _batch_status["message"] = "Läuft..."

        for i, item_id in enumerate(item_ids):
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item or not item.local_path or not os.path.exists(item.local_path):
                continue

            try:
                results = ml_service.classify_image(item.local_path)
                if results and not (isinstance(results, dict) and "error" in results):
                    item.ship_type = results[0]["label"]
                    db.add(
                        Classification(
                            item_id=item_id,
                            image_path=item.local_path,
                            predicted_type=results[0]["label"],
                            confidence=results[0]["confidence"],
                            all_predictions=json.dumps(results),
                        )
                    )
                    db.commit()
            except Exception as e:
                log.error("batch_classify_error", item_id=item_id, error=str(e))

            _batch_status["progress"] = i + 1

        _batch_status["message"] = f"Fertig: {_batch_status['progress']}/{_batch_status['total']}"
    finally:
        _batch_status["running"] = False
        db.close()


@router.post("/classify/batch")
def batch_classify(
    job_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Classify all unclassified downloaded items. Optionally filter by job_id."""
    if _batch_status["running"]:
        raise HTTPException(status_code=409, detail="Batch classification already running")

    from backend.models.item import Item

    query = db.query(Item.id).filter(
        Item.status == "downloaded",
        Item.local_path.isnot(None),
        Item.ship_type.is_(None) | (Item.ship_type == ""),
    )
    if job_id:
        query = query.filter(Item.job_id == job_id)

    item_ids = [row[0] for row in query.all()]

    if not item_ids:
        return {"status": "nothing_to_classify", "count": 0}

    thread = threading.Thread(target=_run_batch_classify, args=(item_ids,), daemon=True)
    thread.start()

    return {"status": "started", "count": len(item_ids)}


@router.get("/classify/batch/status")
def batch_classify_status():
    """Get batch classification progress."""
    return _batch_status


@router.get("/model/info")
def model_info():
    """Get model information."""
    return ml_service.get_model_info()


@router.get("/classifications")
def get_classifications(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    """Get classification history."""
    total = db.query(func.count()).select_from(Classification).scalar()
    offset = (page - 1) * per_page

    rows = (
        db.query(Classification)
        .order_by(Classification.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    results = []
    for r in rows:
        item = {
            "id": r.id,
            "item_id": r.item_id,
            "image_path": r.image_path,
            "predicted_type": r.predicted_type,
            "confidence": r.confidence,
            "all_predictions": r.all_predictions,
            "model_name": r.model_name,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        if item.get("all_predictions"):
            try:
                item["all_predictions"] = json.loads(item["all_predictions"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(item)

    return {
        "classifications": results,
        "total": total or 0,
        "page": page,
        "pages": max(1, ((total or 0) + per_page - 1) // per_page),
    }
