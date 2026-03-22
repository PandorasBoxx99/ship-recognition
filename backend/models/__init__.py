"""SQLAlchemy ORM models — import all to ensure they are registered with Base."""

from backend.models.augmentation import AugmentationLog
from backend.models.category import Category
from backend.models.classification import Classification
from backend.models.item import Item
from backend.models.job import Job
from backend.models.settings import PredefinedURL
from backend.models.vpn import VPNLog

__all__ = [
    "Job",
    "Item",
    "Category",
    "VPNLog",
    "PredefinedURL",
    "Classification",
    "AugmentationLog",
]
