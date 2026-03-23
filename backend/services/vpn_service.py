"""VPN service — NordVPN integration via REST API + CLI fallback.

Uses NordVPN API (api.nordvpn.com) for:
- Token validation (Basic Auth with token)
- Server recommendations by country
- Connection status

Falls back to NordVPN CLI if available.
"""

import base64
import subprocess
import time

import requests
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.vpn import VPNLog

import structlog

log = structlog.get_logger()

NORDVPN_API = "https://api.nordvpn.com"


# ============ API-Based Functions ============

def _api_headers(token: str | None = None) -> dict:
    """Build auth headers for NordVPN API."""
    api_key = token or settings.VPN_API_KEY
    if not api_key:
        return {}
    # NordVPN API uses Basic Auth: username="token", password=<access_token>
    credentials = base64.b64encode(f"token:{api_key}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def test_token(token: str | None = None) -> dict:
    """Validate NordVPN access token via API.

    Calls /v1/users/services/credentials — returns 200 if token is valid.
    """
    api_key = token or settings.VPN_API_KEY
    if not api_key:
        return {"valid": False, "error": "Kein Access Token konfiguriert"}

    try:
        resp = requests.get(
            f"{NORDVPN_API}/v1/users/services/credentials",
            headers=_api_headers(api_key),
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            return {
                "valid": True,
                "message": "Token gueltig — Zugang verifiziert",
                "username": data.get("username", ""),
                "nordlynx_private_key": "***" if data.get("nordlynx_private_key") else None,
            }
        elif resp.status_code == 401:
            return {"valid": False, "error": "Token ungueltig oder abgelaufen"}
        else:
            return {"valid": False, "error": f"API-Fehler: HTTP {resp.status_code}"}

    except requests.Timeout:
        return {"valid": False, "error": "Timeout — NordVPN API nicht erreichbar"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def get_recommended_servers(country: str = "Germany", limit: int = 5) -> dict:
    """Get recommended NordVPN servers for a country via API."""
    # Map country names to NordVPN country IDs
    country_ids = {
        "Germany": 81, "Netherlands": 153, "Switzerland": 209,
        "United States": 228, "United Kingdom": 227,
        "Sweden": 208, "Austria": 14, "France": 74,
    }
    country_id = country_ids.get(country, 81)

    try:
        resp = requests.get(
            f"{NORDVPN_API}/v1/servers/recommendations",
            params={
                "filters[country_id]": country_id,
                "filters[servers_technologies][identifier]": "openvpn_udp",
                "limit": limit,
            },
            timeout=10,
        )

        if resp.status_code == 200:
            servers = resp.json()
            return {
                "country": country,
                "servers": [
                    {
                        "name": s.get("name"),
                        "hostname": s.get("hostname"),
                        "load": s.get("load"),
                        "ip": s.get("station"),
                    }
                    for s in servers
                ],
            }
        return {"error": f"API-Fehler: HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


# ============ CLI-Based Functions (fallback) ============

def _find_nordvpn_binary() -> str | None:
    """Find NordVPN CLI binary path."""
    import os
    import shutil

    # Check configured binary
    if shutil.which(settings.VPN_BINARY):
        return settings.VPN_BINARY

    # Windows: check common install paths
    candidates = [
        r"C:\Program Files\NordVPN\NordVPN.exe",
        r"C:\Program Files (x86)\NordVPN\NordVPN.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def get_vpn_status() -> dict:
    """Check VPN connection status (CLI or API-based)."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    binary = _find_nordvpn_binary()
    if not binary:
        # No CLI — check via API if token exists
        if settings.VPN_API_KEY:
            token_result = test_token()
            return {
                "connected": False,
                "token_valid": token_result.get("valid", False),
                "error": "NordVPN CLI nicht gefunden. Token-Status: " +
                         ("gueltig" if token_result.get("valid") else "ungueltig"),
            }
        return {"connected": False, "error": "NordVPN CLI nicht gefunden und kein Token konfiguriert"}

    try:
        result = subprocess.run(
            [binary, "status"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout

        connected = "Connected" in output or "Verbunden" in output
        country = None
        ip = None

        for line in output.split("\n"):
            if "Country:" in line or "Land:" in line:
                country = line.split(":")[-1].strip()
            if "Server IP:" in line or "IP:" in line:
                ip = line.split(":")[-1].strip()

        return {"connected": connected, "country": country, "ip": ip, "raw": output}
    except Exception as e:
        return {"connected": False, "error": str(e)}


def connect_vpn(country: str, db: Session) -> dict:
    """Connect to VPN via CLI."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    binary = _find_nordvpn_binary()
    if not binary:
        return {"connected": False, "error": "NordVPN CLI nicht gefunden"}

    try:
        # Login with token first if available
        if settings.VPN_API_KEY:
            subprocess.run(
                [binary, "login", "--token", settings.VPN_API_KEY],
                capture_output=True, timeout=15,
            )

        subprocess.run(
            [binary, "connect", country],
            capture_output=True, timeout=30,
        )
        time.sleep(3)
        status = get_vpn_status()

        db.add(VPNLog(
            action="connect", country=country,
            ip_address=status.get("ip"),
            success=status.get("connected", False),
        ))
        db.commit()
        return status
    except Exception as e:
        return {"connected": False, "error": str(e)}


def disconnect_vpn(db: Session) -> dict:
    """Disconnect from VPN via CLI."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    binary = _find_nordvpn_binary()
    if not binary:
        return {"connected": False, "error": "NordVPN CLI nicht gefunden"}

    try:
        subprocess.run([binary, "disconnect"], capture_output=True, timeout=10)
        db.add(VPNLog(action="disconnect", success=True))
        db.commit()
        return {"connected": False}
    except Exception as e:
        return {"error": str(e)}


def rotate_vpn(db: Session) -> dict:
    """Rotate VPN IP (disconnect + reconnect)."""
    disconnect_vpn(db)
    time.sleep(2)
    country = settings.VPN_DEFAULT_COUNTRY or "Germany"
    return connect_vpn(country, db)
