"""ORM models for normalized image entities."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ship_id = Column(Integer, ForeignKey("ships.id"), index=True)
    file_path = Column(Text, nullable=False)
    file_name = Column(Text)
    source_url = Column(Text)
    source_name = Column(Text)
    hash_sha256 = Column(Text, index=True)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    mime_type = Column(Text)
    quality_score = Column(Float)
    is_synthetic = Column(Integer, default=0)
    split_type = Column(Text)  # train, val, test
    label_status = Column(Text)  # unlabeled, labeled, reviewed
    review_status = Column(Text)  # pending, approved, rejected
    # Detection / crop fields
    parent_image_id = Column(Integer, ForeignKey("images.id"), index=True, nullable=True)
    is_primary_crop = Column(Integer, default=0)  # 1 = largest ship crop
    crop_rank = Column(Integer, nullable=True)  # 1 = largest, 2 = second, etc.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    ship = relationship("Ship", back_populates="images")
    parent_image = relationship("Image", remote_side="Image.id", backref="crops")
    annotations = relationship(
        "ImageAnnotation", back_populates="image", cascade="all, delete-orphan"
    )
    inference_logs = relationship("InferenceLog", back_populates="image")


class ImageAnnotation(Base):
    __tablename__ = "image_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    annotation_type = Column(Text)
    bbox_json = Column(Text)
    segmentation_json = Column(Text)
    confidence = Column(Float)
    reviewer = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    image = relationship("Image", back_populates="annotations")
