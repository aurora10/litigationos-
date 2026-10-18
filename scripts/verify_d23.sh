#!/usr/bin/env bash
# D23 acceptance: conversational iteration on drafts
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D23 conversation test"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== create a draft =="
DRAFT=$(curl -sf -X POST "$BASE/cases/$CID/drafts" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"kind":"EMAIL","instruction":"Email to lawyer about deposit dispute"}')
DID=$(echo "$DRAFT" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "draft $DID created"

echo "== converse: ask for rewrite =="
T1=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"make the email shorter and more formal\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "$BASE/agent/tasks/$T1" -H "$AUTH" > /tmp/d23_1.json
python3 -c "
import json
t=json.load(open('/tmp/d23_1.json'))
assert t['status']=='COMPLETED', t
assert t['role']=='d23', t
print('d23 response:', t['output'][:200])
"

echo "== add evidence mid-conversation =="
T2=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"add the exit report as evidence\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "$BASE/agent/tasks/$T2" -H "$AUTH" > /tmp/d23_2.json
python3 -c "
import json
t=json.load(open('/tmp/d23_2.json'))
print('d23 response 2:', t['output'][:200])
"

echo "== D23 PASS =="