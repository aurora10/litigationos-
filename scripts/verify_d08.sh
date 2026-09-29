#!/usr/bin/env bash
# D08 acceptance: issue tree with arguments, sourced claims, missing-evidence.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D08 issue case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "test evidence aansluiting plaats" > /tmp/d08_doc.txt
DID=$(curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d08_doc.txt \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== create issue =="
ISID=$(curl -sf -X POST "$BASE/cases/$CID/issues" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"Condition at handover","question":"Was the property delivered in good condition?"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== add arguments FOR / AGAINST =="
curl -sf -X POST "$BASE/issues/$ISID/arguments" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"argument_type":"SUPPORTING","statement":"Signed exit report confirms good condition"}' | grep -q id && echo "for OK"
curl -sf -X POST "$BASE/issues/$ISID/arguments" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"argument_type":"OPPOSING","statement":"Landlord claims later photos show damage"}' | grep -q id && echo "against OK"

echo "== add claim WITH provenance =="
curl -sf -X POST "$BASE/issues/$ISID/claims" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"statement\":\"Landlord confirmed good condition at exit\",\"evidence_document_id\":\"$DID\",\"evidence_page\":1}" \
  | grep -q id && echo "claim OK"

echo "== issues tree shows source + no 'missing sources' for that claim =="
curl -sf "$BASE/cases/$CID/issues" -H "$AUTH" > /tmp/d08.json
grep -q '"Was the property delivered in good condition?"' /tmp/d08.json
python3 - <<PY
import json
tree=json.load(open('/tmp/d08.json'))[0]
cl=tree["claims"][0]
assert cl["sources"][0]["page"]==1, cl["sources"]
assert not any(f"claim without source" in m for m in tree["missing"]), tree["missing"]
print("issue tree OK, missing:", tree["missing"])
PY

echo "== audit =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM audit_logs WHERE entity_id IN (SELECT id FROM issues WHERE case_id='$CID')" | grep -qv '^ *0$' && echo "audit OK"

echo "== D08 PASS =="
