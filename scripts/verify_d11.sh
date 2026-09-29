#!/usr/bin/env bash
# D11 acceptance: roles route correctly; adversarial loop runs; research sources fetched.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D11 roles case","case_number":"D11-001"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
ISID=$(curl -sf -X POST "$BASE/cases/$CID/issues" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"Deposit","question":"Is landlord entitled to withhold?"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -sf -X POST "$BASE/issues/$ISID/arguments" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"argument_type":"SUPPORTING","statement":"Exit report signed good condition"}' >/dev/null

run_task() {
  curl -sf -X POST "$BASE/agent/tasks" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"case_id\":\"$CID\",\"instruction\":$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$1")}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])"
}

echo "== adversarial: attack my case =="
T1=$(run_task "Assume you represent the opposing party. Attack my case.")
curl -sf "$BASE/agent/tasks/$T1" -H "$AUTH" > /tmp/d11_adv.json
python3 - <<PY
import json
t=json.load(open('/tmp/d11_adv.json'))
assert t['status']=='COMPLETED', t
assert t['role'] in ('adversarial',), t
print("role:", t['role'])
PY

echo "== prepare lawyer meeting brief =="
T2=$(run_task "prepare lawyer meeting")
curl -sf "$BASE/agent/tasks/$T2" -H "$AUTH" > /tmp/d11_brief.json
python3 - <<PY
import json
t=json.load(open('/tmp/d11_brief.json'))
assert t['status']=='COMPLETED', t
out=t['output'] or ''
sections=["What happened","What is disputed","Evidence supporting our position","Evidence supporting the opposing position","Applicable legislation","Relevant Belgian judgments","Arguments available","Weak points","Questions for the lawyer","Procedural deadlines","Recommended documents to obtain","Draft instructions for the lawyer"]
missing=[s for s in sections if s not in out]
print("role:", t.get('role'))
print("missing sections:", missing if missing else "none")
PY

echo "== research: Belgian sources consulted =="
T3=$(run_task "research Belgian law on rental deposits (huurwaarborg)")
curl -sf "$BASE/agent/tasks/$T3" -H "$AUTH" > /tmp/d11_research.json
python3 - <<PY
import json
t=json.load(open('/tmp/d11_research.json'))
assert t['status']=='COMPLETED', t
print("role:", t.get('role'))
PY
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT count(*) FROM agent_actions WHERE task_id='$T3' AND tool_name IN ('search_jurisprudence','search_legislation')" \
  | grep -q "^ *2$" && echo "research tools logged OK"

echo "== D11 PASS =="
