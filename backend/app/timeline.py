"""Timeline with provenance (D07)."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id

router = APIRouter(tags=["timeline"])


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


def _row(r):
    return {
        "id": str(r[0]), "case_id": str(r[1]), "event_date": r[2].isoformat(),
        "title": r[3], "description": r[4], "verification_status": r[5],
    }


class EventIn(BaseModel):
    event_date: str  # ISO
    title: str
    description: str | None = None
    source_document_id: str | None = None
    page_number: int | None = None


@router.get("/cases/{case_id}/timeline")
def list_timeline(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        evs = conn.execute(
            "SELECT id,case_id,event_date,title,description,verification_status"
            " FROM timeline_events WHERE case_id=%s ORDER BY event_date", (str(case_id),)
        ).fetchall()
        out = []
        for e in evs:
            srcs = conn.execute(
                "SELECT p.id,p.source_document_id,p.page_number FROM timeline_sources t"
                " JOIN provenance p ON p.id=t.provenance_id WHERE t.event_id=%s",
                (str(e[0]),),
            ).fetchall()
            out.append({**_row(e), "sources": [
                {"provenance_id": str(s[0]), "document_id": str(s[1]), "page": s[2]} for s in srcs
            ]})
        return out


@router.post("/cases/{case_id}/timeline", status_code=201)
def add_event(case_id: UUID, body: EventIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        ev = conn.execute(
            "INSERT INTO timeline_events (case_id,event_date,title,description,verification_status)"
            " VALUES (%s,%s,%s,%s,'PROPOSED')"
            " RETURNING id,case_id,event_date,title,description,verification_status",
            (str(case_id), body.event_date, body.title, body.description),
        ).fetchone()
        if body.source_document_id:
            prov = conn.execute(
                "INSERT INTO provenance (source_document_id,page_number) VALUES (%s,%s) RETURNING id",
                (body.source_document_id, body.page_number),
            ).fetchone()
            conn.execute(
                "INSERT INTO timeline_sources (event_id,provenance_id) VALUES (%s,%s)",
                (str(ev[0]), str(prov[0])),
            )
    out = _row(ev)
    audit("USER", user_id, "INSERT", "timeline_event", out["id"], new={"case_id": str(case_id), **body.model_dump()})
    return out


@router.patch("/timeline/{event_id}")
def review_event(event_id: UUID, action: dict, user_id: str = Depends(current_user_id)):
    """action = {'status':'APPROVED'|'REJECTED'}"""
    status = action.get("status")
    if status not in ("APPROVED", "REJECTED"):
        raise HTTPException(400, "status must be APPROVED or REJECTED")
    with _db() as conn:
        r = conn.execute(
            "UPDATE timeline_events SET verification_status=%s WHERE id=%s RETURNING id",
            (status, str(event_id)),
        ).fetchone()
        if not r:
            raise HTTPException(404, "Not found")
    audit("USER", user_id, f"TIMELINE_{status}", "timeline_event", str(event_id))
    return {"id": str(event_id), "verification_status": status}
