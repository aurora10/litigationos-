#!/usr/bin/env bash
# D02 acceptance: auth guard + login + refresh + owner seed.
# Usage: ./scripts/verify_d02.sh  (on a running stack)
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}

echo "== unauthenticated request is rejected =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/cases")
[ "$code" = "401" ] || { echo "FAIL: expected 401, got $code"; exit 1; }
echo "no-token /cases -> 401 OK"

echo "== login =="
resp=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "login -> 200 + tokens OK"

echo "== authenticated request =="
curl -sf "$BASE/cases" -H "Authorization: Bearer $TOKEN" | grep -q '\[\]' && echo "with-token /cases -> 200 [] OK"

echo "== refresh =="
REFRESH=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")
curl -sf -X POST "$BASE/auth/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | grep -q access_token && echo "refresh -> new access token OK"

echo "== bad password rejected =="
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"wrong\"}")
[ "$code" = "401" ] || { echo "FAIL: expected 401, got $code"; exit 1; }
echo "bad password -> 401 OK"

echo "== owner seed is idempotent =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" \
  -t -c "SELECT count(*) FROM users" | grep -q "^ *1$" && echo "exactly one user row OK"

echo "== D02 PASS =="
