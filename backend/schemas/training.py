"""Pydantic schemas for training endpoints."""

from pydantic import BaseModel


class TrainingStartRequest(BaseModel):
    dataset_dir: str
    epochs: int = 5
    batch_size: int = 8
    learning_rate: float = 5e-5
