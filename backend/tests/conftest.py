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


@pytest.fixture(scope="session")
def pg_engine():
    """Vrai PostgreSQL/PostGIS, schéma jetable migré par Alembic ; ignoré sans TEST_DATABASE_URL."""
    import os
    import uuid

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from app.database import get_engine

    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("TEST_DATABASE_URL not set; PostgreSQL check not executed")
    url = make_url(raw).set(drivername="postgresql+psycopg")
    schema = "test_" + uuid.uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = url.update_query_dict({"options": f"-csearch_path={schema},public"})
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = scoped.render_as_string(hide_password=False)
    get_engine.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(scoped, hide_parameters=True)
    yield engine
    engine.dispose()
    get_engine().dispose()
    get_engine.cache_clear()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.fixture
def pg_db(pg_engine):
    from sqlalchemy import text

    tables = [t.name for t in Base.metadata.sorted_tables if t.name != "cares"]
    with pg_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE " + ", ".join(f'"{name}"' for name in tables) + " CASCADE")
        )
    with Session(pg_engine) as session:
        yield session


@pytest.fixture
def pg_client(pg_engine, pg_db, counts):
    def session():
        with Session(pg_engine) as s:
            yield s

    def counter(key, window):
        counts[key] = counts.get(key, 0) + 1
        return counts[key]

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_counter] = lambda: counter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def published(request, monkeypatch):
    """Capture les événements temps réel ; les tests `realtime` utilisent le vrai Redis."""
    events = []
    if request.node.get_closest_marker("realtime") is None:
        monkeypatch.setattr(
            "app.realtime.publish",
            lambda user_ids, event: events.append((set(user_ids), event)),
        )
    return events
