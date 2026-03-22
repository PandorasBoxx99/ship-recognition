"""ORM model for scraping jobs."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    name = Column(Text)
    status = Column(String, default="pending")
    total_items = Column(Integer, default=0)
    downloaded = Column(Integer, default=0)
    limit_count = Column(Integer)
    delay_min = Column(Float, default=1.0)
    delay_max = Column(Float, default=5.0)
    vpn_required = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    items = relationship("Item", back_populates="job", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="job", cascade="all, delete-orphan")
