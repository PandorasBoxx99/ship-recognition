"""Augmentation endpoints."""

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.augmentation import AugmentationLog
from backend.schemas.augmentation import AugmentRequest
from backend.services import ml_service

router = APIRouter(prefix="/api/augment", tags=["augmentation"])


@router.post("")
def start_augmentation(req: AugmentRequest, db: Session = Depends(get_db)):
    """Start image augmentation."""
    if not req.source_dir or not os.path.exists(req.source_dir):
        raise HTTPException(
            status_code=400, detail=f"Source directory not found: {req.source_dir}"
        )

    result = ml_service.augment_images(
        req.source_dir,
        num_per_image=req.num_per_image,
        transforms_config=req.transforms,
    )

    # Log to DB
    db.add(
        AugmentationLog(
            source_dir=req.source_dir,
            num_source_images=0,
            transforms_config=json.dumps(req.transforms or {}),
        )
    )
    db.commit()

    return result


@router.get("/status")
def augment_status():
    """Get augmentation status."""
    return ml_service.get_augment_status()
