"""ORM models for scrape sources and jobs (normalized)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class ScrapeSource(Base):
    __tablename__ = "scrape_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    base_url = Column(Text)
    source_type = Column(Text)  # html, api, rss
    parser_config_json = Column(Text)
    rate_limit = Column(Integer)
    retry_limit = Column(Integer)
    is_active = Column(Integer, default=1)
    requires_vpn = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    scrape_jobs = relationship("ScrapeJob", back_populates="source")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("scrape_sources.id"), index=True)
    status = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    items_saved = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_log = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    source = relationship("ScrapeSource", back_populates="scrape_jobs")
