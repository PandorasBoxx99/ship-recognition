"""Settings and predefined URL management endpoints."""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.settings import PredefinedURL
from backend.schemas.settings import URLCreateRequest

router = APIRouter(prefix="/api/urls", tags=["settings"])


@router.get("")
def get_urls(db: Session = Depends(get_db)):
    """List predefined URLs."""
    urls = db.query(PredefinedURL).order_by(PredefinedURL.name).all()
    return [_url_to_dict(u) for u in urls]


@router.post("", status_code=201)
def add_url(req: URLCreateRequest, db: Session = Depends(get_db)):
    """Add a predefined URL."""
    url = req.url.strip()
    name = req.name.strip()

    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    if not name:
        name = urlparse(url).netloc.replace("www.", "").split(".")[0].title()

    try:
        new_url = PredefinedURL(url=url, name=name)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        return _url_to_dict(new_url)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="URL already exists")


@router.delete("/{url_id}")
def delete_url(url_id: int, db: Session = Depends(get_db)):
    """Delete a predefined URL."""
    db.query(PredefinedURL).filter(PredefinedURL.id == url_id).delete()
    db.commit()
    return {"status": "deleted"}


def _url_to_dict(url: PredefinedURL) -> dict:
    return {
        "id": url.id,
        "url": url.url,
        "name": url.name,
        "created_at": str(url.created_at) if url.created_at else None,
    }
