"""VPN service — wraps NordVPN CLI calls."""

import subprocess
import time

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.vpn import VPNLog


def get_vpn_status() -> dict:
    """Check NordVPN connection status."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    try:
        result = subprocess.run(
            [settings.VPN_BINARY, "status"],
            capture_output=True,
            text=True,
            timeout=10,
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
    """Connect to VPN and log the action."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    try:
        subprocess.run(
            [settings.VPN_BINARY, "connect", country],
            capture_output=True,
            timeout=30,
        )
        time.sleep(3)
        status = get_vpn_status()

        db.add(
            VPNLog(
                action="connect",
                country=country,
                ip_address=status.get("ip"),
                success=status.get("connected", False),
            )
        )
        db.commit()

        return status
    except Exception as e:
        return {"connected": False, "error": str(e)}


def disconnect_vpn(db: Session) -> dict:
    """Disconnect from VPN and log the action."""
    if not settings.VPN_ENABLED:
        return {"connected": False, "error": "VPN disabled in config"}

    try:
        subprocess.run(
            [settings.VPN_BINARY, "disconnect"],
            capture_output=True,
            timeout=10,
        )
        db.add(VPNLog(action="disconnect", success=True))
        db.commit()
        return {"connected": False}
    except Exception as e:
        return {"error": str(e)}


def rotate_vpn(db: Session) -> dict:
    """Rotate VPN IP (disconnect + reconnect)."""
    disconnect_vpn(db)
    time.sleep(2)
    return connect_vpn("Germany", db)


def test_token(token: str | None = None) -> dict:
    """Test if a NordVPN access token is valid by attempting login.

    If no token is provided, uses the one from settings.
    Returns success/error status.
    """
    api_key = token or settings.VPN_API_KEY
    if not api_key:
        return {"valid": False, "error": "Kein Access Token konfiguriert"}

    try:
        # First check if nordvpn CLI is available
        result = subprocess.run(
            [settings.VPN_BINARY, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {"valid": False, "error": f"NordVPN CLI nicht gefunden ({settings.VPN_BINARY})"}

        # Try to login with the token
        result = subprocess.run(
            [settings.VPN_BINARY, "login", "--token", api_key],
            capture_output=True, text=True, timeout=30,
        )
        output = (result.stdout + " " + result.stderr).strip()

        # Check for success indicators
        if result.returncode == 0 or "already logged in" in output.lower() or "welcome" in output.lower():
            # After login, check account status
            account_result = subprocess.run(
                [settings.VPN_BINARY, "account"],
                capture_output=True, text=True, timeout=10,
            )
            account_info = account_result.stdout.strip()

            return {
                "valid": True,
                "message": "Token gueltig — eingeloggt",
                "account": account_info,
            }
        else:
            return {
                "valid": False,
                "error": f"Login fehlgeschlagen: {output}",
            }

    except FileNotFoundError:
        return {"valid": False, "error": f"NordVPN CLI nicht installiert ({settings.VPN_BINARY})"}
    except subprocess.TimeoutExpired:
        return {"valid": False, "error": "Timeout — NordVPN antwortet nicht"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
