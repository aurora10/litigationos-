#!/usr/bin/env bash
# D13 acceptance: email ingestion via webhook — dedupe, thread, inbox enqueue.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
WH=${WEBHOOK_TOKEN:-dev-webhook-token}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

echo "== webhook without token → 401 =="
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/webhooks/email" -H "Content-Type: application/json" -d '{}')
[ "$code" = "401" ] || { echo "FAIL: got $code"; exit 1; }
echo "401 OK"

echo "== ingest email via webhook =="
curl -sS -X POST "$BASE/webhooks/email" -H "Content-Type: application/json" -H "X-Webhook-Token: $WH" \
  -d '{"provider_message_id":"gmail-001","thread_id":"t-1","sender":"landlord@example.com","recipients":["owner@localhost.dev"],"subject":"D13 test email — binnen 30 dagen","body":"Beste, betreft uw dossier: antwoord binnen 30 dagen.","received_at":"2026-09-29T10:00:00"}' \
  | grep -q '"status":"RECEIVED"' && echo "received OK"

echo "== duplicate is deduped =="
curl -sS -X POST "$BASE/webhooks/email" -H "Content-Type: application/json" -H "X-Webhook-Token: $WH" \
  -d '{"provider_message_id":"gmail-001","subject":"dup"}' | grep -q DUPLICATE && echo "dedupe OK"

echo "== appears in Inbox =="
curl -sf "$BASE/inbox" -H "$AUTH" > /tmp/d13.json
python3 -c "
import json
items=json.load(open('/tmp/d13.json'))
e=[i for i in items if i['classification'].get('sender')=='landlord@example.com']
assert e, items
assert e[0]['status']=='REVIEW_REQUIRED'
print('inbox item present; classification:', e[0]['classification']['document_type'])
"

echo "== audit =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE action='EMAIL_RECEIVED'" | grep -q EMAIL_RECEIVED && echo "audit OK"

echo "== D13 PASS =="
