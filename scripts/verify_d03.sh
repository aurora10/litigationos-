#!/usr/bin/env bash
# D03 acceptance: case CRUD + parties + audit, all behind auth.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}

TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

echo "== create case =="
CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"CASE-001 deposit dispute","jurisdiction":"BE-Vrederechter-Leuven"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "created $CID"

echo "== list/get =="
curl -sf "$BASE/cases" -H "$AUTH" | grep -q "CASE-001" && echo "list OK"
curl -sf "$BASE/cases/$CID" -H "$AUTH" | grep -q "BE-Vrederechter-Leuven" && echo "get OK"

echo "== add party =="
curl -sf -X POST "$BASE/cases/$CID/parties" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Mr Landlord","role":"LANDLORD"}' | grep -q '"id"' && echo "party OK"

echo "== update =="
curl -sf -X PATCH "$BASE/cases/$CID" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"case_number":"03/26/001"}' | grep -q "03/26/001" && echo "update OK"

echo "== audit rows exist =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM audit_logs WHERE entity_type IN ('case','party')" | grep -qv '^ *0$' && echo "audit OK"

echo "== soft archive (no hard delete) =="
curl -sf -X DELETE "$BASE/cases/$CID" -H "$AUTH" | grep -q ARCHIVED && echo "archive OK"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT status FROM cases WHERE id='$CID'" | grep -q ARCHIVED && echo "row still present (soft) OK"

echo "== still protected =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/cases")
[ "$code" = "401" ] && echo "unauth 401 OK"

echo "== D03 PASS =="
