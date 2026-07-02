# infirmo-backend — image Docker du scaffold DevOps (INF-8).
# À faire évoluer par l'équipe backend au fur et à mesure de l'app réelle.

FROM python:3.12-slim

# uv, épinglé à une version précise et copié depuis l'image officielle Astral
# (pas de "curl | sh") — chaîne d'approvisionnement traitée comme non fiable.
COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dépendances d'abord pour profiter du cache Docker : pyproject.toml/uv.lock
# changent moins souvent que le code applicatif.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app

# Utilisateur non-root.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
