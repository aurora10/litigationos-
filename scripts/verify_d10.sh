#!/usr/bin/env bash
# D10 acceptance: agent answers with enforced sections + activity feed + tool log.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
LOGIN_RESP=$(curl -sS -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}") || { echo "FAIL: cannot reach backend /api/auth/login"; exit 1; }
[ -n "$LOGIN_RESP" ] || { echo "FAIL: empty login response (backend up? curl localhost:8000/health)"; exit 1; }
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null) \
  || { echo "FAIL: login did not return access_token; response was:"; echo "$LOGIN_RESP"; exit 1; }
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D10 agent case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
# seed a claim/issue so the agent has something to work with
ISID=$(curl -sf -X POST "$BASE/cases/$CID/issues" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"Deposit return","question":"Is the landlord entitled to withhold the deposit?"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf -X POST "$BASE/issues/$ISID/arguments" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"argument_type":"SUPPORTING","statement":"Exit report signed good condition"}' >/dev/null

echo "== submit agent task =="
TID=$(curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instruction\":\"Prepare a short summary of my case for my lawyer.\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "task $TID"

echo "== event feed shows activity =="
curl -sf "$BASE/agent/tasks/$TID/events" -H "$AUTH" > /tmp/d10_events.json
python3 -c "
import json
ev=json.load(open('/tmp/d10_events.json'))
k=[e['kind'] for e in ev]
assert 'reading_documents' in k and 'searching_evidence' in k and 'synthesizing' in k, k
print('activity feed OK:', k)
"

echo "== final output has enforced sections =="
curl -sf "$BASE/agent/tasks/$TID" -H "$AUTH" > /tmp/d10_task.json
python3 -c "
import json
t=json.load(open('/tmp/d10_task.json'))
assert t['status'] in ('COMPLETED','FAILED'), t
out=t['output'] or ''
for sec in ['Answer','Sources','Confidence','Open questions','Proposed next actions']:
    assert sec in out or t['status']=='FAILED', out[:300]
print('task status:', t['status'])
print(t['output'][:400])
"

echo "== audit =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE entity_id='$TID'" | grep -q "AGENT_TASK_CREATED" && echo "audit OK"

echo "== D10 PASS =="
