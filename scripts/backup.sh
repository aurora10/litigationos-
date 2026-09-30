#!/usr/bin/env bash
# Nightly backup: pg_dump + SeaweedFS volume snapshot into ./backups/<date>.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=backups/$STAMP
mkdir -p "$OUT"

echo "backing up postgres..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-litigation}" -Fc --no-owner -f "/backup/db.dump" "${POSTGRES_DB:-litigation}" 2>/dev/null || \
  docker compose exec -T db pg_dump -U "${POSTGRES_USER:-litigation}" -Fc --no-owner "${POSTGRES_DB:-litigation}" > "$OUT/db.dump"

echo "backing up seaweedfs volume..."
docker run --rm -v litigationos-_s3data:/data -v "$PWD/$OUT":/out alpine sh -c "cd /data && tar czf /out/s3data.tar.gz ."

echo "backup complete: $OUT"
ls -la "$OUT"
