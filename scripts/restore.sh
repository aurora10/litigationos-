#!/usr/bin/env bash
# Restore a backup taken with scripts/backup.sh into a fresh stack.
# Usage: ./scripts/restore.sh backups/20260930-120000
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="$1"
[ -d "$SRC" ] || { echo "usage: $0 <backup_dir>"; exit 1; }

echo "resetting stack (data loss!)..."
docker compose down -v
docker compose up -d db s3
sleep 5

echo "restoring db..."
docker compose exec -T db pg_restore -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" --clean --if-exists < "$SRC/db.dump" 2>/dev/null \
  || docker compose exec -T db bash -c "pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists" < "$SRC/db.dump"

echo "restoring s3..."
docker run --rm -v litigationos-_s3data:/data -v "$PWD/$SRC":/in alpine sh -c "cd /data && rm -rf * && tar xzf /in/s3data.tar.gz"
docker compose up -d
echo "restore complete from $SRC"
