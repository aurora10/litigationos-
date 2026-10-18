#!/usr/bin/env bash
# D21 acceptance: guided intake - one question at a time until READY_FOR_ANALYSIS
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D21 intake test case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== start intake =="
T1=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"help me build my case\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "$BASE/agent/tasks/$T1" -H "$AUTH" > /tmp/d21_1.json
python3 -c "
import json
t=json.load(open('/tmp/d21_1.json'))
assert t['status']=='COMPLETED', t
assert t['role']=='intake', t
out=t['output'] or ''
assert out.startswith('Q:'), out
print('Q1:', out[:120])
"

echo "== answer Q1 =="
ANS1="De keuring was op 15 februari 2024"
T2=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"$ANS1\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "$BASE/agent/tasks/$T2" -H "$AUTH" > /tmp/d21_2.json
python3 -c "
import json
t=json.load(open('/tmp/d21_2.json'))
assert t['role']=='intake', t
out=t['output'] or ''
assert out.startswith('Q:'), out
print('Q2:', out[:120])
"

echo "== answer Q2 =="
ANS2="De huurder heeft de sleutels teruggegeven op 1 maart 2024"
T3=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"$ANS2\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf "$BASE/agent/tasks/$T3" -H "$AUTH" > /tmp/d21_3.json
python3 -c "
import json
t=json.load(open('/tmp/d21_3.json'))
assert t['role']=='intake', t
out=t['output'] or ''
if out.startswith('READY_FOR_ANALYSIS'):
    print('READY_FOR_ANALYSIS reached!')
else:
    print('Q3:', out[:120])
"

echo "== D21 PASS =="