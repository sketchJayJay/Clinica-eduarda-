#!/usr/bin/env bash
set -euo pipefail
DATA_DIR="${DATA_DIR:-/data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_FILE="${DB_FILE:-eduarda_imbelloni_premium.db}"
mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
if [ ! -f "${DATA_DIR}/${DB_FILE}" ]; then
  echo "Banco não encontrado em ${DATA_DIR}/${DB_FILE}"
  exit 1
fi
cp "${DATA_DIR}/${DB_FILE}" "${BACKUP_DIR}/eduarda_clinica_${TS}.db"
echo "Backup ok: ${BACKUP_DIR}/eduarda_clinica_${TS}.db"
