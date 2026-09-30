#!/usr/bin/env bash
# D18 acceptance: production compose boots, /health reachable via Caddy.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DOMAIN:?set DOMAIN in .env (e.g. DOMAIN=localhost)}"
export DOMAIN

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# localhost is served over plain HTTP (no public cert possible); real domains use https.
if [ "$DOMAIN" = "localhost" ]; then scheme="http"; port=":80"; else scheme="https"; port=""; fi
code=000
for i in $(seq 1 60); do
  sleep 2
  code=$(curl -sk -o /dev/null -w "%{http_code}" "$scheme://$DOMAIN$port/health")
  [ "$code" = "200" ] && break
done
[ "$code" = "200" ] || { echo "FAIL: $scheme://$DOMAIN$port/health returned $code"; exit 1; }
curl -sk "$scheme://$DOMAIN$port/health" | grep -q '"status":"ok"'
echo "== D18 PASS =="
