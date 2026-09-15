# T9 v0.1 implementation plan

Date: 2026-09-15. Scope: the BUILD v4.1.1 brief and the approved sign-in/profile demonstration.

## Deliverable

A synthetic user signs in to the Flutter app, edits a professional profile, saves it in PostgreSQL, signs out, and signs in again to retrieve it. This is a limited executable increment, not completion of authentication, professional verification, matching or transcription.

## Work and verification

- [ ] Backend: SQLAlchemy models, Alembic migration, explicitly enabled synthetic seed, expiring and revocable bearer sessions, validated profile ownership; pytest with coverage and PostgreSQL acceptance.
- [ ] Mobile: French Flutter sign-in/profile screens, memory-only session, input/error/loading states; widget/client tests, analysis and web build.
- [ ] Infrastructure: documented Docker startup, same-origin web/API routing, migrations, real acceptance checks, honest CI/deployment gates, backup/rollback corrections.
- [ ] Governance: authoritative DoD, issue/PR evidence fields, populated ADRs, baseline effort, Delta Log, reproducible dashboard and cold-start procedure.
- [ ] Verification: isolated Compose project, actual login/profile persistence, clean rebuild/restart, local quality reports, whole-change review.
- [ ] Repository hygiene: preserve project rules in neutral guidance, remove vendor-specific tooling/history credits as requested, preserve human authors, back up refs before rewrite and verify every rewritten ref.

## Integration contract

`POST /api/auth/login` accepts `email,password` and returns `access_token,token_type`.
Authenticated `GET /api/profile` and `PUT /api/profile` use `display_name,role,city` (role: `titulaire` or `remplacant`). `POST /api/auth/logout` revokes the bearer token. PostgreSQL owns persistence; Redis limits login attempts. The demo is disabled unless `INFIRMO_DEMO_MODE=true`.

## Constraints and rulings

- Synthetic data only; no real professionals, patients or audio. No external data processor is introduced by the in-process SQLAlchemy/Alembic and HTTP client libraries.
- Existing source scope/ownership is retained. AI transcription and full professional authentication stay in the original roadmap.
- Unknown human hours, meeting outcomes, independent onboarding and remote deployment remain explicitly unverified. Tool execution time is not assigned to team members.
- User authorized implementation and history cleanup. Work is isolated on `feature/t9-executable-reporting`; no implementation merge into `develop` without review.
- Backend and mobile share only the API contract. Infra consumes Dockerfiles and the seed/migration commands. Reporting consumes execution evidence, not inferred completion.
- Existing local scaffold tests passed before implementation. Docker was stopped; starting Docker Desktop restored the engine without restarting an existing workload.

## External completion gates

The current repository account has `push` permission but not repository administration. An organization administrator must enable Actions capacity and apply the versioned branch rules. An independent peer must execute the documented cold start. The team must supply actual effort and conduct the retrospective. These cannot be truthfully replaced by generated records.
