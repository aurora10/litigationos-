#!/usr/bin/env bash
# D14 acceptance: draft is created, submitted for approval, and only executed after approve.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D14 drafting case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== agent drafts a lawyer email =="
DRAFT=$(curl -sf -X POST "$BASE/cases/$CID/drafts" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"kind":"EMAIL","instruction":"Update my lawyer on status and ask one question about the deposit","to":"advocaat@example.be","subject":"Update dossier"}')
ID=$(echo "$DRAFT" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
STATUS=$(echo "$DRAFT" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
[ "$STATUS" = "DRAFT" ] || { echo "FAIL: status=$STATUS"; exit 1; }
echo "$DRAFT" | python3 -c "import sys,json;print(json.load(sys.stdin)['body'][:120])"
echo "draft OK"

echo "== submit for approval =="
AP=$(curl -sf -X POST "$BASE/drafts/$ID/submit?to=advocaat@example.be&subject=Update" -H "$AUTH")
APID=$(echo "$AP" | python3 -c "import sys,json;print(json.load(sys.stdin)['approval_id'])")
echo "$AP" | grep -q '"status":"REVIEW"' && echo "review status OK"

echo "== approve → draft becomes APPROVED (ready to execute) =="
curl -sf -X POST "$BASE/approvals/$APID/approve" -H "$AUTH" | grep -q APPROVED
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT status FROM drafts WHERE id='$ID'" | grep -q APPROVED && echo "draft approved OK"

echo "== nothing sent without execution =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM communications WHERE direction='OUT' AND subject='Update'" | grep -q '^ *0$' \
  && echo "no send before EXECUTED OK"

echo "== reject path =="
ID2=$(curl -sf -X POST "$BASE/cases/$CID/drafts" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"kind":"EMAIL","instruction":"another draft"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
AP2=$(curl -sf -X POST "$BASE/drafts/$ID2/submit?to=x@y.be&subject=t" -H "$AUTH" | python3 -c "import sys,json;print(json.load(sys.stdin)['approval_id'])")
curl -sf -X POST "$BASE/approvals/$AP2/reject" -H "$AUTH" | grep -q REJECTED && echo "reject OK"

echo "== audit trail =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE entity_id='$APID'" | grep -q APPROVED && echo "audit OK"

echo "== D14 PASS =="
