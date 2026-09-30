#!/usr/bin/env bash
# D17 acceptance: security + backup+restore.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

echo "== auth still enforced =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/cases")
[ "$code" = "401" ] && echo "unauth 401 OK"

echo "== CORS locked =="
headers=$(curl -sI -X OPTIONS "$BASE/cases" -H "Origin: http://evil.example" -H "Access-Control-Request-Method: GET")
echo "$headers" | grep -qi "access-control-allow-origin: http://evil.example" && { echo "FAIL: CORS too open"; exit 1; } || echo "CORS OK"

echo "== backup =="
./scripts/backup.sh
LATEST=$(ls -1t backups | head -1)
[ -d "backups/$LATEST" ] || { echo "FAIL: no backup dir"; exit 1; }
ls -la backups/$LATEST

echo "== restore =="
./scripts/restore.sh "backups/$LATEST" >/dev/null
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM cases" | grep -vq '^ *0$' && echo "restore OK (data present)"

echo "== D17 PASS =="
