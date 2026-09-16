# Infrastructure

Owner: Lazaro Marrero Rousse. Local and staging environments use synthetic data only.

## Local executable v0.1

Prerequisites: Git, Docker Engine/Desktop with Compose v2 supporting `--wait`, and
Python 3.12+ for the acceptance check. Start Docker before running these commands
from the repository root. Do not overwrite an existing `.env`.

```sh
cp .env.example .env
docker compose up -d --build --wait --wait-timeout 180
python infra/check_v01.py
```

Open http://localhost:8080. The public synthetic login is `demo@infirmo.example`
with password `Infirmo-demo-2026!`. Override with `INFIRMO_DEMO_EMAIL` and
`INFIRMO_DEMO_PASSWORD` in `.env`; pass the same environment variables to the
acceptance script if changed. The backend applies Alembic migrations and runs an
idempotent synthetic seed on startup. Saving a profile persists in PostgreSQL.
`docker compose down` stops the stack while retaining its database volume.

| Service | Purpose | Host access |
| --- | --- | --- |
| mobile | Flutter web and `/api` reverse proxy | localhost:8080 (`WEB_PORT`) |
| backend | Login, profile and readiness API | localhost:8000 (`BACKEND_PORT`) |
| db | PostgreSQL/PostGIS | Private |
| redis | Login throttle | Private |
| ia | Health-only scaffold; Whisper not implemented | Private network |
| prometheus / grafana | Optional `monitoring` profile | 9090 / 3001 |

Record any unexpected local adjustment in `/reporting/`, fix its source procedure,
and repeat from a clean environment. A successful local run does not constitute a
third-party cold-start validation. Do not put real health data in this demo.

## Quality and deployment

[Quality workflows](github/README.md) run all module checks and the Compose cold-start
on every PR and push to `develop`/`main`. The stable **Quality gate** requires all
four jobs to succeed. Backend/IA publish coverage and JUnit reports; mobile publishes
LCOV. No missing app/test directory is silently accepted.

[Staging and production runbook](deploy/README.md) documents SSH secrets, pinned
images, synchronized configuration, readiness and rollback. Missing deployment
configuration fails explicitly. No server provisioning or deployment is implied
by the existence of these workflows.

[Backup and restoration](backup/README.md) supports an explicit Compose and env file.
[Monitoring](monitoring/README.md) records technical counters, not personal data.
[Performance smoke test](perf/README.md) and [hosting constraints](hds/README.md)
remain separate from the sprint governance metrics in `/reporting/`.

Terraform and Kubernetes are not used. Module releases remain independent;
`infra/` follows the repository revision containing its deployment configuration.
