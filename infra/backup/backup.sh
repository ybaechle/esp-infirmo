#!/usr/bin/env bash
# infra/backup/backup.sh — sauvegarde PostgreSQL locale/staging (INF-16).
#
# COMPLIANCE (AGENTS.md, infra/hds/README.md) : la sauvegarde de
# véritables données de santé est l'activité HDS n°6 (Art. R1111-9 CSP).
# Ce script est prévu pour les environnements LOCAL et STAGING, qui ne
# contiennent que des données SYNTHÉTIQUES (voir infra/hds/README.md §2-3).
# Sur l'environnement HDS cible, c'est le dispositif de sauvegarde certifié
# de l'hébergeur (activité 6) qui s'applique — voir ../hds/README.md.
#
# Usage :
#   ./backup.sh                 # dump vers infra/backup/dumps/, rotation 7
#   BACKUP_KEEP=14 ./backup.sh  # conserve les 14 dumps les plus récents
#
# Lit POSTGRES_USER / POSTGRES_DB depuis le .env à la racine du repo s'il
# existe (mêmes variables que docker-compose.yml). Le mot de passe n'est pas
# nécessaire ici : pg_dump s'exécute *dans* le conteneur "db" via
# `docker compose exec`, authentifié localement (peer/trust sur le socket
# du conteneur), pas besoin de PGPASSWORD sur l'hôte.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DUMPS_DIR="${SCRIPT_DIR}/dumps"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
if [ -n "${IMAGES_ENV_FILE:-}" ]; then
  compose=(docker compose --env-file "$ENV_FILE" --env-file "$IMAGES_ENV_FILE" -f "$COMPOSE_FILE")
fi

# Nombre de dumps les plus récents à conserver (rotation).
BACKUP_KEEP="${BACKUP_KEEP:-7}"
[[ "$BACKUP_KEEP" =~ ^[1-9][0-9]*$ ]] || { echo "BACKUP_KEEP must be positive" >&2; exit 1; }

# Charge POSTGRES_USER / POSTGRES_DB depuis .env si présent, sans écraser
# des variables déjà positionnées dans l'environnement appelant.
POSTGRES_USER="$("${compose[@]}" exec -T db printenv POSTGRES_USER | tr -d '\r')"
POSTGRES_DB="$("${compose[@]}" exec -T db printenv POSTGRES_DB | tr -d '\r')"

mkdir -p "${DUMPS_DIR}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump_file="${DUMPS_DIR}/infirmo-${POSTGRES_DB}-${timestamp}.dump"

echo "[backup] Sauvegarde de la base '${POSTGRES_DB}' (utilisateur '${POSTGRES_USER}')..."

# Format custom (-Fc) : compressé, restaurable sélectivement avec pg_restore.
# -T (pas -i) : exécuté dans le conteneur "db" déjà démarré par
# docker compose ; ne nécessite pas de client pg_dump sur l'hôte.
"${compose[@]}" exec -T db \
  pg_dump -Fc -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${dump_file}.partial"
mv "${dump_file}.partial" "${dump_file}"

size_bytes="$(wc -c < "${dump_file}" | tr -d ' ')"
echo "[backup] OK : ${dump_file} (${size_bytes} octets)"

# Rotation : ne garder que les BACKUP_KEEP dumps les plus récents.
mapfile -t existing_dumps < <(ls -1t "${DUMPS_DIR}"/infirmo-"${POSTGRES_DB}"-*.dump 2>/dev/null || true)
count="${#existing_dumps[@]}"
if [ "${count}" -gt "${BACKUP_KEEP}" ]; then
  echo "[backup] Rotation : ${count} dumps présents, conservation des ${BACKUP_KEEP} plus récents."
  for old_dump in "${existing_dumps[@]:${BACKUP_KEEP}}"; do
    echo "[backup]   suppression : ${old_dump}"
    rm -f -- "${old_dump}"
  done
fi

echo "[backup] Terminé."
