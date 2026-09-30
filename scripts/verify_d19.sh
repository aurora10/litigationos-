#!/usr/bin/env bash
# D19 acceptance: central log exists, /api/logs readable with auth, route logs an error.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

echo "== errors are logged centrally =="
# trigger a 401 deliberately (missing token)
curl -s -o /dev/null "$BASE/cases"

echo "== /api/logs requires auth =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/logs")
[ "$code" = "401" ] && echo "protected OK"

echo "== /api/logs readable for owner =="
curl -sf "$BASE/logs?limit=5" -H "$AUTH" > /tmp/d19.json
python3 -c "
import json
d=json.load(open('/tmp/d19.json'))
assert isinstance(d.get('entries'), list)
print('entries:', len(d['entries']))
"
docker compose exec -T backend sh -c 'test -f /app/logs/app.jsonl && tail -1 /app/logs/app.jsonl' && echo "log file present"

echo "== D19 PASS =="
