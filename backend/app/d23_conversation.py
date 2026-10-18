"""Conversational iteration (D23) - handle follow-ups on drafts, evidence additions, and rewrites."""
import json
from app import llm
from app import intake

D23_SYSTEM = """You are LitigationOS's conversational drafting assistant. The user wants to modify or extend an existing draft, or add new evidence to the case.

RULES:
1. You have access to the current draft, the case context, and any new evidence the user mentions.
2. If the user provides NEW EVIDENCE (scan, email, document), acknowledge it and confirm it will be added to the case.
3. If the user wants a REWRITE (shorter, different tone, add evidence), produce the NEW VERSION of the draft.
4. If the user asks a QUESTION, answer it based on case context.
5. Output format:
   - If producing a new draft version: output the full new draft text
   - If acknowledging new evidence: "EVIDENCE_ADDED: <description>"
   - If answering a question: answer directly

CURRENT DRAFT ({draft_kind}):
{draft_body}

CASE CONTEXT:
{case_context}

NEW EVIDENCE MENTIONED:
{new_evidence}

USER INSTRUCTION:
{instruction}"""


def build_d23_prompt(draft_kind: str, draft_body: str, case_context: dict, new_evidence: str, instruction: str) -> str:
    ctx = json.dumps(case_context, ensure_ascii=False, indent=2)
    return D23_SYSTEM.format(
        draft_kind=draft_kind,
        draft_body=draft_body or "(empty)",
        case_context=json.dumps(case_context, ensure_ascii=False, indent=2),
        new_evidence=new_evidence or "(none)",
        instruction=instruction,
    )


def run_d23_turn(draft_id: str, draft_kind: str, draft_body: str, case_context: dict, new_evidence: str, instruction: str) -> str:
    """Process a conversational turn on a draft."""
    prompt = build_d23_prompt(draft_kind, draft_body, case_context, new_evidence, instruction)
    return llm.complete(prompt=prompt, system="")


def extract_case_context(case_id: str) -> dict:
    import os
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        case = conn.execute("SELECT id,title,case_number,jurisdiction,description FROM cases WHERE id=%s", (case_id,)).fetchone()
        parties = [{"name": p[0], "role": p[1]} for p in conn.execute("SELECT name,role FROM parties WHERE case_id=%s", (case_id,))]
        issues = [{"title": i[0], "question": i[1]} for i in conn.execute("SELECT title,question FROM issues WHERE case_id=%s", (case_id,))]
        deadlines = [{"due_date": str(d[0]), "description": d[1]} for d in conn.execute("SELECT due_date,description FROM deadlines WHERE case_id=%s", (case_id,))]
        docs = [{"filename": d[0], "status": d[1]} for d in conn.execute("SELECT filename,processing_status FROM documents WHERE case_id=%s", (case_id,))]
    return {"case": case, "parties": parties, "issues": issues, "deadlines": deadlines, "documents": docs}