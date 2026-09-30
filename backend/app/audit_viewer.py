"""Audit viewer (D16) — list audit rows; prove append-only."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.deps import current_user_id

router = APIRouter(tags=["audit"])


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


@router.get("/audit")
def list_audit(entity_type: str | None = Query(None), entity_id: UUID | None = Query(None),
               action: str | None = Query(None), limit: int = Query(50, le=200),
               user_id: str = Depends(current_user_id)):
    q = ("SELECT id,actor_type,actor_id,action,entity_type,entity_id,created_at FROM audit_logs")
    conds, params = [], []
    if entity_type:
        conds.append("entity_type=%s"); params.append(entity_type)
    if entity_id:
        conds.append("entity_id=%s"); params.append(str(entity_id))
    if action:
        conds.append("action=%s"); params.append(action)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    with _db() as conn:
        rows = conn.execute(q, params).fetchall()
    return [{
        "id": str(r[0]), "actor_type": r[1], "actor_id": str(r[2]) if r[2] else None,
        "action": r[3], "entity_type": r[4], "entity_id": str(r[5]) if r[5] else None,
        "created_at": r[6].isoformat(),
    } for r in rows]
