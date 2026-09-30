"""Email ingestion via n8n webhook (D13). n8n forwards a normalized email; we dedupe
(by provider_message_id), thread it, and drop it into the Inbox for review."""
import os

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.audit import audit

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "dev-webhook-token")


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


class EmailIn(BaseModel):
    provider_message_id: str
    thread_id: str | None = None
    sender: str | None = None
    recipients: list[str] = []
    subject: str = ""
    body: str = ""
    received_at: str | None = None  # ISO


# Check auth FIRST so even an invalid body without a token is 401 (not 422).
async def _authed_body(request: Request) -> EmailIn:
    if request.headers.get("x-webhook-token") != WEBHOOK_TOKEN:
        raise HTTPException(401, "invalid webhook token")
    try:
        return EmailIn(**(await request.json()))
    except ValidationError as e:
        raise HTTPException(422, e.errors())


@router.post("/email", status_code=202)
async def email_webhook(request: Request):
    body = await _authed_body(request)
    with _db() as conn:
        existing = conn.execute(
            "SELECT communication_id FROM emails WHERE provider_message_id=%s",
            (body.provider_message_id,),
        ).fetchone()
        if existing:
            return {"status": "DUPLICATE", "communication_id": str(existing[0])}

        comm = conn.execute(
            "INSERT INTO communications (case_id,direction,channel,subject) VALUES"
            " ((SELECT id FROM cases ORDER BY created_at DESC LIMIT 1),'IN','EMAIL',%s) RETURNING id, case_id",
            (body.subject,),
        ).fetchone()
        conn.execute(
            "INSERT INTO emails (communication_id,provider_message_id,thread_id,sender,recipients,subject,raw_body,received_at)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(comm[0]), body.provider_message_id, body.thread_id, body.sender,
             psycopg.types.json.Json(body.recipients), body.subject, body.body, body.received_at),
        )
        conn.execute(
            "INSERT INTO inbox_items (source_channel,classification,status)"
            " VALUES ('EMAIL', %s, 'REVIEW_REQUIRED')",
            (psycopg.types.json.Json({
                "document_type": "EMAIL",
                "sender": body.sender, "subject": body.subject,
                "thread_id": body.thread_id,
            }),),
        )
    audit("SYSTEM", None, "EMAIL_RECEIVED", "communication", str(comm[0]),
          new={"subject": body.subject, "from": body.sender})
    return {"status": "RECEIVED", "communication_id": str(comm[0])}


@router.post("/outlook", status_code=202)
async def outlook_webhook(request: Request):
    return await email_webhook(request)
