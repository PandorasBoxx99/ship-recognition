"""Agent service — action registry and system context for AI agent control."""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import (
    Classification,
    Image,
    Item,
    Job,
    MLModel,
    ScrapeSource,
    Ship,
    TrainingRun,
)

log = structlog.get_logger()


# ---- Action Registry ----

def _action_run_scraper(params: dict, db: Session) -> dict:
    """Start a scraping job for a given source."""
    from backend.services.scrape_service import start_scraping_job
    job_id = params.get("job_id")
    if not job_id:
        return {"error": "job_id required"}
    start_scraping_job(int(job_id))
    return {"status": "started", "job_id": job_id}


def _action_train_model(params: dict, db: Session) -> dict:
    """Start model training."""
    from backend.services.ml_service import start_training
    dataset_dir = params.get("dataset_dir", "")
    if not dataset_dir:
        return {"error": "dataset_dir required"}
    return start_training(
        dataset_dir,
        epochs=params.get("epochs", 5),
        batch_size=params.get("batch_size", 8),
        learning_rate=params.get("learning_rate", 5e-5),
    )


def _action_predict(params: dict, db: Session) -> dict:
    """Run inference on an image."""
    from backend.services.ml_service import classify_image
    image_path = params.get("image_path", "")
    if not image_path:
        return {"error": "image_path required"}
    results = classify_image(image_path)
    if isinstance(results, dict) and "error" in results:
        return results
    return {"predictions": results}


def _action_generate_synthetic(params: dict, db: Session) -> dict:
    """Generate synthetic training data."""
    from backend.services.ml_service import augment_images
    source_dir = params.get("source_dir", "")
    if not source_dir:
        return {"error": "source_dir required"}
    return augment_images(
        source_dir,
        num_per_image=params.get("num_per_image", 5),
        transforms_config=params.get("transforms"),
    )


def _action_rebuild_dataset(params: dict, db: Session) -> dict:
    """Return dataset statistics for rebuilding."""
    ships = db.query(Ship).count()
    images = db.query(Image).count()
    synthetic = db.query(Image).filter(Image.is_synthetic == 1).count()
    unlabeled = db.query(Image).filter(
        (Image.label_status.is_(None)) | (Image.label_status == "unlabeled")
    ).count()
    return {
        "ships": ships,
        "images": images,
        "synthetic": synthetic,
        "unlabeled": unlabeled,
    }


AGENT_ACTIONS: dict[str, Any] = {
    "run_scraper": _action_run_scraper,
    "train_model": _action_train_model,
    "predict": _action_predict,
    "generate_synthetic": _action_generate_synthetic,
    "rebuild_dataset": _action_rebuild_dataset,
}


def execute_action(action: str, params: dict, db: Session) -> dict:
    """Execute a registered agent action."""
    handler = AGENT_ACTIONS.get(action)
    if not handler:
        return {
            "status": "error",
            "errors": [
                {"code": "UNKNOWN_ACTION", "message": f"Action '{action}' not found"}
            ],
        }

    log.info("agent_action", action=action, params=params)
    try:
        result = handler(params, db)
        return {"status": "success", "data": result}
    except Exception as e:
        log.error("agent_action_failed", action=action, error=str(e))
        return {"status": "error", "errors": [{"code": "ACTION_FAILED", "message": str(e)}]}


def get_system_context(db: Session) -> dict:
    """Return full system context for agent decision-making."""
    # Counts
    total_ships = db.query(func.count()).select_from(Ship).scalar() or 0
    total_images = db.query(func.count()).select_from(Image).scalar() or 0
    total_items = db.query(func.count()).select_from(Item).scalar() or 0
    downloaded = db.query(func.count()).select_from(Item).filter(
        Item.status == "downloaded"
    ).scalar() or 0
    classified = db.query(func.count()).select_from(Classification).scalar() or 0

    # Active model
    active_model = db.query(MLModel).filter(MLModel.is_active == 1).first()

    # Running jobs
    running_jobs = db.query(Job).filter(Job.status == "running").count()

    # Sources
    sources = db.query(ScrapeSource).filter(ScrapeSource.is_active == 1).count()

    # Recent training
    last_training = (
        db.query(TrainingRun)
        .order_by(TrainingRun.created_at.desc())
        .first()
    )

    # Type distribution
    type_dist = (
        db.query(Ship.ship_type, func.count().label("count"))
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .group_by(Ship.ship_type)
        .all()
    )

    # Data gaps (types with few images)
    image_per_type = (
        db.query(Ship.ship_type, func.count(Image.id).label("image_count"))
        .outerjoin(Image, Ship.id == Image.ship_id)
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .group_by(Ship.ship_type)
        .all()
    )
    data_gaps = [
        {"type": t.ship_type, "image_count": t.image_count}
        for t in image_per_type if t.image_count < 10
    ]

    return {
        "timestamp": datetime.now().isoformat(),
        "data": {
            "ships": total_ships,
            "images": total_images,
            "items_legacy": total_items,
            "downloaded": downloaded,
            "classified": classified,
        },
        "model": {
            "name": active_model.name if active_model else None,
            "version": active_model.version if active_model else None,
            "type": active_model.model_type if active_model else None,
            "is_active": True if active_model else False,
        },
        "jobs": {
            "running": running_jobs,
        },
        "sources": {
            "active": sources,
        },
        "last_training": {
            "status": last_training.status if last_training else None,
            "finished_at": (
                str(last_training.finished_at)
                if last_training and last_training.finished_at
                else None
            ),
        },
        "type_distribution": [
            {"type": t.ship_type, "count": t.count} for t in type_dist
        ],
        "data_gaps": data_gaps,
    }


def get_capabilities() -> dict:
    """Return list of available agent actions and their parameters."""
    return {
        "actions": [
            {
                "name": "run_scraper",
                "description": "Start a scraping job",
                "params": {"job_id": "int (required)"},
            },
            {
                "name": "train_model",
                "description": "Start model training",
                "params": {
                    "dataset_dir": "str (required)",
                    "epochs": "int (default: 5)",
                    "batch_size": "int (default: 8)",
                    "learning_rate": "float (default: 5e-5)",
                },
            },
            {
                "name": "predict",
                "description": "Classify a single image",
                "params": {"image_path": "str (required)"},
            },
            {
                "name": "generate_synthetic",
                "description": "Generate synthetic training data",
                "params": {
                    "source_dir": "str (required)",
                    "num_per_image": "int (default: 5)",
                    "transforms": "dict (optional)",
                },
            },
            {
                "name": "rebuild_dataset",
                "description": "Get dataset statistics for rebuilding",
                "params": {},
            },
        ]
    }
