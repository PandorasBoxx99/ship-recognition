"""ORM model for augmentation logs."""

from sqlalchemy import Column, DateTime, Integer, Text, func

from backend.database import Base


class AugmentationLog(Base):
    __tablename__ = "augmentation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_dir = Column(Text, nullable=False)
    output_dir = Column(Text)
    num_source_images = Column(Integer)
    num_generated = Column(Integer)
    transforms_config = Column(Text)  # JSON
    created_at = Column(DateTime, server_default=func.now())
