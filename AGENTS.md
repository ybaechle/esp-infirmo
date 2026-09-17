# INFIRMO project instructions

## Scope and ownership

INFIRMO is a French-facing Flutter application for independent nurses. The source scope is `docs/livrables/INFIRMO_Cahier_des_Charges_v4.pdf`; the current executable boundary is in `README.md` and `reporting/sprint-1.md`.

| Owner | Responsibility |
| --- | --- |
| Tetiana Lombardi | Product, Figma, backlog, reporting |
| Maxence Noizet | Flutter mobile |
| Yohan Baechlé | Fullstack integration |
| Lothaire Nobili | Backend |
| Ziad Tiarimti | Backend |
| Pierre-Arthur Toutouom Yountebo | IA |
| Lazaro Marrero Rousse | Infrastructure and CI/CD |

## Architecture

- `mobile/` calls only the backend over HTTP/WebSocket. No direct database, Redis or IA access.
- `backend/` owns the database, authorization and business logic. Use SQLAlchemy and versioned Alembic migrations; never manually edit deployed tables.
- `ia/` is private to the backend. Whisper and transcription are outside the initial profile increment.
- `infra/` owns Compose, deployment, backup and operational tooling. Reuse Docker Compose; add Terraform/Kubernetes only for an established need.
- Modules are released independently as `<module>-vX.Y.Z`. The academic v0.1 identifies the tested source commit and module versions; it does not introduce a global release scheme.
- Read relevant ADRs before changing a structural decision. Prefer the standard library or an existing dependency. Pin/lock new dependencies in the owning module.

## Data and security

- Development, tests, demonstrations and non-HDS staging use synthetic data only. Never use real nurse/patient records, voices or screenshots.
- Real health-data processing requires an approved EU HDS environment, processor contracts and the project's security/compliance validation. The synthetic demonstration does not satisfy those deployment gates.
- Enforce authorization in the backend. Minimize fields and use pseudonymous identifiers. Never log request/response bodies, professional transmissions, passwords or tokens.
- Real health data requires TLS in transit and encryption at rest, including backups. Explicitly local synthetic loopback demonstrations must remain documented as such.
- Keep secrets outside Git. Commit examples only. `.env`, overrides, credentials and generated build artifacts are not deliverables.
- Do not introduce external analytics, email, push, transcription or storage processors without reviewing data residency and the applicable processor agreement first. An in-process open-source library is not itself an external processor.
- Use secure session handling, expiry, revocation, bounded inputs and useful error handling. Store no persistent plaintext credentials on the device.

## Workflow and evidence

- Read `CONTRIBUTING.md` and existing lessons before implementation. Work on `feature/*`, `bugfix/*`, `docs/*`, `ci/*`, `test/*` or `refactor/*`; review by PR into `develop`.
- Use Conventional Commits and the user's existing Git identity. Preserve human authorship. Do not add automated-tool authors, co-author trailers, session links or generated-by signatures to commits, PRs or contribution records. Do not invent balanced contributions or attribute work to absent team members.
- The Definition of Done in `CONTRIBUTING.md` is authoritative. Missing CI capacity, a skipped deployment or an unperformed independent test cannot be marked successful.
- Record observed procedural friction in `reporting/delta-log.csv`, fix its source procedure, and rerun from a clean baseline. Keep failures after correction.
- Update actual hours and freshly estimated remaining work from the responsible person's observations. Unknown means blank, not zero. Do not use tool runtime as human effort.
- Run relevant tests/lint/build checks; report their actual outputs and limits. Do not weaken checks to obtain green status.
- Preserve local work. Before rewriting history or destructive operations, inspect exact targets, retain a recoverable backup and verify the outcome. Never force-push without explicit user authorization.

## graphify

When the user types `/graphify`, read the installed graphify skill (`~/.Codex/skills/graphify/SKILL.md`, or its installed equivalent) before doing anything else.
