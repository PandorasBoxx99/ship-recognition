"""Scraper and job management endpoints."""

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.item import Item
from backend.models.job import Job
from backend.schemas.job import AnalyzeRequest, JobCreateRequest
from backend.services import vpn_service
from backend.services.scrape_service import (
    active_jobs,
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
    for img in images:
        db.add(
            Item(
                job_id=job.id,
                source_url=img["source_page"],
                image_url=img["url"],
                ship_name=img.get("alt", ""),
            )
        )

    job.total_items = len(images)
    db.commit()
    db.refresh(job)

    return _job_to_dict(job)


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

    if job.vpn_required:
        vpn_status = vpn_service.get_vpn_status()
        if not vpn_status.get("connected"):
            raise HTTPException(status_code=400, detail="VPN not connected. Please connect first.")

    start_scraping_job(job_id)
    return {"status": "started", "job_id": job_id}


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
