#!/usr/bin/env bash
# D06 acceptance: inbox upload → classification → review → proposals committed.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

# case with a case_number the classifier can match to
CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D06 inbox case","case_number":"D06-001"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== inbox upload (case-matching letter) =="
cat > /tmp/d06_letter.txt <<'TXT'
Geachte,
Betreft: dossier D06-001 — huurwaarborg.
We verwachten uw antwoord binnen 30 dagen, uiterlijk 15/10/2026.
Hoogachtend, de verhuurder
TXT
IID=$(curl -sf -X POST "$BASE/inbox" -H "$AUTH" -F file=@/tmp/d06_letter.txt \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "item $IID"

echo "== classified + matched =="
curl -sf "$BASE/inbox/$IID" -H "$AUTH" > /tmp/d06_item.json
python3 -c "
import json,sys
i=json.load(open('/tmp/d06_item.json'))
assert i['status']=='REVIEW_REQUIRED', i
assert i['match_status']=='MATCHED', i
assert i['matched_case_id']=='$CID', i
assert any(h for h in i['classification']['deadline_hints']), i
print('classification+match OK:', i['classification']['document_type'])
"
grep -q '"proposal_type": "DEADLINE"' /tmp/d06_item.json && echo "deadline proposal OK"

echo "== approve → proposals commit =="
curl -sf -X POST "$BASE/inbox/$IID/approve" -H "$AUTH" | grep -q APPROVED && echo "approved"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM deadlines WHERE case_id='$CID'" | grep -qv '^ *0$' && echo "deadline committed OK"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE entity_id='$IID'" | grep -q INBOX_APPROVED && echo "audit OK"

echo "== reject path =="
IID2=$(curl -sf -X POST "$BASE/inbox" -H "$AUTH" -F file=@/tmp/d06_letter.txt \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf -X POST "$BASE/inbox/$IID2/reject" -H "$AUTH" | grep -q REJECTED && echo "reject OK"

echo "== D06 PASS =="
