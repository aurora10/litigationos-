#!/usr/bin/env bash
# D18 acceptance: production compose boots, /health reachable via Caddy.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DOMAIN:?set DOMAIN in .env (e.g. DOMAIN=localhost)}"
export DOMAIN

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
code=000
for i in $(seq 1 60); do
  sleep 2
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://$DOMAIN/health")
  [ "$code" = "200" ] && break
done
[ "$code" = "200" ] || { echo "FAIL: https://$DOMAIN/health returned $code"; exit 1; }
curl -sk "https://$DOMAIN/health" | grep -q '"status":"ok"'
echo "== D18 PASS =="
