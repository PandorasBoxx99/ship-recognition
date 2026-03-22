"""ORM model for website categories."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    item_count = Column(Integer, default=0)
    selected = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    job = relationship("Job", back_populates="categories")
