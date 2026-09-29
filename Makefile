SHELL := /bin/bash

.PHONY: up down logs psql test
up:        ; docker compose up -d
down:      ; docker compose down
logs:      ; docker compose logs -f
psql:      ; docker compose exec db psql -U $${POSTGRES_USER:-litigation} -d $${POSTGRES_DB:-litigation}
test:      ; ./scripts/verify_d01.sh
