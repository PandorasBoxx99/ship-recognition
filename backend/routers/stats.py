"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.classification import Classification
from backend.models.image import Image
from backend.models.item import Item
from backend.models.job import Job
from backend.models.ship import Ship

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Global statistics for the dashboard.

    Ship data is read from the normalized v2 tables (ships/images), which are the
    single source of truth. Pending/failed come from the scrape queue (v1 items),
    which is the ingestion layer.
    """
    total_jobs = db.query(func.count()).select_from(Job).scalar() or 0

    # Ship data — v2 is the source of truth
    total_ships = db.query(func.count()).select_from(Ship).scalar() or 0
    total_images = db.query(func.count()).select_from(Image).scalar() or 0

    # Scrape-pipeline (queue) metrics from the ingestion layer
    pending = (
        db.query(func.count()).select_from(Item).filter(Item.status == "pending").scalar() or 0
    )
    failed = (
        db.query(func.count()).select_from(Item).filter(Item.status == "failed").scalar() or 0
    )
    classifications = db.query(func.count()).select_from(Classification).scalar() or 0

    # Ship type distribution from the normalized ships table
    type_rows = (
        db.query(Ship.ship_type, func.count().label("count"))
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .group_by(Ship.ship_type)
        .order_by(func.count().desc())
        .all()
    )

    return {
        "total_jobs": total_jobs,
        "total_ships": total_ships,
        "total_images": total_images,
        "pending": pending,
        "failed": failed,
        "classifications": classifications,
        "type_distribution": [{"type": t.ship_type, "count": t.count} for t in type_rows],
    }
