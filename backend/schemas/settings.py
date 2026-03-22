"""Pydantic schemas for settings/URL endpoints."""

from pydantic import BaseModel


class URLCreateRequest(BaseModel):
    url: str
    name: str = ""


class URLResponse(BaseModel):
    id: int
    url: str
    name: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}
