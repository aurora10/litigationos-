#!/usr/bin/env bash
# D07 acceptance: timeline events with optional provenance (document + page).
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D07 timeline case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "exit report page 4: appartement in good condition" > /tmp/d07_doc.txt
DID=$(curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d07_doc.txt \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== add timeline event with provenance (doc + page) =="
EID=$(curl -sf -X POST "$BASE/cases/$CID/timeline" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"event_date\":\"2026-02-12\",\"title\":\"Exit inspection signed\",\"source_document_id\":\"$DID\",\"page_number\":4}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "event $EID"

echo "== list shows event with source =="
curl -sf "$BASE/cases/$CID/timeline" -H "$AUTH" > /tmp/d07.json
grep -q "Exit inspection signed" /tmp/d07.json
grep -q "\"document_id\": \"$DID\"" /tmp/d07.json && echo "source linked OK"

echo "== event is PROPOSED until reviewed, then APPROVED =="
grep -q '"verification_status": "PROPOSED"' /tmp/d07.json && echo "starts PROPOSED OK"
curl -sf -X PATCH "$BASE/timeline/$EID" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"APPROVED"}' | grep -q APPROVED && echo "approve OK"

echo "== audit =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE entity_id='$EID'" | grep -q "TIMELINE_APPROVED" && echo "audit OK"

echo "== D07 PASS =="
