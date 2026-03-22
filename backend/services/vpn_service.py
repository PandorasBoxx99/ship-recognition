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
