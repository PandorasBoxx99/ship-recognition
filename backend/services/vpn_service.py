"""VPN service — NordVPN integration via REST API.

Uses api.nordvpn.com for all operations:
- Token validation
- Server recommendations
- Account/connection status
- Service credentials for SOCKS5 proxy routing

Scraper traffic is tunneled through NordVPN's SOCKS5 proxies (see get_proxies),
authenticated with the manual service credentials derived from the access token.

No CLI dependency — works on Windows, Linux, Docker.
"""

import base64
import threading

import requests
import structlog
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.vpn import VPNLog

log = structlog.get_logger()

NORDVPN_API = "https://api.nordvpn.com"

# NordVPN offers SOCKS5 proxies only in a limited set of countries.
# Host pattern: <country-code>.socks.nordhold.net on port 1080.
SOCKS5_PROXIES = {
    "Netherlands": "nl.socks.nordhold.net",
    "Sweden": "se.socks.nordhold.net",
    "United States": "us.socks.nordhold.net",
}
SOCKS5_PORT = 1080
AVAILABLE_PROXY_COUNTRIES = list(SOCKS5_PROXIES.keys())

# Cache the manual service credentials (username, password) for the process —
# they are stable per account and only need to be fetched once.
_creds_lock = threading.Lock()
_cached_creds: tuple[str, str] | None = None


def _api_headers(token: str | None = None) -> dict:
    """Build auth headers for NordVPN API."""
    api_key = token or settings.VPN_API_KEY
    if not api_key:
        return {}
    credentials = base64.b64encode(f"token:{api_key}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def _has_token() -> bool:
    return bool(settings.VPN_API_KEY)


def get_service_credentials(
    token: str | None = None, refresh: bool = False
) -> tuple[str, str] | None:
    """Fetch the NordVPN manual service credentials (username, password).

    These are derived from the access token and are used to authenticate against
    the SOCKS5 proxy / OpenVPN. Result is cached for the process.
    """
    global _cached_creds
    with _creds_lock:
        if _cached_creds and not refresh:
            return _cached_creds

        api_key = token or settings.VPN_API_KEY
        if not api_key:
            return None

        try:
            resp = requests.get(
                f"{NORDVPN_API}/v1/users/services/credentials",
                headers=_api_headers(api_key),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                username = data.get("username")
                password = data.get("password")
                if username and password:
                    _cached_creds = (username, password)
                    return _cached_creds
            log.warning("vpn_credentials_unavailable", status=resp.status_code)
        except Exception as e:
            log.warning("vpn_credentials_failed", error=str(e))
        return None


def resolve_proxy_country(country: str | None = None) -> str | None:
    """Pick a SOCKS5-capable country, falling back to the configured default."""
    for candidate in (country, settings.VPN_PROXY_COUNTRY, settings.VPN_DEFAULT_COUNTRY):
        if candidate in SOCKS5_PROXIES:
            return candidate
    return "Netherlands" if "Netherlands" in SOCKS5_PROXIES else None


def get_socks5_upstream(country: str | None = None) -> tuple[str, int, str, str] | None:
    """Return (host, port, username, password) for the NordVPN SOCKS5 proxy.

    Returns None when VPN is disabled, no token is set, credentials can't be
    fetched, or no SOCKS5 server is available for the chosen country.
    """
    if not settings.VPN_ENABLED:
        return None

    creds = get_service_credentials()
    if not creds:
        return None

    chosen = resolve_proxy_country(country)
    host = SOCKS5_PROXIES.get(chosen) if chosen else None
    if not host:
        return None

    return host, SOCKS5_PORT, creds[0], creds[1]


def get_proxies(country: str | None = None) -> dict | None:
    """Build a requests-style proxies dict routing through NordVPN SOCKS5."""
    upstream = get_socks5_upstream(country)
    if not upstream:
        return None

    host, port, username, password = upstream
    # socks5h => resolve DNS through the proxy too (no DNS leak)
    url = f"socks5h://{username}:{password}@{host}:{port}"
    return {"http": url, "https": url}


def get_exit_ip(proxies: dict) -> str | None:
    """Return the public IP seen through the given proxies, or None on failure."""
    try:
        resp = requests.get("https://api.ipify.org", proxies=proxies, timeout=15)
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception as e:
        log.warning("vpn_exit_ip_failed", error=str(e))
    return None


def get_direct_ip() -> str | None:
    """Return the machine's real public IP (without the VPN proxy)."""
    try:
        resp = requests.get("https://api.ipify.org", timeout=10)
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception as e:
        log.warning("vpn_direct_ip_failed", error=str(e))
    return None


def get_connection_info() -> dict:
    """Rich VPN connection info for the frontend.

    Includes the real (direct) IP, the VPN exit IP, the active SOCKS5 server and
    country, and the list of selectable exit countries.
    """
    direct_ip = get_direct_ip()
    info = {
        "vpn_enabled": settings.VPN_ENABLED,
        "token_present": _has_token(),
        "direct_ip": direct_ip,
        "vpn_ip": None,
        "proxy_country": None,
        "server_host": None,
        "available_countries": AVAILABLE_PROXY_COUNTRIES,
        "protected": False,
    }

    if settings.VPN_ENABLED and _has_token():
        upstream = get_socks5_upstream()
        if upstream:
            host, _port, _user, _pass = upstream
            info["proxy_country"] = resolve_proxy_country()
            info["server_host"] = host
            proxies = get_proxies()
            vpn_ip = get_exit_ip(proxies) if proxies else None
            info["vpn_ip"] = vpn_ip
            info["protected"] = bool(vpn_ip and vpn_ip != direct_ip)

    return info


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
                "mode": "socks5",
                "proxy_country": resolve_proxy_country(),
            }
        elif resp.status_code == 401:
            return {
                "connected": False,
                "error": "Token ungueltig oder abgelaufen",
                "token_valid": False,
            }
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

    # Get best server for the country (informational)
    servers = get_recommended_servers(country, 1)
    server_name = None
    if "servers" in servers and servers["servers"]:
        server_name = servers["servers"][0].get("name")

    # Establish + verify the real SOCKS5 tunnel used for scraping.
    proxy_country = resolve_proxy_country()
    proxies = get_proxies(proxy_country)
    exit_ip = get_exit_ip(proxies) if proxies else None
    if not exit_ip:
        return {
            "connected": False,
            "error": "SOCKS5-Proxy konnte nicht aufgebaut/verifiziert werden",
            "proxy_country": proxy_country,
        }

    # Log the connection with the verified exit IP
    db.add(VPNLog(
        action="connect", country=proxy_country,
        ip_address=exit_ip, success=True,
    ))
    db.commit()

    log.info("vpn_connected", proxy_country=proxy_country, exit_ip=exit_ip)

    return {
        "connected": True,
        "country": country,
        "ip": exit_ip,
        "server": server_name,
        "proxy_country": proxy_country,
        "mode": "socks5",
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
