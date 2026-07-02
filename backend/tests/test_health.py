"""Tests des health checks du scaffold infirmo-backend (INF-8).

Ne nécessitent pas Docker : le test de /health/ready force des URLs de
dépendances injoignables (port fermé en local) pour vérifier le chemin 503
avec des timeouts courts.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Port local non écouté : la connexion est refusée immédiatement (pas besoin
# d'attendre le timeout complet), ce qui garde le test rapide sans Docker.
_UNREACHABLE_POSTGRES_URL = "postgresql://user:pass@127.0.0.1:1/infirmo"
_UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1/0"


def test_health_is_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_503_when_dependencies_unreachable(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _UNREACHABLE_POSTGRES_URL)
    monkeypatch.setenv("REDIS_URL", _UNREACHABLE_REDIS_URL)

    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not-ready"
    assert body["postgres"] is False
    assert body["redis"] is False


def test_health_ready_returns_503_when_env_vars_missing(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["postgres"] is False
    assert body["redis"] is False


def test_metrics_exposes_prometheus_http_metrics() -> None:
    """INF-15 : /metrics doit exposer les métriques standard (comptages,
    latence) sans jamais contenir de donnée de santé (AGENTS.md §5.6)."""
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
