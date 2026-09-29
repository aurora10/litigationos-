"""Case management (D03): CRUD + parties, soft-archive, audit on every mutation."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id

router = APIRouter(prefix="/cases", tags=["cases"])


def _db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


def _row_to_case(r):
    return {
        "id": str(r[0]), "title": r[1], "description": r[2], "jurisdiction": r[3],
        "case_number": r[4], "status": r[5], "court": r[6],
        "created_at": r[7].isoformat(), "updated_at": r[8].isoformat(),
    }


class CaseIn(BaseModel):
    title: str
    description: str | None = None
    jurisdiction: str | None = None
    case_number: str | None = None
    court: str | None = None


class CasePatch(BaseModel):
    title: str | None = None
    description: str | None = None
    jurisdiction: str | None = None
    case_number: str | None = None
    court: str | None = None


@router.get("")
def list_cases(user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,title,description,jurisdiction,case_number,status,court,created_at,updated_at"
            " FROM cases ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_case(r) for r in rows]


@router.post("", status_code=201)
def create_case(body: CaseIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        row = conn.execute(
            "INSERT INTO cases (title,description,jurisdiction,case_number,court) VALUES (%s,%s,%s,%s,%s)"
            " RETURNING id,title,description,jurisdiction,case_number,status,court,created_at,updated_at",
            (body.title, body.description, body.jurisdiction, body.case_number, body.court),
        ).fetchone()
    case = _row_to_case(row)
    audit("USER", user_id, "INSERT", "case", case["id"], new=case)
    return case


@router.get("/{case_id}")
def get_case(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "SELECT id,title,description,jurisdiction,case_number,status,court,created_at,updated_at"
            " FROM cases WHERE id=%s", (str(case_id),)
        ).fetchone()
        if not r:
            raise HTTPException(404, "Case not found")
        parties = [
            {"id": str(p[0]), "name": p[1], "role": p[2], "email": p[3], "phone": p[4]}
            for p in conn.execute("SELECT id,name,role,email,phone FROM parties WHERE case_id=%s", (str(case_id),))
        ]
    return {**_row_to_case(r), "parties": parties}


@router.patch("/{case_id}")
def update_case(case_id: UUID, body: CasePatch, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        old = conn.execute(
            "SELECT id,title,description,jurisdiction,case_number,status,court,created_at,updated_at FROM cases WHERE id=%s",
            (str(case_id),),
        ).fetchone()
        if not old:
            raise HTTPException(404, "Case not found")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if fields:
            sets = ", ".join(f"{k}=%s" for k in fields)
            conn.execute(
                f"UPDATE cases SET {sets}, updated_at=now() WHERE id=%s",
                (*fields.values(), str(case_id)),
            )
        new = conn.execute(
            "SELECT id,title,description,jurisdiction,case_number,status,court,created_at,updated_at FROM cases WHERE id=%s",
            (str(case_id),),
        ).fetchone()
    audit("USER", user_id, "UPDATE", "case", str(case_id), old=_row_to_case(old), new=_row_to_case(new))
    return _row_to_case(new)


@router.delete("/{case_id}")
def archive_case(case_id: UUID, user_id: str = Depends(current_user_id)):
    """Soft-archive only — a case is never hard-deleted."""
    with _db() as conn:
        r = conn.execute(
            "UPDATE cases SET status='ARCHIVED', updated_at=now() WHERE id=%s RETURNING id", (str(case_id),)
        ).fetchone()
    if not r:
        raise HTTPException(404, "Case not found")
    audit("USER", user_id, "ARCHIVE", "case", str(case_id))
    return {"id": str(case_id), "status": "ARCHIVED"}


class PartyIn(BaseModel):
    name: str
    role: str
    email: str | None = None
    phone: str | None = None


@router.get("/{case_id}/parties")
def list_parties(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,name,role,email,phone FROM parties WHERE case_id=%s", (str(case_id),)
        ).fetchall()
    return [{"id": str(r[0]), "name": r[1], "role": r[2], "email": r[3], "phone": r[4]} for r in rows]


@router.post("/{case_id}/parties", status_code=201)
def add_party(case_id: UUID, body: PartyIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "INSERT INTO parties (case_id,name,role,email,phone) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (str(case_id), body.name, body.role, body.email, body.phone),
        ).fetchone()
    party = {"id": str(r[0]), **body.model_dump()}
    audit("USER", user_id, "INSERT", "party", party["id"], new={**party, "case_id": str(case_id)})
    return party
