#!/usr/bin/env bash
# D01 acceptance: starts the stack and verifies every service.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== starting stack =="
docker compose up -d --build

echo "== service status =="
docker compose ps

echo "== backend health =="
health_status=""
for i in $(seq 1 30); do
  sleep 2
  health_status=$(curl -fs localhost:8000/health 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "down")
  [ "$health_status" = "ok" ] && break
done
curl -fs localhost:8000/health && echo
[ "$health_status" = "ok" ] || { echo "FAIL: backend not ok (got $health_status)"; exit 1; }

echo "== frontend =="
curl -fs -o /dev/null -w "frontend http %{http_code}\n" localhost:3000

echo "== worker connected to redis =="
docker compose logs worker 2>&1 | grep -q "connected to redis" && echo "worker ok"

echo "== D01 PASS =="
