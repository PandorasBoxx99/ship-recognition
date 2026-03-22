"""Pydantic schemas for ship/item endpoints."""

from typing import Any

from pydantic import BaseModel


class ShipResponse(BaseModel):
    """Matches dict(sqlite3.Row) for items joined with jobs."""

    id: int
    job_id: int
    source_url: str
    image_url: str | None = None
    local_path: str | None = None
    ship_name: str | None = None
    ship_type: str | None = None
    imo_number: str | None = None
    mmsi: str | None = None
    metadata: Any = None
    status: str = "pending"
    created_at: str | None = None
    downloaded_at: str | None = None
    error_message: str | None = None
    job_name: str | None = None
    job_url: str | None = None

    model_config = {"from_attributes": True}


class ShipListResponse(BaseModel):
    ships: list[ShipResponse]
    types: list[str]
    total: int
    page: int
    per_page: int
    pages: int


class TypeStat(BaseModel):
    type: str
    count: int
    sources: int = 0


class ShipStatsResponse(BaseModel):
    total_downloaded: int
    total_classified: int
    by_type: list[TypeStat]
