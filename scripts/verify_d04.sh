#!/usr/bin/env bash
# D04 acceptance: upload a document, verify hashing + immutability + audit.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

# need a case
CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D04 test case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== upload =="
echo "dit is een huurovereenkomst testdocument" > /tmp/d04_doc.txt
curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d04_doc.txt > /tmp/d04_resp.json
DID=$(python3 -c "import json;print(json.load(open('/tmp/d04_resp.json'))['id'])")
HASH_API=$(python3 -c "import json;print(json.load(open('/tmp/d04_resp.json'))['file_hash'])")
HASH_LOCAL=$(sha256sum /tmp/d04_doc.txt | cut -d' ' -f1)
[ "$HASH_API" = "$HASH_LOCAL" ] || { echo "FAIL: hash mismatch $HASH_API != $HASH_LOCAL"; exit 1; }
echo "hash match OK ($HASH_LOCAL)"

echo "== original stored + downloadable =="
curl -sf "$BASE/documents/$DID" -H "$AUTH" | grep -q download_url && echo "download URL OK"

echo "== original immutable: re-upload same filename creates NEW document =="
DID2=$(curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d04_doc.txt | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
[ "$DID2" != "$DID" ] && echo "new document row OK (original untouched)"

echo "== document_versions has ORIGINAL =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT version_type FROM document_versions WHERE document_id='$DID'" | grep -q ORIGINAL && echo "ORIGINAL version OK"

echo "== audit row for upload =="
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT action FROM audit_logs WHERE entity_id='$DID'" | grep -q UPLOAD && echo "audit OK"

echo "== D04 PASS =="
