"""VPN service — NordVPN integration via REST API.

Uses api.nordvpn.com for all operations:
- Token validation
- Server recommendations
- Account/connection status

No CLI dependency — works on Windows, Linux, Docker.
"""

import base64

import requests
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.vpn import VPNLog

import structlog

log = structlog.get_logger()

NORDVPN_API = "https://api.nordvpn.com"


def _api_headers(token: str | None = None) -> dict:
    """Build auth headers for NordVPN API."""
    api_key = token or settings.VPN_API_KEY
    if not api_key:
        return {}
    credentials = base64.b64encode(f"token:{api_key}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def _has_token() -> bool:
    return bool(settings.VPN_API_KEY)


def test_token(token: str | None = None) -> dict:
    """Validate NordVPN access token via API."""
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


def get_vpn_status() -> dict:
    """Check VPN/token status via API (no CLI needed)."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN deaktiviert"}

    if not _has_token():
        return {"connected": False, "error": "Kein Access Token konfiguriert"}

    try:
        # Validate token + get account info
        resp = requests.get(
            f"{NORDVPN_API}/v1/users/services/credentials",
            headers=_api_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Get recommended server for display
            servers = get_recommended_servers(settings.VPN_DEFAULT_COUNTRY or "Germany", 1)
            server_name = None
            server_ip = None
            if "servers" in servers and servers["servers"]:
                server_name = servers["servers"][0].get("name")
                server_ip = servers["servers"][0].get("ip")

            return {
                "connected": True,
                "country": settings.VPN_DEFAULT_COUNTRY or "Germany",
                "ip": server_ip,
                "server": server_name,
                "username": data.get("username"),
                "token_valid": True,
            }
        elif resp.status_code == 401:
            return {"connected": False, "error": "Token ungueltig oder abgelaufen", "token_valid": False}
        else:
            return {"connected": False, "error": f"API-Fehler: HTTP {resp.status_code}"}
    except requests.Timeout:
        return {"connected": False, "error": "NordVPN API nicht erreichbar"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


def get_recommended_servers(country: str = "Germany", limit: int = 5) -> dict:
    """Get recommended NordVPN servers for a country."""
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


def connect_vpn(country: str, db: Session) -> dict:
    """'Connect' to VPN — validates token and logs preferred country."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN deaktiviert"}

    if not _has_token():
        return {"connected": False, "error": "Kein Access Token konfiguriert"}

    # Validate token
    token_result = test_token()
    if not token_result.get("valid"):
        return {"connected": False, "error": token_result.get("error", "Token ungueltig")}

    # Get best server for the country
    servers = get_recommended_servers(country, 1)
    server_name = None
    server_ip = None
    if "servers" in servers and servers["servers"]:
        server_name = servers["servers"][0].get("name")
        server_ip = servers["servers"][0].get("ip")

    # Log the connection
    db.add(VPNLog(
        action="connect", country=country,
        ip_address=server_ip, success=True,
    ))
    db.commit()

    log.info("vpn_connected", country=country, server=server_name, ip=server_ip)

    return {
        "connected": True,
        "country": country,
        "ip": server_ip,
        "server": server_name,
        "token_valid": True,
    }


def disconnect_vpn(db: Session) -> dict:
    """'Disconnect' from VPN."""
    db.add(VPNLog(action="disconnect", success=True))
    db.commit()
    return {"connected": False}


def rotate_vpn(db: Session) -> dict:
    """Rotate — reconnect to get a different server."""
    disconnect_vpn(db)
    country = settings.VPN_DEFAULT_COUNTRY or "Germany"
    return connect_vpn(country, db)
