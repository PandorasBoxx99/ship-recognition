"""Common Pydantic schemas used across the API."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str


class StatusResponse(BaseModel):
    status: str
