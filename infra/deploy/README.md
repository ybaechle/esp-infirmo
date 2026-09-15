# Deployment and rollback

These workflows are configuration, not evidence that staging or production exists. Only synthetic data is authorized for the current demonstration. See [hosting requirements](../hds/README.md).

## Server prerequisites

A Linux server needs Docker with Compose v2 (`--wait` and multiple `--env-file` supported), a dedicated SSH account, outbound GHCR access, and a domain pointing to the server for Caddy TLS. Authenticate the server to private GHCR using a read-only package credential. The server directory is `~/infirmo`.

Copy `.env.staging.example` to `~/infirmo/.env` on the server and configure the database password, domain and all three initial image references. Do not use `develop` or `latest` images. For the synthetic demonstration only, set `INFIRMO_DEMO_MODE=true` and set a unique `INFIRMO_DEMO_PASSWORD`. Otherwise leave demo mode false. No demo identity is seeded when disabled.

Configure GitHub environments `staging` and `production`. Production should require a human reviewer. Configure each environment's secrets:

| Staging | Production | Value |
| --- | --- | --- |
| STAGING_SSH_HOST | PROD_SSH_HOST | Server address |
| STAGING_SSH_USER | PROD_SSH_USER | Dedicated user |
| STAGING_SSH_KEY | PROD_SSH_KEY | Private deployment key |
| STAGING_SSH_KNOWN_HOSTS | PROD_SSH_KNOWN_HOSTS | Host key verified with the server operator |

Do not derive trust by scanning the host during deployment. A missing secret fails the deployment visibly. No workflow provisions a paid server.

## Staging

`Deploy Staging` follows a successful `Quality` push run on `develop` and checks out that exact tested commit. It builds backend, IA and mobile images tagged with the full commit SHA. It copies the same revision's Compose, Caddyfile and `deploy.sh` to the server before deploying.

`deploy.sh` records image selections in the server's `.images.env`, invokes Compose with both `.env` and `.images.env`, waits up to 180 seconds for healthy containers, checks actual PostgreSQL/Redis readiness, and reloads Caddy. The image file records the requested selection even if readiness fails; a failed attempt must be recorded and explicitly rolled back. A green container readiness check is not third-party functional acceptance.

Staging also copies the acceptance script from the tested revision and runs it after readiness inside the backend container, using its synthetic demo credentials against `http://mobile`. This verifies the deployed reverse proxy, login, persistence and logout; a failed check fails the workflow. Staging therefore requires `INFIRMO_DEMO_MODE=true` and a configured synthetic password. Production does not run this demo acceptance.

For independent public TLS validation, run `python infra/check_v01.py --url https://your-domain` with the synthetic credentials supplied through `INFIRMO_DEMO_EMAIL` and `INFIRMO_DEMO_PASSWORD`. Record the tester, commit, duration and result in `/reporting/`. Never print credentials in reports.

## Production handoff

`Release` runs the quality suite before semantic-release. Each newly created module tag explicitly dispatches `Deploy Production` with `build=true`; this works with `GITHUB_TOKEN`, whose tag pushes do not trigger another push workflow. The production job validates module/version, checks out the exact release tag, builds that module's versioned image, synchronizes release configuration and persists its selected image in `.images.env`.

Module release tags identify the whole repository revision used for deployment configuration. They are not proof that the complete academic increment has been accepted. Avoid concurrent manual changes to the server files.

## Rollback

Use Actions → Deploy Production → Run workflow, choose the module and a previously validated version, and leave `build=false`. The image must already exist in GHCR. All other module image selections remain persisted in `.images.env`; a later Compose invocation retains them when using the same env files.

A rollback changes application images and revision configuration. It does not automatically reverse database migrations. Review schema compatibility and take a validated backup before any destructive migration. Do not select an older tag that lacks the deployment script/configuration introduced with v0.1.

Manual inspection on the server:

```sh
cd ~/infirmo
docker compose --env-file .env --env-file .images.env -f docker-compose.staging.yml ps
curl --fail https://your-domain/health/ready
```

No production deployment, paid provisioning, or remote configuration is performed by merely adding these files.
