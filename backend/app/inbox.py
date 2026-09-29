"""Inbox & review queue (D06): upload → classify → propose → human approve/reject."""
import os
import re
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.audit import audit
from app.deps import current_user_id
from app import storage

router = APIRouter(prefix="/inbox", tags=["inbox"])

DOC_TYPES = [
    ("COURT_LETTER", ["vrederechter", "gerechtsdeurwaarder", "vonbet", "citaitt", "cassatie"]),
    ("LAWYER_EMAIL", ["advocaat", "lawyer", "mr."]),
    ("LEASE", ["huurovereenkomst", "lease", "huurcontract", "bail"]),
    ("INVOICE", ["factuur", "invoice", "te betalen", "total"]),
]


def _db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


def _row(r):
    return {
        "id": str(r[0]), "source_channel": r[1], "original_document_id": str(r[2]) if r[2] else None,
        "classification": r[3], "match_status": r[4],
        "matched_case_id": str(r[5]) if r[5] else None, "status": r[6],
        "created_at": r[7].isoformat(), "reviewed_at": r[8].isoformat() if r[8] else None,
    }


def classify(filename: str, text: str, mime: str) -> dict:
    lt = (filename + " " + text).lower()
    doctype = "PHOTO" if mime.startswith("image/") else next(
        (t for t, kws in DOC_TYPES if any(k in lt for k in kws)), "DOCUMENT"
    )
    dates = re.findall(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    deadlines = re.findall(r"(binnen \d+ dagen|dans les \d+ jours|within \d+ days)", lt)
    return {"document_type": doctype, "dates_found": dates[:5], "deadline_hints": deadlines[:3]}


def match_case(filename: str, text: str) -> str | None:
    with _db() as conn:
        nums = [r[0] for r in conn.execute("SELECT case_number FROM cases WHERE case_number IS NOT NULL")]
        lt = (filename + " " + text).lower()
        for n in nums:
            if n and n.lower() in lt:
                r = conn.execute("SELECT id FROM cases WHERE case_number=%s", (n,)).fetchone()
                return str(r[0]) if r else None
    return None


def _make_proposals(item_id: str, classification: dict, case_id: str | None) -> None:
    if not case_id:
        return
    with _db() as conn:
        for d in classification.get("dates_found", [])[:2]:
            conn.execute(
                "INSERT INTO inbox_proposals (inbox_item_id,proposal_type,payload) VALUES (%s,'TIMELINE_EVENT',%s)",
                (item_id, psycopg.types.json.Json({"date_guess": d, "title": f"Extracted date {d}"})),
            )
        for h in classification.get("deadline_hints", [])[:2]:
            conn.execute(
                "INSERT INTO inbox_proposals (inbox_item_id,proposal_type,payload) VALUES (%s,'DEADLINE',%s)",
                (item_id, psycopg.types.json.Json({"hint": h, "description": f"Deadline hint: {h}"})),
            )


@router.post("", status_code=201)
async def inbox_upload(file: UploadFile, user_id: str = Depends(current_user_id)):
    """Upload an un-filed item; attaches a case match where possible."""
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    filename = file.filename or "upload.bin"
    try:
        text = data.decode("utf-8", errors="ignore")[:5000]
    except Exception:
        text = ""
    storage.ensure_bucket()
    key, sha = storage.put_original(data, filename, mime)
    classification = classify(filename, text, mime)
    case_id = match_case(filename, text)
    with _db() as conn:
        if case_id:
            doc = conn.execute(
                "INSERT INTO documents (case_id,filename,mime_type,object_key,file_hash) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (case_id, filename, mime, key, sha),
            ).fetchone()
        else:
            # create a holding case so documents.case_id is satisfied; user reassigns on review
            holding = conn.execute(
                "INSERT INTO cases (title, description, status) VALUES (%s,'auto-created holding case for unmatched inbox item','OPEN') RETURNING id",
                ("(inbox) " + filename,),
            ).fetchone()
            doc = conn.execute(
                "INSERT INTO documents (case_id,filename,mime_type,object_key,file_hash) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (str(holding[0]), filename, mime, key, sha),
            ).fetchone()
        item = conn.execute(
            "INSERT INTO inbox_items (source_channel,original_document_id,classification,match_status,matched_case_id,status)"
            " VALUES ('UPLOAD',%s,%s,%s,%s,'REVIEW_REQUIRED')"
            " RETURNING id,source_channel,original_document_id,classification,match_status,matched_case_id,status,created_at,reviewed_at",
            (str(doc[0]), psycopg.types.json.Json(classification),
             'MATCHED' if case_id else 'CASE_MATCH_NEEDED', case_id),
        ).fetchone()
    _make_proposals(str(item[0]), classification, case_id)
    out = _row(item)
    audit("USER", user_id, "INBOX_UPLOAD", "inbox_item", out["id"], new={"filename": filename, "classification": classification})
    return out


@router.get("")
def list_inbox(status: str | None = None, user_id: str = Depends(current_user_id)):
    q = "SELECT id,source_channel,original_document_id,classification,match_status,matched_case_id,status,created_at,reviewed_at FROM inbox_items"
    params: list = []
    if status:
        q += " WHERE status=%s"; params.append(status)
    q += " ORDER BY created_at DESC"
    with _db() as conn:
        return [_row(r) for r in conn.execute(q, params).fetchall()]


@router.get("/{item_id}")
def get_item(item_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "SELECT id,source_channel,original_document_id,classification,match_status,matched_case_id,status,created_at,reviewed_at"
            " FROM inbox_items WHERE id=%s", (str(item_id),)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Not found")
        proposals = [
            {"id": str(p[0]), "proposal_type": p[1], "payload": p[2], "status": p[3]}
            for p in conn.execute(
                "SELECT id,proposal_type,payload,status FROM inbox_proposals WHERE inbox_item_id=%s", (str(item_id),)
            )
        ]
    return {**_row(r), "proposals": proposals}


@router.post("/{item_id}/approve")
def approve(item_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        item = conn.execute(
            "UPDATE inbox_items SET status='APPROVED', reviewed_at=now() WHERE id=%s"
            " RETURNING matched_case_id, original_document_id", (str(item_id),)
        ).fetchone()
        if not item:
            raise HTTPException(404, "Not found")
        case_id, doc_id = item
        for p in conn.execute(
            "SELECT proposal_type, payload FROM inbox_proposals WHERE inbox_item_id=%s AND status='PROPOSED'",
            (str(item_id),),
        ).fetchall():
            ptype, payload = p[0], p[1]
            if ptype == "TIMELINE_EVENT" and case_id:
                conn.execute(
                    "INSERT INTO timeline_events (case_id,event_date,title,description,verification_status)"
                    " VALUES (%s, now(), %s, %s, 'PROPOSED')",
                    (case_id, payload.get("title", "event"), str(payload)),
                )
            elif ptype == "DEADLINE" and case_id:
                conn.execute(
                    "INSERT INTO deadlines (case_id,due_date,description,status) VALUES (%s, now() + interval '30 days', %s, 'PROPOSED')",
                    (case_id, payload.get("description", "deadline")),
                )
            elif ptype == "EVIDENCE" and case_id:
                conn.execute(
                    "INSERT INTO evidence (case_id,title,evidence_type,source_document_id) VALUES (%s,%s,'DOCUMENT',%s)",
                    (case_id, payload.get("title", "evidence"), doc_id),
                )
        conn.execute("UPDATE inbox_proposals SET status='ACCEPTED' WHERE inbox_item_id=%s AND status='PROPOSED'", (str(item_id),))
    audit("USER", user_id, "INBOX_APPROVED", "inbox_item", str(item_id))
    return {"id": str(item_id), "status": "APPROVED"}


@router.post("/{item_id}/reject")
def reject(item_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "UPDATE inbox_items SET status='REJECTED', reviewed_at=now() WHERE id=%s RETURNING id", (str(item_id),)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Not found")
    audit("USER", user_id, "INBOX_REJECTED", "inbox_item", str(item_id))
    return {"id": str(item_id), "status": "REJECTED"}
