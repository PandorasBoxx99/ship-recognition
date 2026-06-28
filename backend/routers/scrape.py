"""Scraper and job management endpoints."""

import json
import os
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.item import Item
from backend.models.job import Job
from backend.schemas.job import AnalyzeRequest, JobCreateRequest
from backend.services.scrape_service import (
    _scrape_log_path,
    analyze_website,
    find_images,
    start_scraping_job,
)

router = APIRouter(prefix="/api", tags=["scraper"])


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL required")
    return analyze_website(req.url)


@router.get("/jobs")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_job_to_dict(j) for j in jobs]


@router.post("/jobs", status_code=201)
def create_job(req: JobCreateRequest, db: Session = Depends(get_db)):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL required")

    name = req.name or req.url

    job = Job(
        url=req.url,
        name=name,
        limit_count=req.limit,
        delay_min=req.delay_min,
        delay_max=req.delay_max,
        vpn_required=req.vpn_required,
    )
    db.add(job)
    db.flush()

    images = find_images(req.url, limit=req.limit)
    added = 0
    skipped = 0

    for img in images:
        image_url = img["url"]

        # Duplicate check: skip if same image_url already exists in DB
        existing = db.query(Item).filter(Item.image_url == image_url).first()
        if existing:
            skipped += 1
            continue

        # Build metadata JSON from scraped details
        source_domain = urlparse(req.url).netloc.replace("www.", "")
        meta = {"source": source_domain, "scraped_at": datetime.now().isoformat()}
        meta_keys = [
            "vessel_url", "photo_id", "detail_url",
            "flag", "year_built", "length", "beam", "gross_tonnage", "dwt",
            "location", "photographer", "photo_date",
            "latitude", "longitude", "coordinates",
            "weather", "port", "country",
        ]
        for key in meta_keys:
            if key in img and img[key]:
                meta[key] = img[key]

        db.add(
            Item(
                job_id=job.id,
                source_url=img.get("source_page", img.get("vessel_url", "")),
                image_url=image_url,
                ship_name=img.get("alt", ""),
                ship_type=img.get("ship_type", ""),
                imo_number=img.get("imo", ""),
                mmsi=img.get("mmsi", ""),
                metadata_=json.dumps(meta),
            )
        )
        added += 1

    job.total_items = added
    db.commit()
    db.refresh(job)

    result = _job_to_dict(job)
    result["skipped_duplicates"] = skipped
    return result


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = db.query(Item).filter(Item.job_id == job_id).all()
    return {"job": _job_to_dict(job), "items": [_item_to_dict(i) for i in items]}


@router.post("/jobs/{job_id}/start")
def start_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == "running":
        raise HTTPException(status_code=400, detail="Job laeuft bereits")

    if job.vpn_required and not settings.VPN_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="VPN ist erforderlich, aber in den Einstellungen deaktiviert.",
        )

    # Check if there are pending items (needed for resume)
    pending = db.query(Item).filter(Item.job_id == job_id, Item.status == "pending").count()
    if pending == 0:
        raise HTTPException(status_code=400, detail="Keine ausstehenden Items zum Herunterladen.")

    # Reset failed items to pending so they get retried on resume
    failed_items = db.query(Item).filter(Item.job_id == job_id, Item.status == "failed").all()
    for item in failed_items:
        item.status = "pending"
        item.error_message = None
    if failed_items:
        db.commit()

    start_scraping_job(job_id)
    return {"status": "started", "job_id": job_id, "pending_items": pending + len(failed_items)}


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "paused"
    db.commit()
    return {"status": "paused"}


@router.delete("/jobs/{job_id}/delete")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db.query(Item).filter(Item.job_id == job_id).delete()
    db.query(Job).filter(Job.id == job_id).delete()
    db.commit()
    return {"status": "deleted"}


@router.get("/jobs/{job_id}/log")
def get_job_log(job_id: int, lines: int = 100):
    """Get scrape log entries for a specific job (last N lines)."""
    if not os.path.exists(_scrape_log_path):
        return {"lines": [], "file": _scrape_log_path}

    job_prefix = f"[Job {job_id}]"
    matching = []
    try:
        with open(_scrape_log_path, encoding="utf-8") as f:
            for line in f:
                if job_prefix in line:
                    matching.append(line.rstrip())
    except Exception:
        pass

    return {"lines": matching[-lines:], "total": len(matching)}


def _job_to_dict(job: Job) -> dict:
    """Convert Job ORM to dict matching original Flask JSON shape."""
    return {
        "id": job.id,
        "url": job.url,
        "name": job.name,
        "status": job.status,
        "total_items": job.total_items or 0,
        "downloaded": job.downloaded or 0,
        "limit_count": job.limit_count,
        "delay_min": job.delay_min,
        "delay_max": job.delay_max,
        "vpn_required": 1 if job.vpn_required else 0,
        "created_at": str(job.created_at) if job.created_at else None,
        "started_at": str(job.started_at) if job.started_at else None,
        "completed_at": str(job.completed_at) if job.completed_at else None,
        "error_message": job.error_message,
    }


def _item_to_dict(item: Item) -> dict:
    """Convert Item ORM to dict matching original Flask JSON shape."""
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
