"""ML model registry endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.ml import MLModel

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models(db: Session = Depends(get_db)):
    """List all registered models."""
    models = db.query(MLModel).order_by(MLModel.created_at.desc()).all()
    return [_model_to_dict(m) for m in models]


@router.get("/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db)):
    """Get a specific model."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_to_dict(model)


@router.post("/{model_id}/activate")
def activate_model(model_id: int, db: Session = Depends(get_db)):
    """Set a model as the active model (deactivates all others)."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Deactivate all
    db.query(MLModel).update({MLModel.is_active: 0})
    # Activate selected
    model.is_active = 1
    db.commit()

    return {"status": "activated", "model_id": model_id, "model_name": model.name}


@router.post("")
def register_model(
    name: str,
    version: str,
    model_type: str,
    path: str,
    framework: str = "pytorch",
    task_type: str = "ship_classification",
    input_size: str = "224x224",
    db: Session = Depends(get_db),
):
    """Register a new model in the registry."""
    model = MLModel(
        name=name,
        version=version,
        model_type=model_type,
        framework=framework,
        task_type=task_type,
        path=path,
        input_size=input_size,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_to_dict(model)


def _model_to_dict(model: MLModel) -> dict:
    result = {
        "id": model.id,
        "name": model.name,
        "version": model.version,
        "model_type": model.model_type,
        "framework": model.framework,
        "task_type": model.task_type,
        "path": model.path,
        "input_size": model.input_size,
        "is_active": bool(model.is_active),
        "created_at": str(model.created_at) if model.created_at else None,
    }
    if model.label_map_json:
        try:
            result["label_map"] = json.loads(model.label_map_json)
        except (json.JSONDecodeError, TypeError):
            result["label_map"] = None
    if model.metrics_json:
        try:
            result["metrics"] = json.loads(model.metrics_json)
        except (json.JSONDecodeError, TypeError):
            result["metrics"] = None
    return result
