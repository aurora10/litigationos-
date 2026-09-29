"""Database bootstrap: applies schema migrations at backend startup.

Convention: backend/app/migrations/NNNN_name.sql, applied once each,
tracked in the _migrations table. Runs idempotently on every boot so
`docker compose up` is all that's needed.
"""
import logging
from pathlib import Path

import psycopg

log = logging.getLogger("migrations")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def apply_migrations(database_url: str) -> list[str]:
    applied = []
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _migrations ("
            "name TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT name FROM _migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO _migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
            log.info("applied migration %s", path.name)
    return applied
