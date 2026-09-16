"""Run against a disposable PostgreSQL database; each run owns a temporary schema."""

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import get_engine
from app.main import app
from app.seed_demo import seed_demo


@pytest.mark.postgres
@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set; real PostgreSQL check not executed",
)
def test_migrations_and_persisted_journey(monkeypatch):
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(drivername="postgresql+psycopg")
    schema = "test_" + uuid.uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", scoped_url.render_as_string(hide_password=False))
    monkeypatch.setenv("INFIRMO_DEMO_MODE", "true")
    get_engine.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        command.upgrade(Config("alembic.ini"), "head")
        with Session(get_engine()) as db:
            seed_demo(db)
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "demo@infirmo.example",
                    "password": "Infirmo-demo-2026!",
                },
            )
            assert response.status_code == 200
            auth = {"Authorization": "Bearer " + response.json()["access_token"]}
            profile = {
                "display_name": "Postgres Démo",
                "role": "titulaire",
                "city": "Nancy",
            }
            assert (
                client.put("/api/profile", headers=auth, json=profile).json() == profile
            )
        get_engine().dispose()
        get_engine.cache_clear()
        with TestClient(app) as client:
            assert client.get("/api/profile", headers=auth).json() == profile
            assert client.post("/api/auth/logout", headers=auth).status_code == 204
            assert client.get("/api/profile", headers=auth).status_code == 401
        command.downgrade(Config("alembic.ini"), "base")
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        get_engine().dispose()
        get_engine.cache_clear()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
