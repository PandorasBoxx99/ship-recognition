"""VPN management endpoints."""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import vpn_service

router = APIRouter(prefix="/api/vpn", tags=["vpn"])


@router.get("/status")
def vpn_status():
    return vpn_service.get_vpn_status()


@router.post("/connect")
def vpn_connect(
    country: str = Body("Germany", embed=True),
    db: Session = Depends(get_db),
):
    return vpn_service.connect_vpn(country, db)


@router.post("/disconnect")
def vpn_disconnect(db: Session = Depends(get_db)):
    return vpn_service.disconnect_vpn(db)


@router.post("/rotate")
def vpn_rotate(db: Session = Depends(get_db)):
    return vpn_service.rotate_vpn(db)


@router.post("/test-token")
def vpn_test_token(token: str = Body("", embed=True)):
    """Validate NordVPN access token via NordVPN REST API."""
    return vpn_service.test_token(token if token else None)


@router.get("/servers")
def vpn_servers(country: str = "Germany", limit: int = 5):
    """Get recommended NordVPN servers for a country via API."""
    return vpn_service.get_recommended_servers(country, limit)
