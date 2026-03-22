"""Pydantic schemas for augmentation endpoints."""

from typing import Any

from pydantic import BaseModel


class AugmentRequest(BaseModel):
    source_dir: str
    num_per_image: int = 5
    transforms: dict[str, Any] | None = None
