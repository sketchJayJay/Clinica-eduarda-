#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${BASE_DIR}/data"
BACKUP_DIR="${BASE_DIR}/backups"
TS="$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

if [ ! -f "${DATA_DIR}/eduarda_imbelloni.db" ]; then
  echo "Banco não encontrado em ${DATA_DIR}/eduarda_imbelloni.db"
  exit 1
fi

# Backup simples (cópia do DB)
cp "${DATA_DIR}/eduarda_imbelloni.db" "${BACKUP_DIR}/eduarda_imbelloni_${TS}.db"

# Mantém só os últimos 14 backups
ls -1t "${BACKUP_DIR}"/eduarda_imbelloni_*.db | tail -n +15 | xargs -r rm -f

echo "Backup ok: ${BACKUP_DIR}/eduarda_imbelloni_${TS}.db"
