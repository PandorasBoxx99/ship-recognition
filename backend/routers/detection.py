"""Ship detection and cropping endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.ship import Ship
from backend.services.detection_service import (
    detect_and_crop_for_ship,
    get_detection_status,
    start_batch_detection,
)

router = APIRouter(tags=["detection"])


@router.post("/api/v2/ships/{ship_id}/detect")
def detect_ship(
    ship_id: int,
    confidence_threshold: float = Query(0.5, ge=0.1, le=1.0),
    padding_pct: float = Query(0.05, ge=0.0, le=0.5),
    db: Session = Depends(get_db),
):
    """Run ship detection on all images of a ship entity."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")

    stats = detect_and_crop_for_ship(ship_id, confidence_threshold, padding_pct)
    return {"ship_id": ship_id, "ship_name": ship.name, **stats}


@router.post("/api/detect/batch")
def batch_detect(
    confidence_threshold: float = Query(0.5, ge=0.1, le=1.0),
):
    """Start batch ship detection for all ships (background thread)."""
    if not start_batch_detection(confidence_threshold=confidence_threshold):
        raise HTTPException(status_code=409, detail="Erkennung laeuft bereits")
    return {"status": "started"}


@router.get("/api/detect/batch/status")
def batch_detect_status():
    """Get batch detection progress."""
    return get_detection_status()
