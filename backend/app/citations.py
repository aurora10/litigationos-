"""Citation verification gate (D12): no legal claim without a resolvable source.

Flow:
1) ask LLM for the claim in citable form
2) persist legal_source + legal_citation
3) fetch the source's URL and compare the passage
4) verdict VERIFIED / MISMATCH / UNVERIFIABLE, with the check result stored
"""
import os
import re
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id
from app import research_tools as rt

router = APIRouter(tags=["citations"])


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


class ParseIn(BaseModel):
    text: str  # free-form citation as produced by an agent, e.g. "Cass. 14 nov 2019, ECLI:BE:CASS:2019:ARR.2019112804.1"


def extract_citation(text: str) -> dict | None:
    """Very small parser — ECLI if present wins; else ELI URL; else CELEX."""
    ecli = re.search(r"ECLI:BE:[A-Z0-9]+:\d{4}:[A-Z0-9.]+", text)
    if ecli:
        return {"kind": "ECLI", "citation": ecli.group(0)}
    eli = re.search(r"https://www\.ejustice\.just\.fgov\.be/eli/[a-z0-9/:.]+/justel", text, re.I)
    if eli:
        return {"kind": "ELI", "citation": eli.group(0)}
    celex = re.search(r"3\d{5}[A-Z]\d+", text)  # e.g. 31998R0442 pattern
    if celex:
        return {"kind": "CELEX", "citation": celex.group(0)}
    return None


@router.post("/citations/verify", status_code=201)
def create_and_verify(body: ParseIn, case_id: UUID, passage: str, relevance: str = "",
                      task_id: UUID | None = None, user_id: str = Depends(current_user_id)):
    step1 = extract_citation(body.text)
    if not step1:
        raise HTTPException(400, "No ECLI/ELI/CELEX found in citation text")
    key = step1["citation"]
    kind = step1["kind"]
    # fetch/resolve actual source url
    url = None
    html = None
    if kind == "ECLI":
        r = rt.juportal_get_by_ecli(key)
        if r:
            url = r["url"]; html = rt._get(url)
    elif kind == "ELI":
        url = key; html = rt._get(url)
    elif kind == "CELEX":
        r = rt.eurlex_get_by_celex(key)
        if r:
            url = r["url"]; html = rt._get(url)

    # verification verdict
    if html is None:
        verdict, note = "UNVERIFIABLE", "could not resolve source url"
    else:
        plain = re.sub(r"\s+", " ", html.lower())
        passage_norm = re.sub(r"\s+", " ", passage.strip().lower())
        first_40 = passage_norm[:80]
        verdict, note = ("VERIFIED", "passage located in source") if first_40 and first_40 in plain else ("MISMATCH", "passage not found in fetched source")

    with _db() as conn:
        src = conn.execute(
            "INSERT INTO legal_sources (source_type,citation,url,content) VALUES (%s,%s,%s,%s)"
            " ON CONFLICT (citation) DO UPDATE SET url=EXCLUDED.url, content=EXCLUDED.content"
            " RETURNING id",
            ("CASE_LAW" if kind == "ECLI" else "LEGISLATION" if kind == "ELI" else "REGULATION", key, url, html[:20000] if html else None),
        ).fetchone()
        cit = conn.execute(
            "INSERT INTO legal_citations (case_id,task_id,legal_source_id,exact_passage,relevance,verification,verification_note,verified_at)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s, CASE WHEN %s='VERIFIED' THEN now() END) RETURNING id",
            (str(case_id), str(task_id) if task_id else None, str(src[0]), passage, relevance, verdict, note, verdict),
        ).fetchone()
    audit("USER", user_id, "CITATION_CHECK", "legal_citation", str(cit[0]),
          new={"citation": key, "verdict": verdict})
    return {"citation": key, "verification": verdict, "note": note, "legal_citation_id": str(cit[0])}


@router.get("/cases/{case_id}/citations")
def list_citations(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT c.id, s.citation, s.url, c.exact_passage, c.verification, c.verification_note, c.relevance"
            " FROM legal_citations c JOIN legal_sources s ON s.id=c.legal_source_id WHERE c.case_id=%s"
            " ORDER BY c.created_at DESC", (str(case_id),)
        ).fetchall()
    return [{
        "id": str(r[0]), "citation": r[1], "url": r[2], "exact_passage": r[3],
        "verification": r[4], "note": r[5], "relevance": r[6],
    } for r in rows]
