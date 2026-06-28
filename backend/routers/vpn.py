"""VPN management endpoints (NordVPN SOCKS5)."""

from fastapi import APIRouter, Body, HTTPException

from backend.config import update_env_settings
from backend.services import vpn_service

router = APIRouter(prefix="/api/vpn", tags=["vpn"])


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


@router.post("/test-token")
def vpn_test_token(token: str = Body("", embed=True)):
    """Validate a NordVPN access token via the NordVPN REST API."""
    return vpn_service.test_token(token if token else None)
