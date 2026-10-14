import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.ratelimit import get_counter


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def counts():
    return {}


@pytest.fixture
def client(db_engine, counts):
    def counter(key, window):
        counts[key] = counts.get(key, 0) + 1
        return counts[key]

    def session():
        with Session(db_engine) as s:
            yield s

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_counter] = lambda: counter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def encryption_keys(monkeypatch):
    import base64

    key = base64.b64encode(b"k" * 32).decode()
    monkeypatch.setenv("INFIRMO_ENCRYPTION_KEYS", f"test:{key}")
    return key
