#!/usr/bin/env bash
# Executed in the deployment directory after copying the revision's config.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "Missing deployment .env" >&2; exit 1; }
[ -f .images.env ] || install -m 600 /dev/null .images.env
while [ "$#" -gt 0 ]; do
  module="$1"; image="$2"; shift 2
  case "$module" in backend|ia|mobile) ;; *) echo "Invalid module" >&2; exit 1 ;; esac
  [[ "$image" =~ ^ghcr.io/[a-z0-9_./-]+:[a-zA-Z0-9_.-]+$ ]] || { echo "Invalid image" >&2; exit 1; }
  key="${module^^}_IMAGE"
  temp=$(mktemp .images.XXXXXX)
  grep -v "^${key}=" .images.env > "$temp" || true
  printf '%s=%s
' "$key" "$image" >> "$temp"
  chmod 600 "$temp"
  mv "$temp" .images.env
done
compose=(docker compose --env-file .env --env-file .images.env -f docker-compose.staging.yml)
"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up -d --wait --wait-timeout 180
"${compose[@]}" exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=10)"
"${compose[@]}" exec -T caddy caddy reload --config /etc/caddy/Caddyfile
printf '%s
' 'Deployment containers ready; run the public synthetic acceptance check separately.'
