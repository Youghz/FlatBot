"""Shared test fixtures."""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from flat_research.db import Base


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing. Created fresh per test.

    Uses StaticPool so all connections share the same in-memory database,
    and check_same_thread=False so FastAPI's thread pool can access it.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()
