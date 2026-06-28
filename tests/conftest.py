"""Shared test fixtures for the Ship Recognition test suite."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, get_db
from backend.models import (
    Classification,
    Item,
    Job,
    PredefinedURL,
)


@pytest.fixture(scope="session")
def test_engine():
    """In-memory SQLite engine shared across all tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Fresh database session for each test — rolls back after test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def seeded_db(db_session):
    """Database session pre-populated with sample data."""
    # Predefined URLs
    for url, name in [
        ("https://www.shipspotting.com/", "ShipSpotting"),
        ("https://www.vesselfinder.com/", "VesselFinder"),
    ]:
        db_session.add(PredefinedURL(url=url, name=name))

    # Job with items
    job = Job(
        url="https://example.com/ships",
        name="Test Job",
        status="completed",
        total_items=3,
        downloaded=2,
        limit_count=100,
        delay_min=1.0,
        delay_max=3.0,
        vpn_required=False,
    )
    db_session.add(job)
    db_session.flush()

    items = [
        Item(
            job_id=job.id,
            source_url="https://example.com/ships/1",
            image_url="https://example.com/img1.jpg",
            local_path="/tmp/test/1.jpg",
            ship_name="Test Ship Alpha",
            ship_type="Container Ship",
            status="downloaded",
        ),
        Item(
            job_id=job.id,
            source_url="https://example.com/ships/2",
            image_url="https://example.com/img2.jpg",
            local_path="/tmp/test/2.jpg",
            ship_name="Test Ship Beta",
            ship_type="Tanker",
            status="downloaded",
        ),
        Item(
            job_id=job.id,
            source_url="https://example.com/ships/3",
            image_url="https://example.com/img3.jpg",
            ship_name="Pending Ship",
            status="pending",
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.flush()

    # Classification
    db_session.add(
        Classification(
            item_id=items[0].id,
            image_path="/tmp/test/1.jpg",
            predicted_type="Container Ship",
            confidence=0.92,
            all_predictions='[{"label":"Container Ship","confidence":0.92}]',
        )
    )

    db_session.commit()
    return db_session


@pytest.fixture
def mock_vpn():
    """Mock the NordVPN REST API so VPN calls return a connected status."""
    with patch("backend.services.vpn_service.requests.get") as mock_get:
        credentials = MagicMock()
        credentials.status_code = 200
        credentials.json.return_value = {"username": "test-user"}

        servers = MagicMock()
        servers.status_code = 200
        servers.json.return_value = [{"name": "de1024", "station": "1.2.3.4"}]

        # Each VPN operation issues a credentials check followed by a server lookup.
        mock_get.side_effect = [credentials, servers] * 8
        yield mock_get


@pytest.fixture
def mock_ml():
    """Mock ML engine to avoid loading the actual model."""
    mock_predictions = [
        {"label": "Container Ship", "confidence": 0.87},
        {"label": "Tanker", "confidence": 0.08},
        {"label": "Cruise", "confidence": 0.03},
    ]
    with patch("backend.services.ml_service.classify_image", return_value=mock_predictions) as m:
        yield m


@pytest.fixture
def client(seeded_db):
    """FastAPI TestClient with seeded database."""
    from backend.main import app

    def _override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
