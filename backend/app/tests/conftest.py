"""Isolated service/API tests; never use the developer database or release directory."""

from unittest.mock import Mock
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.config import get_settings
import app.models.models
import app.models.releases
from app.main import app


@compiles(UUID, "sqlite")
def sqlite_uuid(element, compiler, **kw):
    return "CHAR(32)"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(conn, record):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def settings(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "test-maintainer-token")
    monkeypatch.setattr(settings, "SESSION_SECRET", "test-session-secret-" * 3)
    monkeypatch.setattr(settings, "RELEASE_ROOT", tmp_path)
    monkeypatch.setattr(settings, "ENABLE_DEMO_DATA", False)
    return settings


@pytest.fixture
def client(db, settings, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr("app.api.releases.dispatch", Mock())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin(client):
    client.headers["Authorization"] = "Bearer test-maintainer-token"
    return client
