#!/usr/bin/env bash
# D09 acceptance: full-text + semantic search with provenance.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D09 search case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== upload a text doc and OCR it =="
cat > /tmp/d09_lease.txt <<'TXT'
HUUROVERENKOMST. Artikel 1: de huurwaarborg bedraagt twee maanden huur.
Artikel 5: de oplevering gebeurt in aanwezigheid van beide partijen.
Het pand wordt in goede staat overgeleverd. Waarborg terugbetaling.
TXT
DID=$(curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d09_lease.txt \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
# txt isn't OCR'd by worker; insert text directly to isolate search behaviour
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -c \
  "INSERT INTO document_text (document_id,page_number,text_content) VALUES ('$DID',1,'HUUROVERENKOMST. Artikel 1: de huurwaarborg bedraagt twee maanden huur. Artikel 5: de oplevering gebeurt. Het pand wordt in goede staat overgeleverd. Waarborg terugbetaling.')" >/dev/null

echo "== full-text search: keyword 'waarborg' =="
curl -sf "$BASE/search?q=waarborg" -H "$AUTH" > /tmp/d09.json
python3 -c "
import json
r=json.load(open('/tmp/d09.json'))
assert r['results'], r
assert r['results'][0]['provenance']['document_id']=='$DID'
print('fulltext OK, score %.3f' % r['results'][0]['score'])
"

echo "== semantic: same doc found by meaning without keyword =="
curl -sf -X POST "$BASE/cases/$CID/documents/$DID/embed" -H "$AUTH" | grep -q embedded_chunks
curl -sf "$BASE/search?q=deposit%20repayment&semantic=1" -H "$AUTH" > /tmp/d09s.json
python3 -c "
import json
r=json.load(open('/tmp/d09s.json'))
assert r['results'] and r['results'][0]['document_id']=='$DID', r
print('semantic OK')
"

echo "== D09 PASS =="
