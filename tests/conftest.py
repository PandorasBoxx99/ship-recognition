"""Shared test fixtures for the Ship Recognition test suite."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for testing."""
    from backend.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Create a fresh database session for each test."""
    from backend.database import Base

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
