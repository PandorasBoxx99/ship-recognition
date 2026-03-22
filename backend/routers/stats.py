"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.classification import Classification
from backend.models.item import Item
from backend.models.job import Job

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Global statistics for the dashboard."""
    total_jobs = db.query(func.count()).select_from(Job).scalar() or 0
    total_items = db.query(func.count()).select_from(Item).scalar() or 0
    downloaded = (
        db.query(func.count()).select_from(Item).filter(Item.status == "downloaded").scalar() or 0
    )
    pending = (
        db.query(func.count()).select_from(Item).filter(Item.status == "pending").scalar() or 0
    )
    failed = (
        db.query(func.count()).select_from(Item).filter(Item.status == "failed").scalar() or 0
    )
    classifications = db.query(func.count()).select_from(Classification).scalar() or 0

    # Ship type distribution
    type_rows = (
        db.query(Item.ship_type, func.count().label("count"))
        .filter(Item.ship_type.isnot(None), Item.ship_type != "")
        .group_by(Item.ship_type)
        .order_by(func.count().desc())
        .all()
    )

    return {
        "total_jobs": total_jobs,
        "total_items": total_items,
        "downloaded": downloaded,
        "pending": pending,
        "failed": failed,
        "classifications": classifications,
        "type_distribution": [{"type": t.ship_type, "count": t.count} for t in type_rows],
    }
