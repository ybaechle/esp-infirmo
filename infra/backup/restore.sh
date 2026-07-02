#!/usr/bin/env bash
# infra/backup/restore.sh — restauration PostgreSQL locale/staging (INF-16).
#
# COMPLIANCE (AGENTS.md §5, infra/hds/README.md) : comme backup.sh, ce script
# vise les environnements LOCAL et STAGING (données SYNTHÉTIQUES uniquement).
# Sur l'environnement HDS cible, la restauration relève du dispositif certifié
# de l'hébergeur (activité 6) — voir ../hds/README.md.
#
# Usage :
#   ./restore.sh dumps/infirmo-infirmo-20260702T140000Z.dump       # demande confirmation
#   ./restore.sh -y dumps/infirmo-infirmo-20260702T140000Z.dump    # sans confirmation
#
# ATTENTION : restauration destructive. --clean --if-exists supprime les
# objets existants de la base cible avant de recréer ceux du dump.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

usage() {
  echo "Usage: $0 [-y] <fichier.dump>" >&2
  exit 1
}

skip_confirm=0
dump_file=""

while [ $# -gt 0 ]; do
  case "$1" in
    -y)
      skip_confirm=1
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      dump_file="$1"
      shift
      ;;
  esac
done

if [ -z "${dump_file}" ]; then
  usage
fi

if [ ! -f "${dump_file}" ]; then
  echo "[restore] Fichier introuvable : ${dump_file}" >&2
  exit 1
fi

if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^(POSTGRES_USER|POSTGRES_DB)=' "${ENV_FILE}")
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-infirmo}"
POSTGRES_DB="${POSTGRES_DB:-infirmo}"

if [ "${skip_confirm}" -ne 1 ]; then
  echo "[restore] Cette opération va ÉCRASER le contenu de la base '${POSTGRES_DB}'"
  echo "[restore] avec le contenu de : ${dump_file}"
  read -r -p "[restore] Confirmer ? (taper 'oui' pour continuer) " answer
  if [ "${answer}" != "oui" ]; then
    echo "[restore] Annulé."
    exit 1
  fi
fi

echo "[restore] Restauration de '${dump_file}' dans la base '${POSTGRES_DB}'..."

# --clean --if-exists : supprime les objets existants avant recréation, sans
# échouer si un objet du dump n'existe pas encore dans la base cible.
docker compose -f "${REPO_ROOT}/docker-compose.yml" exec -T db \
  pg_restore --clean --if-exists -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  < "${dump_file}"

echo "[restore] Terminé."
