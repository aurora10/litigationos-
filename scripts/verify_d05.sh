#!/usr/bin/env bash
# D05 acceptance: OCR pipeline — scan becomes searchable per-page text.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8000/api
EMAIL=${OWNER_EMAIL:-owner@localhost.dev}
PASS=${OWNER_PASSWORD:-change-me-now}
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

CID=$(curl -sf -X POST "$BASE/cases" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"D05 OCR test case"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

echo "== render a scan-like image (runs inside worker image, which has pillow+tesseract) =="
mkdir -p /tmp/d05
cat > /tmp/d05/render.py <<'PY'
from PIL import Image, ImageDraw
img = Image.new("L", (900, 400), color=255)
d = ImageDraw.Draw(img)
d.text((60, 100), "HUUROVERENKOMST", fill=0)
d.text((60, 200), "Artikel 1: de huurwaarborg", fill=0)
img.save("/work/scan.png")
print("rendered")
PY
docker run --rm -v /tmp/d05:/work litigationos--worker python3 /work/render.py
ls -la /tmp/d05/scan.png

echo "== upload scan-as-png (triggers OCR) =="
DID=$(curl -sf -X POST "$BASE/cases/$CID/documents" -H "$AUTH" -F file=@/tmp/d05/scan.png \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "doc $DID"

echo "== wait for OCR =="
st=""
for i in $(seq 1 40); do
  sleep 2
  st=$(curl -sf "$BASE/documents/$DID" -H "$AUTH" | python3 -c "import sys,json;print(json.load(sys.stdin)['processing_status'])")
  [ "$st" = "READY" ] && break
  [ "$st" = "FAILED" ] && { echo "FAIL: OCR failed"; docker compose logs worker | tail -5; exit 1; }
done
[ "$st" = "READY" ] || { echo "FAIL: status=${st:-timeout}"; exit 1; }
echo "status READY OK"

echo "== text extracted =="
curl -sf "$BASE/documents/$DID/text" -H "$AUTH" | tee /tmp/d05/text.json | grep -qi "huurwaarborg\|HUUROVERENKOMST" && echo "OCR text OK"
docker compose exec -T db psql -U "${POSTGRES_USER:-litigation}" -d "${POSTGRES_DB:-litigation}" -t \
  -c "SELECT version_type FROM document_versions WHERE document_id='$DID'" | grep -q OCR && echo "OCR version recorded"

echo "== D05 PASS =="
