"""infirmo-ia — scaffold DevOps (INF-8).

Squelette FastAPI exposant uniquement /health, SANS aucune dépendance
Whisper/ML. Sert à valider l'orchestration Docker Compose locale (réseau
interne, healthcheck) avant que l'équipe IA (Pierre-Arthur) n'implémente le
microservice de transcription réel.

Rappel compliance (AGENTS.md, project-architecture) : ce service ne doit
jamais être exposé publiquement. Il n'est appelé que par backend/, sur le
réseau Docker interne — voir docker-compose.yml (réseau "internal").
"""

from fastapi import FastAPI

app = FastAPI(title="infirmo-ia", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Liveness probe : ne vérifie aucune dépendance externe."""
    return {"status": "ok"}
