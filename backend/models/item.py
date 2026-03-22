"""ORM model for downloaded items (ships/images)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    image_url = Column(Text)
    local_path = Column(Text)
    ship_name = Column(Text)
    ship_type = Column(Text)
    imo_number = Column(Text)
    mmsi = Column(Text)
    metadata_ = Column("metadata", Text)  # JSON blob; renamed to avoid SQLAlchemy reserved attr
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, server_default=func.now())
    downloaded_at = Column(DateTime)
    error_message = Column(Text)

    job = relationship("Job", back_populates="items")
    classifications = relationship("Classification", back_populates="item")
