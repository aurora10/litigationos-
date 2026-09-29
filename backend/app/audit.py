"""Audit logging (D03-T04). Single writer used by every mutating route."""
import json
import os

import psycopg


def audit(actor_type, actor_id, action, entity_type, entity_id, old=None, new=None):
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        conn.execute(
            "INSERT INTO audit_logs (actor_type, actor_id, action, entity_type, entity_id, old_value, new_value)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                actor_type,
                actor_id,
                action,
                entity_type,
                str(entity_id) if entity_id is not None else None,
                json.dumps(old, default=str) if old is not None else None,
                json.dumps(new, default=str) if new is not None else None,
            ),
        )
