"""Ship sync service — matches downloaded Items to normalized Ship entities.

Matching priority:
1. IMO number (globally unique, permanent)
2. MMSI (unique at any point in time)
3. Normalized ship name (fuzzy fallback)
4. No match → create new Ship
"""

import json
import os
import re

import structlog
from sqlalchemy.orm import Session

from backend.models.image import Image
from backend.models.item import Item
from backend.models.ship import Ship, ShipAlias

log = structlog.get_logger()


def normalize_ship_name(name: str) -> str:
    """Normalize a ship name for matching.

    Strips prefixes (M/V, MV, SS, HMS, etc.), uppercases,
    removes extra whitespace and punctuation.
    """
    if not name:
        return ""
    s = name.strip().upper()
    # Remove common vessel prefixes
    s = re.sub(r"^(M/V|MV|M\.V\.|SS|HMS|MT|M/T|RV|R/V|SY|S/Y|FV|F/V)\s+", "", s)
    # Remove punctuation except hyphens
    s = re.sub(r"[^A-Z0-9\s\-]", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_item_metadata(item: Item) -> dict:
    """Parse the JSON metadata blob from an Item."""
    if not item.metadata_:
        return {}
    try:
        return json.loads(item.metadata_)
    except (json.JSONDecodeError, TypeError):
        return {}


def _merge_field(ship: Ship, field: str, value) -> bool:
    """Set a field on Ship only if currently empty. Returns True if updated."""
    if not value:
        return False
    current = getattr(ship, field, None)
    if not current:
        setattr(ship, field, value)
        return True
    return False


def find_or_create_ship(db: Session, item: Item) -> Ship:
    """Match an Item to an existing Ship or create a new one.

    Matching priority: IMO → MMSI → normalized name → new Ship.
    Also merges metadata from the Item into the Ship (fill empty fields only).
    """
    imo = (item.imo_number or "").strip()
    mmsi = (item.mmsi or "").strip()
    name = (item.ship_name or "").strip()
    canonical = normalize_ship_name(name)
    meta = _parse_item_metadata(item)

    ship = None
    match_method = None

    # 1. IMO match (highest confidence)
    if imo:
        ship = db.query(Ship).filter(Ship.imo == imo).first()
        if ship:
            match_method = "imo"

    # 2. MMSI match (high confidence, but skip if IMO conflict)
    if not ship and mmsi:
        candidate = db.query(Ship).filter(Ship.mmsi == mmsi).first()
        if candidate:
            # Safety: if both have IMO but they differ, this is a different ship
            if imo and candidate.imo and candidate.imo != imo:
                log.warning("mmsi_imo_conflict",
                            mmsi=mmsi, item_imo=imo, ship_imo=candidate.imo)
            else:
                ship = candidate
                match_method = "mmsi"

    # 3. Normalized name match (lowest confidence)
    if not ship and canonical:
        ship = db.query(Ship).filter(Ship.canonical_name == canonical).first()
        if not ship:
            # Also check aliases
            alias = db.query(ShipAlias).filter(
                ShipAlias.alias_name == canonical
            ).first()
            if alias:
                ship = db.query(Ship).filter(Ship.id == alias.ship_id).first()
        if ship:
            match_method = "name"

    # 4. No match — create new Ship
    if not ship:
        ship = Ship(
            name=name or f"Unbekannt #{item.id}",
            canonical_name=canonical or None,
            imo=imo or None,
            mmsi=mmsi or None,
            ship_type=item.ship_type or meta.get("ship_type") or None,
            flag=meta.get("flag"),
            country=meta.get("country"),
            year_built=_parse_int(meta.get("year_built")),
        )
        db.add(ship)
        db.flush()  # get ship.id
        match_method = "new"
        log.info("ship_created", ship_id=ship.id, name=ship.name, imo=imo)

    # Merge metadata into existing ship (fill empty fields only)
    _merge_field(ship, "imo", imo)
    _merge_field(ship, "mmsi", mmsi)
    _merge_field(ship, "canonical_name", canonical)
    _merge_field(ship, "ship_type", item.ship_type or meta.get("ship_type"))
    _merge_field(ship, "flag", meta.get("flag"))
    _merge_field(ship, "country", meta.get("country"))
    _merge_field(ship, "year_built", _parse_int(meta.get("year_built")))

    # Add alias if name differs from existing ship name
    if name and match_method != "new":
        existing_names = {normalize_ship_name(ship.name)}
        existing_names.update(
            normalize_ship_name(a.alias_name) for a in ship.aliases
        )
        if canonical and canonical not in existing_names:
            source = meta.get("source", "")
            db.add(ShipAlias(ship_id=ship.id, alias_name=name, source=source))
            log.info("alias_added", ship_id=ship.id, alias=name, source=source)

    log.info("ship_matched", ship_id=ship.id, item_id=item.id,
             method=match_method, name=name)

    return ship


def sync_item_to_ship(db: Session, item: Item) -> tuple[Ship, Image | None]:
    """Create Ship + Image from a downloaded Item.

    Idempotent: skips if an Image with this source_url already exists for the ship.
    """
    # Skip if item has no image
    if not item.local_path:
        return find_or_create_ship(db, item), None

    ship = find_or_create_ship(db, item)
    meta = _parse_item_metadata(item)

    # Check if image already linked (idempotent)
    existing_image = db.query(Image).filter(
        Image.ship_id == ship.id,
        Image.source_url == item.image_url,
    ).first()
    if existing_image:
        return ship, existing_image

    # Determine source name from job URL or metadata
    source_name = meta.get("source", "")

    # Get file size
    file_size = None
    try:
        file_size = os.path.getsize(item.local_path) if item.local_path else None
    except OSError:
        pass

    image = Image(
        ship_id=ship.id,
        file_path=item.local_path,
        file_name=os.path.basename(item.local_path) if item.local_path else None,
        source_url=item.image_url,
        source_name=source_name,
        file_size=file_size,
    )
    db.add(image)

    log.info("image_linked", ship_id=ship.id, image_url=item.image_url,
             source=source_name)

    return ship, image


def backfill_all_items(db: Session) -> dict:
    """Process all downloaded Items and sync to Ship+Image entities.

    Idempotent: skips Items that already have linked Images.
    """
    items = db.query(Item).filter(Item.status == "downloaded").all()

    stats = {"total_items": len(items), "ships_created": 0, "ships_matched": 0,
             "images_linked": 0, "aliases_added": 0, "skipped": 0}

    alias_count_before = db.query(ShipAlias).count()
    ship_count_before = db.query(Ship).count()

    for item in items:
        ship, image = sync_item_to_ship(db, item)
        if image:
            stats["images_linked"] += 1
        else:
            stats["skipped"] += 1

    db.commit()

    stats["ships_created"] = db.query(Ship).count() - ship_count_before
    stats["ships_matched"] = stats["total_items"] - stats["ships_created"] - stats["skipped"]
    stats["aliases_added"] = db.query(ShipAlias).count() - alias_count_before
    stats["total_ships"] = db.query(Ship).count()

    log.info("backfill_complete", **stats)
    return stats


def _parse_int(value) -> int | None:
    """Safely parse an integer from a string or None."""
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None
