"""Ship entity CRUD endpoints (normalized ships table)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.ship import Ship, ShipAlias
from backend.models.image import Image

router = APIRouter(prefix="/api/v2/ships", tags=["ships-v2"])


class ShipCreateRequest(BaseModel):
    name: str
    ship_type: str | None = None
    ship_class: str | None = None
    operator: str | None = None
    country: str | None = None
    flag: str | None = None
    imo: str | None = None
    mmsi: str | None = None
    year_built: int | None = None
    description: str | None = None


class ShipUpdateRequest(BaseModel):
    name: str | None = None
    ship_type: str | None = None
    ship_class: str | None = None
    operator: str | None = None
    country: str | None = None
    flag: str | None = None
    imo: str | None = None
    mmsi: str | None = None
    year_built: int | None = None
    description: str | None = None
    notes: str | None = None


@router.get("")
def list_ships(
    search: str = "",
    ship_type: str = "",
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    """List all ship entities with pagination and filtering."""
    query = db.query(Ship)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Ship.name.like(pattern)) | (Ship.imo.like(pattern)) | (Ship.mmsi.like(pattern))
        )
    if ship_type:
        query = query.filter(Ship.ship_type == ship_type)

    total = query.count()
    offset = (page - 1) * per_page
    ships = query.order_by(Ship.updated_at.desc()).offset(offset).limit(per_page).all()

    # Get image count per ship
    image_counts = dict(
        db.query(Image.ship_id, func.count(Image.id))
        .group_by(Image.ship_id)
        .all()
    )

    # Get distinct types
    type_rows = (
        db.query(Ship.ship_type)
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .distinct()
        .order_by(Ship.ship_type)
        .all()
    )

    return {
        "ships": [
            {**_ship_to_dict(s), "image_count": image_counts.get(s.id, 0)}
            for s in ships
        ],
        "types": [t[0] for t in type_rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/{ship_id}")
def get_ship(ship_id: int, db: Session = Depends(get_db)):
    """Get a ship with its images and aliases."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")

    images = db.query(Image).filter(Image.ship_id == ship_id).all()
    aliases = db.query(ShipAlias).filter(ShipAlias.ship_id == ship_id).all()

    return {
        **_ship_to_dict(ship),
        "images": [
            {
                "id": img.id,
                "file_path": img.file_path,
                "source_url": img.source_url,
                "quality_score": img.quality_score,
                "is_synthetic": bool(img.is_synthetic),
                "created_at": str(img.created_at) if img.created_at else None,
            }
            for img in images
        ],
        "aliases": [
            {"id": a.id, "alias_name": a.alias_name, "source": a.source}
            for a in aliases
        ],
    }


@router.post("", status_code=201)
def create_ship(req: ShipCreateRequest, db: Session = Depends(get_db)):
    """Create a new ship entity."""
    ship = Ship(**req.model_dump(exclude_none=True))
    db.add(ship)
    db.commit()
    db.refresh(ship)
    return _ship_to_dict(ship)


@router.put("/{ship_id}")
def update_ship(ship_id: int, req: ShipUpdateRequest, db: Session = Depends(get_db)):
    """Update ship metadata."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(ship, key, value)
    db.commit()
    db.refresh(ship)
    return _ship_to_dict(ship)


@router.delete("/{ship_id}")
def delete_ship(ship_id: int, db: Session = Depends(get_db)):
    """Delete a ship entity."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")
    db.delete(ship)
    db.commit()
    return {"status": "deleted"}


@router.post("/{ship_id}/aliases")
def add_alias(ship_id: int, alias_name: str, source: str = "", db: Session = Depends(get_db)):
    """Add an alias name for a ship."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")

    alias = ShipAlias(ship_id=ship_id, alias_name=alias_name, source=source)
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return {"id": alias.id, "alias_name": alias.alias_name, "source": alias.source}


@router.get("/{ship_id}/images")
def get_ship_images(ship_id: int, db: Session = Depends(get_db)):
    """Get all images for a ship."""
    images = db.query(Image).filter(Image.ship_id == ship_id).all()
    return [
        {
            "id": img.id,
            "file_path": img.file_path,
            "file_name": img.file_name,
            "source_url": img.source_url,
            "hash_sha256": img.hash_sha256,
            "quality_score": img.quality_score,
            "is_synthetic": bool(img.is_synthetic),
            "split_type": img.split_type,
            "label_status": img.label_status,
            "created_at": str(img.created_at) if img.created_at else None,
        }
        for img in images
    ]


def _ship_to_dict(ship: Ship) -> dict:
    return {
        "id": ship.id,
        "name": ship.name,
        "canonical_name": ship.canonical_name,
        "ship_type": ship.ship_type,
        "ship_class": ship.ship_class,
        "subtype": ship.subtype,
        "operator": ship.operator,
        "country": ship.country,
        "flag": ship.flag,
        "imo": ship.imo,
        "mmsi": ship.mmsi,
        "year_built": ship.year_built,
        "description": ship.description,
        "notes": ship.notes,
        "created_at": str(ship.created_at) if ship.created_at else None,
        "updated_at": str(ship.updated_at) if ship.updated_at else None,
    }
