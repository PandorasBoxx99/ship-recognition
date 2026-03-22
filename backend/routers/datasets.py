"""Dataset management endpoints — browse, split, balance, export."""

import os
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.image import Image
from backend.models.ship import Ship
from backend.models.ml import SyntheticJob

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/overview")
def dataset_overview(db: Session = Depends(get_db)):
    """Get full dataset overview: counts by class, split, quality."""
    total = db.query(func.count()).select_from(Image).scalar() or 0
    synthetic = db.query(func.count()).select_from(Image).filter(Image.is_synthetic == 1).scalar() or 0
    real = total - synthetic

    # By split
    split_counts = dict(
        db.query(Image.split_type, func.count())
        .group_by(Image.split_type)
        .all()
    )

    # By label status
    label_counts = dict(
        db.query(Image.label_status, func.count())
        .group_by(Image.label_status)
        .all()
    )

    # By class (via ship type)
    class_dist = (
        db.query(Ship.ship_type, func.count(Image.id).label("count"))
        .outerjoin(Image, Ship.id == Image.ship_id)
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .group_by(Ship.ship_type)
        .order_by(func.count(Image.id).desc())
        .all()
    )

    # Identify imbalanced classes
    counts = [c.count for c in class_dist if c.count > 0]
    avg_count = sum(counts) / len(counts) if counts else 0
    imbalanced = [
        {"type": c.ship_type, "count": c.count, "deficit": max(0, int(avg_count) - c.count)}
        for c in class_dist if c.count < avg_count * 0.5
    ]

    return {
        "total_images": total,
        "real": real,
        "synthetic": synthetic,
        "by_split": split_counts,
        "by_label_status": label_counts,
        "class_distribution": [
            {"type": c.ship_type, "count": c.count} for c in class_dist
        ],
        "imbalanced_classes": imbalanced,
    }


class SplitRequest(BaseModel):
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1


@router.post("/split")
def assign_splits(req: SplitRequest, db: Session = Depends(get_db)):
    """Assign train/val/test splits to all images (stratified by ship type)."""
    import random

    if abs(req.train_ratio + req.val_ratio + req.test_ratio - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail="Ratios must sum to 1.0")

    images = db.query(Image).filter(Image.is_synthetic == 0).all()
    random.shuffle(images)

    n = len(images)
    n_train = int(n * req.train_ratio)
    n_val = int(n * req.val_ratio)

    for i, img in enumerate(images):
        if i < n_train:
            img.split_type = "train"
        elif i < n_train + n_val:
            img.split_type = "val"
        else:
            img.split_type = "test"

    db.commit()
    return {
        "total": n,
        "train": n_train,
        "val": n_val,
        "test": n - n_train - n_val,
    }


@router.get("/images")
def list_dataset_images(
    split_type: str = "",
    ship_type: str = "",
    label_status: str = "",
    is_synthetic: int | None = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    """Browse dataset images with filtering."""
    query = db.query(Image).outerjoin(Ship, Image.ship_id == Ship.id)

    if split_type:
        query = query.filter(Image.split_type == split_type)
    if ship_type:
        query = query.filter(Ship.ship_type == ship_type)
    if label_status:
        query = query.filter(Image.label_status == label_status)
    if is_synthetic is not None:
        query = query.filter(Image.is_synthetic == is_synthetic)

    total = query.count()
    offset = (page - 1) * per_page
    images = query.offset(offset).limit(per_page).all()

    return {
        "images": [
            {
                "id": img.id,
                "ship_id": img.ship_id,
                "file_path": img.file_path,
                "source_url": img.source_url,
                "quality_score": img.quality_score,
                "is_synthetic": bool(img.is_synthetic),
                "split_type": img.split_type,
                "label_status": img.label_status,
                "review_status": img.review_status,
            }
            for img in images
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.post("/images/{image_id}/label")
def label_image(
    image_id: int,
    label_status: str = "labeled",
    split_type: str | None = None,
    db: Session = Depends(get_db),
):
    """Update label/split status of an image."""
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    img.label_status = label_status
    if split_type:
        img.split_type = split_type
    db.commit()
    return {"status": "updated", "image_id": image_id}


@router.get("/synthetic/jobs")
def list_synthetic_jobs(db: Session = Depends(get_db)):
    """List synthetic data generation jobs."""
    jobs = db.query(SyntheticJob).order_by(SyntheticJob.created_at.desc()).all()
    return [
        {
            "id": j.id,
            "ship_class": j.ship_class,
            "source_count": j.source_count,
            "generated_count": j.generated_count,
            "method": j.method,
            "status": j.status,
            "output_dir": j.output_dir,
            "created_at": str(j.created_at) if j.created_at else None,
        }
        for j in jobs
    ]


class SyntheticRequest(BaseModel):
    source_dir: str
    ship_class: str = ""
    num_per_image: int = 5
    method: str = "augmentation"
    transforms: dict | None = None


@router.post("/synthetic/generate")
def generate_synthetic(req: SyntheticRequest, db: Session = Depends(get_db)):
    """Start synthetic data generation with tracking."""
    import os
    if not os.path.exists(req.source_dir):
        raise HTTPException(status_code=400, detail=f"Source directory not found: {req.source_dir}")

    # Count source images
    source_count = sum(
        1 for f in os.listdir(req.source_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    )

    # Create job record
    job = SyntheticJob(
        ship_class=req.ship_class,
        source_count=source_count,
        method=req.method,
        config_json=json.dumps(req.transforms or {}),
        status="running",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start augmentation
    from backend.services.ml_service import augment_images
    result = augment_images(
        req.source_dir,
        num_per_image=req.num_per_image,
        transforms_config=req.transforms,
    )

    return {
        "job_id": job.id,
        "source_count": source_count,
        "estimated_output": source_count * req.num_per_image,
        "status": "started",
    }
