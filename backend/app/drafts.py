"""Drafting + approval workflow (D14). Agent drafts; human approves; only then send."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id
from app import llm

router = APIRouter(tags=["drafts"])

DRAFT_SYSTEM = """You are the LitigationOS drafting agent. Write a concise Dutch formal letter/email given the case context. Always keep it factual and cite the case's evidence with [DOC:id:page] where relevant.
Output only the draft body; no commentary."""


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


class DraftIn(BaseModel):
    kind: str = "EMAIL"
    instruction: str
    to: str | None = None
    subject: str | None = None


@router.post("/cases/{case_id}/drafts", status_code=201)
def create_draft(case_id: UUID, body: DraftIn, user_id: str = Depends(current_user_id)):
    if body.kind not in ("EMAIL", "LETTER", "BRIEFING", "HEARING_PREP"):
        raise HTTPException(400, "invalid kind")
    with _db() as conn:
        case = conn.execute(
            "SELECT id,title,case_number FROM cases WHERE id=%s", (str(case_id),)
        ).fetchone()
        if not case:
            raise HTTPException(404, "case not found")
        issues = [{"q": r[0], "t": r[1]} for r in conn.execute(
            "SELECT title,question FROM issues WHERE case_id=%s", (str(case_id),)
        )]
        ctx = {"case": {"title": case[1], "case_number": case[2]}, "issues": issues}
        draft_body = llm.complete(
            prompt=f"Instruction: {body.instruction}\n\nContext: {ctx}\n\nTo: {body.to or ''}\nSubject: {body.subject or ''}",
            system=DRAFT_SYSTEM,
        )
        r = conn.execute(
            "INSERT INTO drafts (case_id,kind,body,created_by) VALUES (%s,%s,%s,'agent') RETURNING id",
            (str(case_id), body.kind, draft_body),
        ).fetchone()
    audit("AGENT", user_id, "DRAFT_CREATED", "draft", str(r[0]),
          new={"case_id": str(case_id), "kind": body.kind, "to": body.to, "subject": body.subject})
    return {"id": str(r[0]), "kind": body.kind, "body": draft_body, "status": "DRAFT"}


@router.get("/cases/{case_id}/drafts")
def list_drafts(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,kind,body,status,created_at FROM drafts WHERE case_id=%s ORDER BY created_at DESC",
            (str(case_id),),
        ).fetchall()
    return [{"id": str(r[0]), "kind": r[1], "body": r[2], "status": r[3], "created_at": r[4].isoformat()} for r in rows]


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute("SELECT id,case_id,kind,body,status FROM drafts WHERE id=%s", (str(draft_id),)).fetchone()
    if not r:
        raise HTTPException(404, "draft not found")
    return {"id": str(r[0]), "case_id": str(r[1]), "kind": r[2], "body": r[3], "status": r[4]}


@router.post("/drafts/{draft_id}/submit", status_code=201)
def submit_draft(draft_id: UUID, to: str, subject: str = "", user_id: str = Depends(current_user_id)):
    with _db() as conn:
        d = conn.execute("SELECT id FROM drafts WHERE id=%s AND status='DRAFT'", (str(draft_id),)).fetchone()
        if not d:
            raise HTTPException(404, "draft not found or already submitted")
        conn.execute("UPDATE drafts SET status='REVIEW', updated_at=now() WHERE id=%s", (str(draft_id),))
        ap = conn.execute(
            "INSERT INTO approvals (approval_type,payload,created_by) VALUES ('SEND_EMAIL',%s,'agent') RETURNING id",
            (psycopg.types.json.Json({"draft_id": str(draft_id), "to": to, "subject": subject}),),
        ).fetchone()
    audit("USER", user_id, "DRAFT_SUBMITTED", "draft", str(draft_id), new={"to": to, "subject": subject})
    audit("AGENT", user_id, "APPROVAL_REQUESTED", "approval", str(ap[0]), new={"draft_id": str(draft_id)})
    return {"draft_id": str(draft_id), "status": "REVIEW", "approval_id": str(ap[0])}


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        ap = conn.execute(
            "SELECT id,approval_type,payload,status FROM approvals WHERE id=%s", (str(approval_id),)
        ).fetchone()
        if not ap or ap[3] != "REVIEW":
            raise HTTPException(404, "approval not in review")
        payload = ap[2]
        conn.execute("UPDATE approvals SET status='APPROVED', decided_by=%s, decided_at=now() WHERE id=%s",
                     (user_id, str(approval_id),))
        if ap[1] == "SEND_EMAIL":
            conn.execute("UPDATE drafts SET status='APPROVED', updated_at=now() WHERE id=%s", (payload["draft_id"],))
    audit("USER", user_id, "APPROVED", "approval", str(approval_id), new=payload)
    return {"approval_id": str(approval_id), "status": "APPROVED", "note": "ready to execute (send) via D15 worker"}


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        ap = conn.execute("SELECT payload,status FROM approvals WHERE id=%s", (str(approval_id),)).fetchone()
        if not ap or ap[1] != "REVIEW":
            raise HTTPException(404, "approval not in review")
        conn.execute("UPDATE approvals SET status='REJECTED', decided_by=%s, decided_at=now() WHERE id=%s",
                     (user_id, str(approval_id),))
        conn.execute("UPDATE drafts SET status='REJECTED', updated_at=now() WHERE id=%s", (ap[0]["draft_id"],))
    audit("USER", user_id, "REJECTED", "approval", str(approval_id), new=ap[0])
    return {"approval_id": str(approval_id), "status": "REJECTED"}
