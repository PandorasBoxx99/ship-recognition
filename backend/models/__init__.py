"""SQLAlchemy ORM models — import all to ensure they are registered with Base."""

# Legacy v1 tables (kept for backward compatibility)
from backend.models.augmentation import AugmentationLog
from backend.models.category import Category
from backend.models.classification import Classification
from backend.models.item import Item
from backend.models.job import Job
from backend.models.settings import PredefinedURL
from backend.models.vpn import VPNLog

# Normalized v2 tables
from backend.models.ship import Ship, ShipAlias
from backend.models.image import Image, ImageAnnotation
from backend.models.scrape import ScrapeSource, ScrapeJob
from backend.models.ml import MLModel, TrainingRun, InferenceLog, SyntheticJob

__all__ = [
    # v1
    "Job", "Item", "Category", "VPNLog", "PredefinedURL",
    "Classification", "AugmentationLog",
    # v2
    "Ship", "ShipAlias", "Image", "ImageAnnotation",
    "ScrapeSource", "ScrapeJob",
    "MLModel", "TrainingRun", "InferenceLog", "SyntheticJob",
]
