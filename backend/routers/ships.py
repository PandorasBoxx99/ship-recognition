"""Ship listing and detail endpoints."""

import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.classification import Classification
from backend.models.item import Item
from backend.models.job import Job

router = APIRouter(prefix="/api/ships", tags=["ships"])


@router.get("")
def get_ships(
    type: str = Query("", alias="type"),
    source: str = "",
    search: str = "",
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    """Get all downloaded ships with pagination and filtering."""
    # Get distinct types
    type_rows = (
        db.query(Item.ship_type)
        .filter(Item.ship_type.isnot(None), Item.ship_type != "")
        .distinct()
        .order_by(Item.ship_type)
        .all()
    )
    types = [t[0] for t in type_rows]

    # Get distinct sources (extract domain from job URL)
    source_rows = (
        db.query(Job.url)
        .join(Item, Item.job_id == Job.id)
        .filter(Item.status == "downloaded")
        .distinct()
        .all()
    )
    sources = sorted({
        urlparse(r[0]).netloc.replace("www.", "")
        for r in source_rows if r[0]
    })

    # Base query: downloaded items joined with jobs
    query = (
        db.query(
            Item,
            Job.name.label("job_name"),
            Job.url.label("job_url"),
        )
        .outerjoin(Job, Item.job_id == Job.id)
        .filter(Item.status == "downloaded")
    )

    if type:
        query = query.filter(Item.ship_type == type)
    if source:
        query = query.filter(Job.url.like(f"%{source}%"))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Item.ship_name.like(pattern)) | (Item.imo_number.like(pattern))
        )

    total = query.count()
    offset = (page - 1) * per_page
    rows = query.order_by(Item.downloaded_at.desc()).offset(offset).limit(per_page).all()

    ships = []
    for item, job_name, job_url in rows:
        d = _item_to_dict(item)
        d["job_name"] = job_name
        d["job_url"] = job_url
        ships.append(d)

    return {
        "ships": ships,
        "types": types,
        "sources": sources,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/stats")
def ships_stats(db: Session = Depends(get_db)):
    """Statistics about downloaded ships."""
    type_stats = (
        db.query(
            Item.ship_type,
            func.count().label("count"),
            func.count(func.distinct(Item.job_id)).label("sources"),
        )
        .filter(
            Item.status == "downloaded",
            Item.ship_type.isnot(None),
            Item.ship_type != "",
        )
        .group_by(Item.ship_type)
        .order_by(func.count().desc())
        .all()
    )

    total = db.query(func.count()).select_from(Item).filter(Item.status == "downloaded").scalar()
    classified = db.query(func.count()).select_from(Classification).scalar()

    return {
        "total_downloaded": total or 0,
        "total_classified": classified or 0,
        "by_type": [
            {"type": t.ship_type, "count": t.count, "sources": t.sources} for t in type_stats
        ],
    }


@router.get("/{ship_id}")
def get_ship(ship_id: int, db: Session = Depends(get_db)):
    """Get single ship details."""
    row = (
        db.query(
            Item,
            Job.name.label("job_name"),
            Job.url.label("job_url"),
        )
        .outerjoin(Job, Item.job_id == Job.id)
        .filter(Item.id == ship_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Ship not found")

    item, job_name, job_url = row
    result = _item_to_dict(item)
    result["job_name"] = job_name
    result["job_url"] = job_url

    # Parse metadata JSON if present
    if result.get("metadata"):
        try:
            result["metadata"] = json.loads(result["metadata"])
        except (json.JSONDecodeError, TypeError):
            pass

    return result


def _item_to_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "job_id": item.job_id,
        "source_url": item.source_url,
        "image_url": item.image_url,
        "local_path": item.local_path,
        "ship_name": item.ship_name,
        "ship_type": item.ship_type,
        "imo_number": item.imo_number,
        "mmsi": item.mmsi,
        "metadata": item.metadata_,
        "status": item.status,
        "created_at": str(item.created_at) if item.created_at else None,
        "downloaded_at": str(item.downloaded_at) if item.downloaded_at else None,
        "error_message": item.error_message,
    }
