"""Pydantic schemas for stats endpoint."""

from pydantic import BaseModel


class TypeDistribution(BaseModel):
    type: str
    count: int


class StatsResponse(BaseModel):
    total_jobs: int
    total_items: int
    downloaded: int
    pending: int
    failed: int
    classifications: int
    type_distribution: list[TypeDistribution]
