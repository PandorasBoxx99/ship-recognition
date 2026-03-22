"""Pydantic schemas for VPN endpoints."""

from pydantic import BaseModel


class VPNConnectRequest(BaseModel):
    country: str = "Germany"


class VPNStatusResponse(BaseModel):
    connected: bool
    country: str | None = None
    ip: str | None = None
    raw: str | None = None
    error: str | None = None
