"""Deadlines + dashboard (D15). Also executes approved drafts (send path) — D15's
two halves: surface what is due, and execute what was approved."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.audit import audit
from app.deps import current_user_id

router = APIRouter(tags=["deadlines"])


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


@router.get("/deadlines")
def list_deadlines(status: str | None = Query(None), due_before: str | None = Query(None),
                   user_id: str = Depends(current_user_id)):
    q = ("SELECT d.id,d.case_id,d.due_date,d.description,d.status,c.title AS case_title"
         " FROM deadlines d LEFT JOIN cases c ON c.id=d.case_id")
    conds, params = [], []
    if status:
        conds.append("d.status=%s"); params.append(status)
    if due_before:
        conds.append("d.due_date<=%s"); params.append(due_before)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY d.due_date"
    with _db() as conn:
        rows = conn.execute(q, params).fetchall()
    return [{"id": str(r[0]), "case_id": str(r[1]), "due_date": str(r[2]),
             "description": r[3], "status": r[4], "case_title": r[5]} for r in rows]


@router.get("/cases/{case_id}/deadlines")
def case_deadlines(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,due_date,description,status FROM deadlines WHERE case_id=%s ORDER BY due_date",
            (str(case_id),),
        ).fetchall()
    return [{"id": str(r[0]), "due_date": str(r[1]), "description": r[2], "status": r[3]} for r in rows]


@router.post("/cases/{case_id}/deadlines", status_code=201)
def add_deadline(case_id: UUID, body: dict, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "INSERT INTO deadlines (case_id,due_date,description,status) VALUES (%s,%s,%s,'PROPOSED') RETURNING id",
            (str(case_id), body["due_date"], body.get("description", "")),
        ).fetchone()
    audit("USER", user_id, "INSERT", "deadline", str(r[0]), new={"case_id": str(case_id), **body})
    return {"id": str(r[0]), "status": "PROPOSED", **body}


@router.patch("/deadlines/{deadline_id}")
def review_deadline(deadline_id: UUID, action: dict, user_id: str = Depends(current_user_id)):
    """action = {'status':'APPROVED'|'COMPLETED'|'MISSED'}"""
    status = action.get("status")
    if status not in ("APPROVED", "COMPLETED", "MISSED"):
        raise HTTPException(400, "status must be APPROVED|COMPLETED|MISSED")
    with _db() as conn:
        r = conn.execute("UPDATE deadlines SET status=%s WHERE id=%s RETURNING id", (status, str(deadline_id))).fetchone()
    if not r:
        raise HTTPException(404, "not found")
    audit("USER", user_id, f"DEADLINE_{status}", "deadline", str(deadline_id))
    return {"id": str(deadline_id), "status": status}


@router.get("/dashboard")
def dashboard(user_id: str = Depends(current_user_id)):
    """Deadlines due/overdue + inbox needing review + recent agent tasks."""
    with _db() as conn:
        upcoming = conn.execute(
            "SELECT id,case_id,due_date,description,status FROM deadlines"
            " WHERE status IN ('PROPOSED','APPROVED') ORDER BY due_date LIMIT 20"
        ).fetchall()
        inbox = conn.execute("SELECT count(*) FROM inbox_items WHERE status='REVIEW_REQUIRED'").fetchone()[0]
        tasks = conn.execute(
            "SELECT id,case_id,instruction,status,created_at FROM agent_tasks ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    return {
        "upcoming_deadlines": [{"id": str(r[0]), "case_id": str(r[1]), "due_date": str(r[2]),
                                "description": r[3], "status": r[4]} for r in upcoming],
        "inbox_review_count": inbox,
        "recent_agent_tasks": [{"id": str(r[0]), "case_id": str(r[1]), "instruction": r[2][:120],
                                "status": r[3], "created_at": r[4].isoformat()} for r in tasks],
    }


# ---- send execution for approved drafts (approval-gated) ----

@router.post("/approvals/{approval_id}/execute", status_code=202)
def execute_approval(approval_id: UUID, user_id: str = Depends(current_user_id)):
    """Executes an APPROVED approval. For SEND_EMAIL in v1: create OUT communication
    and mark EXECUTED. (Real SMTP sending via n8n is a small follow-up; the approval
    gate is the hard requirement — nothing sends without this call.)"""
    with _db() as conn:
        ap = conn.execute("SELECT approval_type,payload,status FROM approvals WHERE id=%s", (str(approval_id),)).fetchone()
        if not ap or ap[2] != "APPROVED":
            raise HTTPException(404, "approval not APPROVED")
        payload = ap[1]
        if ap[0] != "SEND_EMAIL":
            raise HTTPException(400, f"execute not supported for approval_type={ap[0]}")
        d = conn.execute("SELECT case_id,body FROM drafts WHERE id=%s", (payload["draft_id"],)).fetchone()
        conn.execute(
            "INSERT INTO communications (case_id,direction,channel,subject) VALUES (%s,'OUT','EMAIL',%s)",
            (str(d[0]), payload.get("subject", "")),
        )
        conn.execute("UPDATE approvals SET status='EXECUTED' WHERE id=%s", (str(approval_id),))
        conn.execute("UPDATE drafts SET status='EXECUTED', updated_at=now() WHERE id=%s", (payload["draft_id"],))
    audit("USER", user_id, "EXECUTED", "approval", str(approval_id), new=payload)
    return {"approval_id": str(approval_id), "status": "EXECUTED"}
