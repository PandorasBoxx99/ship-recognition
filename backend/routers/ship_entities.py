"""Ship entity CRUD endpoints (normalized ships table)."""

import os

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


class MergeRequest(BaseModel):
    target_ship_id: int


def _get_image_src(file_path: str | None) -> str | None:
    """Convert a local file path to a /downloads/ URL."""
    if not file_path:
        return None
    parts = file_path.replace("\\", "/").split("/")
    dl_idx = None
    for i, p in enumerate(parts):
        if p == "downloads":
            dl_idx = i
            break
    if dl_idx is not None:
        return "/downloads/" + "/".join(parts[dl_idx + 1:])
    return None


@router.get("")
def list_ships(
    search: str = "",
    ship_type: str = "",
    source: str = "",
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db),
):
    """List all ship entities with pagination, filtering, and image counts."""
    query = db.query(Ship)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Ship.name.like(pattern)) | (Ship.imo.like(pattern)) | (Ship.mmsi.like(pattern))
        )
    if ship_type:
        query = query.filter(Ship.ship_type == ship_type)
    if source:
        # Filter ships that have images from this source
        ship_ids_with_source = (
            db.query(Image.ship_id)
            .filter(Image.source_name.like(f"%{source}%"))
            .distinct()
            .subquery()
        )
        query = query.filter(Ship.id.in_(db.query(ship_ids_with_source)))

    total = query.count()
    offset = (page - 1) * per_page
    ships = query.order_by(Ship.updated_at.desc()).offset(offset).limit(per_page).all()

    # Get image count per ship (originals only)
    image_counts = dict(
        db.query(Image.ship_id, func.count(Image.id))
        .filter(Image.parent_image_id.is_(None))
        .group_by(Image.ship_id)
        .all()
    )

    # Get first image per ship for thumbnail (prefer primary crop)
    thumbnails: dict[int, str | None] = {}
    for ship in ships:
        first_img = (
            db.query(Image.file_path)
            .filter(Image.ship_id == ship.id)
            .order_by(Image.is_primary_crop.desc())
            .first()
        )
        thumbnails[ship.id] = _get_image_src(first_img[0]) if first_img else None

    # Get distinct types
    type_rows = (
        db.query(Ship.ship_type)
        .filter(Ship.ship_type.isnot(None), Ship.ship_type != "")
        .distinct()
        .order_by(Ship.ship_type)
        .all()
    )

    # Get distinct sources from images
    source_rows = (
        db.query(Image.source_name)
        .filter(Image.source_name.isnot(None), Image.source_name != "")
        .distinct()
        .order_by(Image.source_name)
        .all()
    )

    return {
        "ships": [
            {
                **_ship_to_dict(s),
                "image_count": image_counts.get(s.id, 0),
                "thumbnail": thumbnails.get(s.id),
            }
            for s in ships
        ],
        "types": [t[0] for t in type_rows],
        "sources": [s[0] for s in source_rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/{ship_id}")
def get_ship(ship_id: int, include_crops: bool = False, db: Session = Depends(get_db)):
    """Get a ship with its images, aliases, and source summary."""
    ship = db.query(Ship).filter(Ship.id == ship_id).first()
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")

    query = db.query(Image).filter(Image.ship_id == ship_id)
    all_images = query.all()

    aliases = db.query(ShipAlias).filter(ShipAlias.ship_id == ship_id).all()

    # Collect unique sources (from originals only)
    sources = sorted({img.source_name for img in all_images
                      if img.source_name and img.source_name != "detection_crop"})

    # Check which originals have crops
    originals_with_crops = {img.parent_image_id for img in all_images if img.parent_image_id}

    return {
        **_ship_to_dict(ship),
        "images": [
            {
                "id": img.id,
                "file_path": img.file_path,
                "src": _get_image_src(img.file_path),
                "source_url": img.source_url,
                "source_name": img.source_name,
                "file_size": img.file_size,
                "width": img.width,
                "height": img.height,
                "quality_score": img.quality_score,
                "is_synthetic": bool(img.is_synthetic),
                "parent_image_id": img.parent_image_id,
                "is_primary_crop": bool(img.is_primary_crop),
                "crop_rank": img.crop_rank,
                "has_crops": img.id in originals_with_crops,
                "created_at": str(img.created_at) if img.created_at else None,
            }
            for img in all_images
            if include_crops or img.parent_image_id is None
        ],
        "aliases": [
            {"id": a.id, "alias_name": a.alias_name, "source": a.source}
            for a in aliases
        ],
        "sources": sources,
        "image_count": sum(1 for img in all_images if img.parent_image_id is None),
    }


@router.post("/backfill")
def backfill(db: Session = Depends(get_db)):
    """Sync all downloaded Items to normalized Ship+Image entities."""
    from backend.services.ship_sync_service import backfill_all_items
    stats = backfill_all_items(db)
    return stats


@router.post("/{ship_id}/merge")
def merge_ships(ship_id: int, req: MergeRequest, db: Session = Depends(get_db)):
    """Merge another ship into this one. Moves all images and aliases."""
    target = db.query(Ship).filter(Ship.id == ship_id).first()
    source = db.query(Ship).filter(Ship.id == req.target_ship_id).first()
    if not target or not source:
        raise HTTPException(status_code=404, detail="Ship not found")
    if target.id == source.id:
        raise HTTPException(status_code=400, detail="Cannot merge ship with itself")

    # Move images
    moved_images = db.query(Image).filter(Image.ship_id == source.id).all()
    for img in moved_images:
        img.ship_id = target.id

    # Move aliases (add source ship name as alias too)
    moved_aliases = db.query(ShipAlias).filter(ShipAlias.ship_id == source.id).all()
    for alias in moved_aliases:
        alias.ship_id = target.id

    # Add source ship name as alias on target
    if source.name:
        db.add(ShipAlias(ship_id=target.id, alias_name=source.name, source="merge"))

    # Merge metadata (fill empty fields)
    for field in ["imo", "mmsi", "ship_type", "flag", "country", "year_built", "operator"]:
        src_val = getattr(source, field, None)
        tgt_val = getattr(target, field, None)
        if src_val and not tgt_val:
            setattr(target, field, src_val)

    # Delete source ship
    db.delete(source)
    db.commit()

    return {
        "status": "merged",
        "target_ship_id": target.id,
        "images_moved": len(moved_images),
        "aliases_moved": len(moved_aliases),
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
            "src": _get_image_src(img.file_path),
            "file_name": img.file_name,
            "source_url": img.source_url,
            "source_name": img.source_name,
            "file_size": img.file_size,
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
