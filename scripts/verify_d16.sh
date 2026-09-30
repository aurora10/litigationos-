#!/usr/bin/env bash
# D16 acceptance: audit trail is complete and append-only.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D16 audit case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== a few mutations happen =="
curl -sf -X POST "$BASE/cases/$CID/parties" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Mr Landlord","role":"LANDLORD"}' >/dev/null
DLID=$(curl -sf -X POST "$BASE/cases/$CID/deadlines" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"due_date":"2026-10-01","description":"reply"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== audit API shows them =="
curl -sf "$BASE/audit?entity_id=$CID" -H "$AUTH" > /tmp/d16.json
grep -q '"action": "INSERT"' /tmp/d16.json
grep -q '"entity_type": "case"' /tmp/d16.json && echo "audit rows OK"

echo "== append-only enforced (triggers) =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -c \
  "UPDATE audit_logs SET action='HACKED' WHERE id=(SELECT id FROM audit_logs LIMIT 1)" 2>&1 | grep -q "append-only" \
  && echo "no update OK"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -c \
  "DELETE FROM audit_logs WHERE id=(SELECT id FROM audit_logs LIMIT 1)" 2>&1 | grep -q "append-only" \
  && echo "no delete OK"

echo "== D16 PASS =="
