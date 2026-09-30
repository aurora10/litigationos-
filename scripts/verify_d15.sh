#!/usr/bin/env bash
# D15 acceptance: deadlines per case + dashboard + send-execution gate.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D15 deadlines case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== add deadlines =="
DL1=$(curl -sf -X POST "$BASE/cases/$CID/deadlines" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"due_date":"2026-10-15","description":"Reply to landlord letter"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
DL2=$(curl -sf -X POST "$BASE/cases/$CID/deadlines" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"due_date":"2026-11-02","description":"File conclusion at Vrederechter"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== dashboard surfaces upcoming =="
curl -sf "$BASE/dashboard" -H "$AUTH" > /tmp/d15.json
grep -q "Reply to landlord letter" /tmp/d15.json
grep -q '"inbox_review_count"' /tmp/d15.json && echo "dashboard OK"

echo "== approve first deadline =="
curl -sf -X PATCH "$BASE/deadlines/$DL1" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"APPROVED"}' | grep -q APPROVED && echo "approve OK"

echo "== full send gate: draft → approve → execute → communication created =="
DRAFT=$(curl -sf -X POST "$BASE/cases/$CID/drafts" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"kind":"EMAIL","instruction":"Notify lawyer"}')
DID=$(echo "$DRAFT" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
APID=$(curl -sf -X POST "$BASE/drafts/$DID/submit?to=adv@x.be&subject=Update" -H "$AUTH" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['approval_id'])")
curl -sf -X POST "$BASE/approvals/$APID/approve" -H "$AUTH" >/dev/null
curl -sf -X POST "$BASE/approvals/$APID/execute" -H "$AUTH" | grep -q EXECUTED && echo "execute OK"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM communications WHERE direction='OUT' AND case_id='$CID'" | grep -vq '^ *0$' && echo "OUT communication created"

echo "== D15 PASS =="
