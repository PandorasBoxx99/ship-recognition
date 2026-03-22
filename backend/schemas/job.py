"""Pydantic schemas for job/scraping endpoints."""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    url: str


class JobCreateRequest(BaseModel):
    url: str
    name: str | None = None
    limit: int = 100
    delay_min: float = 1.0
    delay_max: float = 5.0
    vpn_required: bool = True


class JobResponse(BaseModel):
    """Matches dict(sqlite3.Row) for a job — all fields optional to handle partial data."""

    id: int
    url: str
    name: str | None = None
    status: str = "pending"
    total_items: int = 0
    downloaded: int = 0
    limit_count: int | None = None
    delay_min: float = 1.0
    delay_max: float = 5.0
    vpn_required: bool | int = True
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
