"""SQLAlchemy ORM models — import all to ensure they are registered with Base."""

# Legacy v1 tables (kept for backward compatibility)
from backend.models.augmentation import AugmentationLog
from backend.models.category import Category
from backend.models.classification import Classification
from backend.models.image import Image, ImageAnnotation
from backend.models.item import Item
from backend.models.job import Job
from backend.models.ml import InferenceLog, MLModel, SyntheticJob, TrainingRun
from backend.models.scrape import ScrapeJob, ScrapeSource
from backend.models.settings import PredefinedURL

# Normalized v2 tables
from backend.models.ship import Ship, ShipAlias

__all__ = [
    # v1
    "Job", "Item", "Category", "PredefinedURL",
    "Classification", "AugmentationLog",
    # v2
    "Ship", "ShipAlias", "Image", "ImageAnnotation",
    "ScrapeSource", "ScrapeJob",
    "MLModel", "TrainingRun", "InferenceLog", "SyntheticJob",
]
