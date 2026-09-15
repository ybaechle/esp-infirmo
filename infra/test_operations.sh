#!/usr/bin/env bash
# Isolated checks: every Docker call is replaced by a local stub.
set -euo pipefail
source_dir="$(cd "$(dirname "$0")" && pwd)"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/bin" "$work/project/infra/backup" "$work/deploy"
cp "$source_dir/backup/backup.sh" "$source_dir/backup/restore.sh" "$work/project/infra/backup/"
cp "$source_dir/deploy/deploy.sh" "$work/deploy/"
touch "$work/deploy/.env" "$work/project/.env"
export DOCKER_CALLS="$work/calls"
cat > "$work/bin/docker" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$DOCKER_CALLS"
case "$*" in
  *'printenv POSTGRES_USER'*) echo synthetic ;;
  *'printenv POSTGRES_DB'*) echo testdb ;;
  *'pg_dump '*)
    if [ "${FAIL_DUMP:-0}" = 1 ]; then exit 1; fi
    printf 'synthetic dump' ;;
  *'pg_restore '*) cat >/dev/null ;;
esac
STUB
chmod +x "$work/bin/docker"
export PATH="$work/bin:$PATH"
[ "$(command -v docker)" = "$work/bin/docker" ]
export COMPOSE_FILE="$work/selected-compose.yml" ENV_FILE="$work/selected.env" IMAGES_ENV_FILE="$work/selected-images.env"
bash "$work/project/infra/backup/backup.sh" >/dev/null
dump=$(find "$work/project/infra/backup/dumps" -name '*.dump' -print -quit)
[ -s "$dump" ]
grep -q -- '--env-file .*selected.env --env-file .*selected-images.env -f .*selected-compose.yml' "$DOCKER_CALLS"
bash "$work/project/infra/backup/restore.sh" -y "$dump" >/dev/null
grep -q -- 'pg_restore --exit-on-error --single-transaction --clean --if-exists' "$DOCKER_CALLS"
if FAIL_DUMP=1 bash "$work/project/infra/backup/backup.sh" >/dev/null 2>&1; then
  echo 'Failed dump incorrectly succeeded' >&2; exit 1
fi
if BACKUP_KEEP=0 bash "$work/project/infra/backup/backup.sh" >/dev/null 2>&1; then
  echo 'Invalid retention incorrectly succeeded' >&2; exit 1
fi
bash "$work/deploy/deploy.sh" backend ghcr.io/example/repo/backend:v1.0.0 >/dev/null
bash "$work/deploy/deploy.sh" ia ghcr.io/example/repo/ia:v1.1.0 >/dev/null
grep -q '^BACKEND_IMAGE=ghcr.io/example/repo/backend:v1.0.0$' "$work/deploy/.images.env"
grep -q '^IA_IMAGE=ghcr.io/example/repo/ia:v1.1.0$' "$work/deploy/.images.env"
grep -q -- 'up -d --wait --wait-timeout 180' "$DOCKER_CALLS"
if bash "$work/deploy/deploy.sh" backend 'bad image' >/dev/null 2>&1; then
  echo 'Invalid image incorrectly accepted' >&2; exit 1
fi
# Verify that the staging workflow preserves the acceptance transport command.
grep -q 'infra/deploy/deploy.sh infra/check_v01.py' "$source_dir/../.github/workflows/deploy-staging.yml"
grep -q 'exec -T backend python - --url http://mobile < check_v01.py' "$source_dir/../.github/workflows/deploy-staging.yml"
echo 'PASS: selectable backup target, failed dump, retention guard, transactional restore, persisted deployment images, readiness wait'
