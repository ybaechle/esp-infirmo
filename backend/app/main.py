"""infirmo-backend — scaffold DevOps (INF-8).

Application FastAPI minimale exposant uniquement des health checks pour
valider l'orchestration Docker Compose locale (INF-8). Ce fichier N'EST PAS
l'application backend finale : il sera remplacé par l'équipe backend
(Louis/Ziad) quand leurs tickets applicatifs démarreront.

Configuration 12-factor : tout vient des variables d'environnement, aucun
secret ni valeur par défaut sensible n'est codé en dur ici.
"""

import os

import psycopg
import redis
from fastapi import FastAPI, Response

app = FastAPI(title="infirmo-backend", version="0.1.0")

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
