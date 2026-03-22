"""Pydantic schemas for classification endpoints."""

from typing import Any

from pydantic import BaseModel


class Prediction(BaseModel):
    label: str
    confidence: float


class ClassifyResponse(BaseModel):
    predictions: list[Prediction]
    image_path: str
    filename: str


class ClassifyShipResponse(BaseModel):
    ship_id: int
    predictions: list[Prediction]


class ClassificationRecord(BaseModel):
    id: int
    item_id: int | None = None
    image_path: str | None = None
    predicted_type: str
    confidence: float
    all_predictions: Any = None
    model_name: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class ClassificationListResponse(BaseModel):
    classifications: list[ClassificationRecord]
    total: int
    page: int
    pages: int
