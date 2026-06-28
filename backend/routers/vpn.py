"""VPN management endpoints."""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import update_env_settings
from backend.database import get_db
from backend.services import vpn_service

router = APIRouter(prefix="/api/vpn", tags=["vpn"])


@router.get("/status")
def vpn_status():
    return vpn_service.get_vpn_status()


@router.get("/connection")
def vpn_connection():
    """Live connection info: direct IP, VPN exit IP, server, selectable countries."""
    return vpn_service.get_connection_info()


@router.put("/config")
def vpn_config(
    enabled: bool | None = Body(None, embed=True),
    proxy_country: str | None = Body(None, embed=True),
):
    """Toggle the VPN and/or change the SOCKS5 exit country in real time."""
    if proxy_country is not None and proxy_country not in vpn_service.SOCKS5_PROXIES:
        allowed = ", ".join(vpn_service.AVAILABLE_PROXY_COUNTRIES)
        raise HTTPException(status_code=400, detail=f"Ungueltiges Land. Erlaubt: {allowed}")

    updates: dict = {}
    if enabled is not None:
        updates["vpn_enabled"] = enabled
    if proxy_country is not None:
        updates["vpn_proxy_country"] = proxy_country
    if updates:
        update_env_settings(updates)

    return vpn_service.get_connection_info()


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
