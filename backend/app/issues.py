"""Issues, arguments, claims (D08) — the case reasoning structure."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id

router = APIRouter(tags=["issues"])


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


class IssueIn(BaseModel):
    title: str
    question: str


class ArgumentIn(BaseModel):
    argument_type: str  # SUPPORTING | OPPOSING | COUNTERARGUMENT
    statement: str


class ClaimIn(BaseModel):
    statement: str
    evidence_document_id: str | None = None
    evidence_page: int | None = None


@router.get("/cases/{case_id}/issues")
def list_issues(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        issues = conn.execute(
            "SELECT id,case_id,title,question,status FROM issues WHERE case_id=%s ORDER BY created_at",
            (str(case_id),),
        ).fetchall()
        out = []
        for i in issues:
            iid = str(i[0])
            args = [
                {"id": str(a[0]), "argument_type": a[1], "statement": a[2]}
                for a in conn.execute(
                    "SELECT id,argument_type,statement FROM arguments WHERE issue_id=%s", (iid,)
                )
            ]
            claims = []
            for cl in conn.execute(
                "SELECT id,statement,verification_status FROM claims WHERE issue_id=%s", (iid,)
            ):
                cid = str(cl[0])
                srcs = conn.execute(
                    "SELECT p.source_document_id,p.page_number FROM claim_sources cs"
                    " JOIN provenance p ON p.id=cs.provenance_id WHERE cs.claim_id=%s", (cid,)
                ).fetchall()
                claims.append({
                    "id": cid, "statement": cl[1], "verification_status": cl[2],
                    "sources": [{"document_id": str(s[0]), "page": s[1]} for s in srcs],
                })
            supporting = [a for a in args if a["argument_type"] == "SUPPORTING"]
            opposing = [a for a in args if a["argument_type"] == "OPPOSING"]
            missing = []
            if not supporting: missing.append("no supporting evidence yet")
            if not opposing: missing.append("no opposing evidence captured — run adversarial pass?")
            unsupported = [c["statement"] for c in claims if not c["sources"]]
            missing += [f"claim without source: '{s}'" for s in unsupported]
            out.append({
                "id": iid, "case_id": str(i[1]), "title": i[2], "question": i[3], "status": i[4],
                "arguments": args, "claims": claims, "missing": missing,
            })
        return out


@router.post("/cases/{case_id}/issues", status_code=201)
def create_issue(case_id: UUID, body: IssueIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "INSERT INTO issues (case_id,title,question) VALUES (%s,%s,%s) RETURNING id",
            (str(case_id), body.title, body.question),
        ).fetchone()
    audit("USER", user_id, "INSERT", "issue", str(r[0]), new={"case_id": str(case_id), **body.model_dump()})
    return {"id": str(r[0]), **body.model_dump(), "status": "OPEN"}


@router.post("/issues/{issue_id}/arguments", status_code=201)
def add_argument(issue_id: UUID, body: ArgumentIn, user_id: str = Depends(current_user_id)):
    if body.argument_type not in ("SUPPORTING", "OPPOSING", "COUNTERARGUMENT"):
        raise HTTPException(400, "argument_type must be SUPPORTING/OPPOSING/COUNTERARGUMENT")
    with _db() as conn:
        r = conn.execute(
            "INSERT INTO arguments (issue_id,argument_type,statement) VALUES (%s,%s,%s) RETURNING id",
            (str(issue_id), body.argument_type, body.statement),
        ).fetchone()
    audit("USER", user_id, "INSERT", "argument", str(r[0]), new={"issue_id": str(issue_id), **body.model_dump()})
    return {"id": str(r[0]), **body.model_dump()}


@router.post("/issues/{issue_id}/claims", status_code=201)
def add_claim(issue_id: UUID, body: ClaimIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        case_id = conn.execute("SELECT case_id FROM issues WHERE id=%s", (str(issue_id),)).fetchone()
        if not case_id:
            raise HTTPException(404, "Issue not found")
        cl = conn.execute(
            "INSERT INTO claims (case_id,issue_id,statement) VALUES (%s,%s,%s) RETURNING id",
            (str(case_id[0]), str(issue_id), body.statement),
        ).fetchone()
        if body.evidence_document_id:
            p = conn.execute(
                "INSERT INTO provenance (source_document_id,page_number) VALUES (%s,%s) RETURNING id",
                (body.evidence_document_id, body.evidence_page),
            ).fetchone()
            conn.execute(
                "INSERT INTO claim_sources (claim_id,provenance_id) VALUES (%s,%s)",
                (str(cl[0]), str(p[0])),
            )
    audit("USER", user_id, "INSERT", "claim", str(cl[0]), new={"issue_id": str(issue_id), **body.model_dump()})
    return {"id": str(cl[0]), **body.model_dump()}
