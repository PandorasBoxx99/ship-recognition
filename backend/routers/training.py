"""Training endpoints."""

import os

from fastapi import APIRouter, HTTPException

from backend.schemas.training import TrainingStartRequest
from backend.services import ml_service

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("/status")
def training_status():
    """Get training status."""
    return ml_service.get_training_status()


@router.post("/start")
def training_start(req: TrainingStartRequest):
    """Start model training."""
    if not req.dataset_dir or not os.path.exists(req.dataset_dir):
        raise HTTPException(
            status_code=400, detail=f"Dataset directory not found: {req.dataset_dir}"
        )

    result = ml_service.start_training(
        req.dataset_dir,
        epochs=req.epochs,
        batch_size=req.batch_size,
        learning_rate=req.learning_rate,
    )
    return result


@router.get("/datasets")
def training_datasets():
    """List available datasets for training."""
    return ml_service.get_available_datasets()
