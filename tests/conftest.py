"""Root conftest.py — shared fixtures for all tests.

Key responsibilities:
1. Point APP_DB_PATH to :memory: *before* any api.store / api.db import
   so tests never touch data/app.db.
2. Provide SQLAlchemy in-memory session for legacy db-dependent tests.
3. Provide a 'client' fixture wiring both DB overrides.
"""

import os

# --- set APP_DB_PATH before any api.store import ----------------------------
# Must happen at module level (before any test collection imports api.store).
os.environ.setdefault("APP_DB_PATH", ":memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from db import Base
from api.routers.eval import get_db as eval_get_db
from api.routers.skills import get_db as skills_get_db

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override both eval and skills get_db
    app.dependency_overrides[eval_get_db] = override_get_db
    app.dependency_overrides[skills_get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
