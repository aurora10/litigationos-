"""Intake agent (D21) — drives a one-question-at-a-time interview until the case is research-ready."""
from __future__ import annotations
import json
import os
from typing import Any

from app import llm


INTAKE_SYSTEM = """You are LitigationOS's intake interviewer. Your job is to gather the minimum facts needed to run a legal analysis.

RULES:
1. Ask EXACTLY ONE question at a time.
2. Questions must be specific, in Dutch, and directly fill a gap in the case data (parties, dates, documents, claims, amounts, jurisdiction).
3. If the user answers, acknowledge briefly and ask the NEXT question.
4. When you have enough to run the analysis, output exactly:
   READY_FOR_ANALYSIS
   <summary of what you collected>
5. Never give legal advice. Never output the analysis yourself.

CURRENT CASE CONTEXT:
{context}

QUESTIONS ALREADY ASKED:
{asked}

ANSWERS RECEIVED:
{answers}

MISSING CATEGORIES (check what's still needed):
- parties: names, roles, contact
- dates: key events (contract, incident, notice, deadline)
- documents: what scans/photos/emails exist
- amounts: claimed damages, rent, deposit
- jurisdiction: which court / applicable law
- legal basis: contract, tort, statutory right

OUTPUT FORMAT (always exactly one of):
Q: <your single question in Dutch>
READY_FOR_ANALYSIS
<bullet summary of what you collected>"""


def build_intake_prompt(context: dict, asked: list[str], answers: list[str]) -> str:
    ctx = json.dumps(context, ensure_ascii=False, indent=2)
    return INTAKE_SYSTEM.format(
        context=ctx,
        asked="\n- ".join(asked) if asked else "(none)",
        answers="\n- ".join(answers) if answers else "(none)",
    )


def run_intake_turn(instruction: str, context: dict, asked: list[str], answers: list[str]) -> str:
    """Returns the agent's next output (a question or READY_FOR_ANALYSIS)."""
    prompt = build_intake_prompt(context, asked, answers)
    prompt += f"\n\nUser's latest input: {instruction}"
    return llm.complete(prompt=prompt, system="")


def extract_intake_context(case_id: str) -> dict:
    """Minimal context from DB — reused by the intake agent."""
    import os
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        case = conn.execute("SELECT id,title,case_number,jurisdiction,description FROM cases WHERE id=%s", (case_id,)).fetchone()
        parties = [{"name": p[0], "role": p[1]} for p in conn.execute("SELECT name,role FROM parties WHERE case_id=%s", (case_id,))]
        issues = [{"title": i[0], "question": i[1]} for i in conn.execute("SELECT title,question FROM issues WHERE case_id=%s", (case_id,))]
        deadlines = [{"due_date": str(d[0]), "description": d[1]} for d in conn.execute("SELECT due_date,description FROM deadlines WHERE case_id=%s", (case_id,))]
        docs = [{"filename": d[0], "status": d[1]} for d in conn.execute("SELECT filename,processing_status FROM documents WHERE case_id=%s", (case_id,))]
    return {"case": case, "parties": parties, "issues": issues, "deadlines": deadlines, "documents": docs}