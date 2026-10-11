"""Infirmo health checks and explicitly enabled synthetic T9 demonstration."""

import os

import psycopg
import redis
from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import router as api_v1
from app.demo import router
from app.errors import ApiError, api_error_handler

app = FastAPI(title="infirmo-backend", version="0.1.0")
app.include_router(router)
app.include_router(api_v1)
app.add_exception_handler(ApiError, api_error_handler)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Service unavailable"})


@app.middleware("http")
async def private_api_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# /metrics (INF-15) : compteurs/latences par route uniquement (métriques
# Prometheus par défaut de l'instrumentator). AUCUNE donnée de santé ni
# secret n'y transite : pas de corps de requête/réponse, pas de payload
# métier — seulement méthode, chemin de la route, code de statut, durée
# Ne jamais inclure de corps ni de jeton dans les métriques.
Instrumentator().instrument(app).expose(app)

# Timeouts courts : un /health/ready doit répondre vite, y compris quand une
# dépendance est injoignable (pas de docker, tests unitaires, etc.).
_DB_CONNECT_TIMEOUT_SECONDS = 2
_REDIS_CONNECT_TIMEOUT_SECONDS = 2


@app.get("/health")
def health() -> dict:
    """Liveness probe : ne vérifie aucune dépendance externe."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(response: Response) -> dict:
    """Readiness probe : vérifie PostgreSQL et Redis.

    Ne jamais logger le contenu des exceptions ici : elles peuvent contenir
    des fragments de DSN (host, credentials). On ne renvoie qu'un booléen.
    """
    postgres_ok = _check_postgres()
    redis_ok = _check_redis()

    if not (postgres_ok and redis_ok):
        response.status_code = 503

    return {
        "status": "ready" if postgres_ok and redis_ok else "not-ready",
        "postgres": postgres_ok,
        "redis": redis_ok,
    }


def _check_postgres() -> bool:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return False
    try:
        with psycopg.connect(
            database_url, connect_timeout=_DB_CONNECT_TIMEOUT_SECONDS
        ) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


def _check_redis() -> bool:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return False
    try:
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=_REDIS_CONNECT_TIMEOUT_SECONDS,
        )
        return bool(client.ping())
    except redis.RedisError:
        return False
