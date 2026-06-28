"""Settings and predefined URL management endpoints."""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import BASE_DIR, settings
from backend.database import get_db
from backend.models.settings import PredefinedURL
from backend.schemas.settings import URLCreateRequest

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/urls")
def get_urls(db: Session = Depends(get_db)):
    """List predefined URLs."""
    urls = db.query(PredefinedURL).order_by(PredefinedURL.name).all()
    return [_url_to_dict(u) for u in urls]


@router.post("/urls", status_code=201)
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


@router.delete("/urls/{url_id}")
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


# ===== VPN Settings =====

class VPNSettingsRequest(BaseModel):
    vpn_provider: str | None = None
    vpn_user: str | None = None
    vpn_api_key: str | None = None
    vpn_default_country: str | None = None
    vpn_auto_connect: bool | None = None
    vpn_rotation: str | None = None
    vpn_enabled: bool | None = None


@router.get("/settings/vpn")
def get_vpn_settings():
    """Get current VPN configuration from .env / settings."""
    return {
        "vpn_enabled": settings.VPN_ENABLED,
        "vpn_provider": settings.VPN_PROVIDER,
        "vpn_binary": settings.VPN_BINARY,
        "vpn_user": settings.VPN_USER,
        "vpn_api_key": "***" if settings.VPN_API_KEY else "",
        "vpn_default_country": settings.VPN_DEFAULT_COUNTRY,
        "vpn_auto_connect": settings.VPN_AUTO_CONNECT,
        "vpn_rotation": settings.VPN_ROTATION,
    }


@router.put("/settings/vpn")
def update_vpn_settings(req: VPNSettingsRequest):
    """Update VPN settings in .env file."""
    env_path = BASE_DIR / ".env"

    # Read existing .env or start from example
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
    else:
        example = BASE_DIR / ".env.example"
        content = example.read_text(encoding="utf-8") if example.exists() else ""

    # Update each field
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    for key, value in updates.items():
        env_key = key.upper()
        str_value = str(value).lower() if isinstance(value, bool) else str(value)

        if f"{env_key}=" in content:
            # Replace existing line
            lines = content.split("\n")
            content = "\n".join(
                f"{env_key}={str_value}" if line.startswith(f"{env_key}=") else line
                for line in lines
            )
        else:
            # Append
            content = content.rstrip() + f"\n{env_key}={str_value}\n"

    env_path.write_text(content, encoding="utf-8")

    # Update runtime settings
    for key, value in updates.items():
        attr = key.upper()
        if hasattr(settings, attr):
            object.__setattr__(settings, attr, value)

    return {"status": "saved", "updated": list(updates.keys())}
