"""ORM model for predefined URLs and settings."""

from sqlalchemy import Column, DateTime, Integer, Text, func

from backend.database import Base


class PredefinedURL(Base):
    __tablename__ = "predefined_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False, unique=True)
    name = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
