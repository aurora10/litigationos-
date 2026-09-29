"""Agent runtime (D10): task queue + LangGraph graph + enforced output format.

Graph: planner → gather context (tools) → synthesize (LLM) → format. Every step
writes an agent_events row (the activity feed) and an agent_actions row (the
tool log). Output is structured: Answer / Sources / Confidence / Open questions /
Proposed next actions.
"""
import json
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.audit import audit
from app.deps import current_user_id
from app import llm

router = APIRouter(prefix="/agent", tags=["agent"])

SYSTEM = """You are the LitigationOS case agent. Use ONLY the provided case data.
Rules:
- Do not invent facts. If context is insufficient, say so under Open questions.
- Every factual claim must end with a citation marker: [DOC:id:page] using the ids given.
- Output exactly these sections, in this order:
  Answer
  Sources
  Confidence
  Open questions
  Proposed next actions
"""


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


# ---------- tools (Appendix C, v1) ----------

def t_get_case(case_id: str):
    with _db() as conn:
        r = conn.execute(
            "SELECT id,title,description,jurisdiction,case_number,status FROM cases WHERE id=%s",
            (case_id,),
        ).fetchone()
        if not r:
            return None
        parts = conn.execute("SELECT name,role FROM parties WHERE case_id=%s", (case_id,)).fetchall()
    return {"id": str(r[0]), "title": r[1], "description": r[2],
            "jurisdiction": r[3], "case_number": r[4], "status": r[5],
            "parties": [{"name": p[0], "role": p[1]} for p in parts]}

def t_search_evidence(case_id: str, query: str, limit: int = 5):
    with _db() as conn:
        rows = conn.execute(
            "SELECT d.id, t.page_number, left(t.text_content, 400)"
            " FROM document_text t JOIN documents d ON d.id=t.document_id"
            " WHERE d.case_id=%s AND to_tsvector('simple', t.text_content) @@ plainto_tsquery('simple', %s)"
            " ORDER BY ts_rank(to_tsvector('simple', t.text_content), plainto_tsquery('simple', %s)) DESC LIMIT %s",
            (case_id, query, query, limit),
        ).fetchall()
    return [{"document_id": str(r[0]), "page": r[1], "excerpt": r[2]} for r in rows]

def t_list_issues(case_id: str):
    with _db() as conn:
        return [{"id": str(r[0]), "title": r[1], "question": r[2]}
                for r in conn.execute("SELECT id,title,question FROM issues WHERE case_id=%s", (case_id,))]

def t_list_deadlines(case_id: str):
    with _db() as conn:
        return [{"id": str(r[0]), "due_date": str(r[1]), "description": r[2], "status": r[3]}
                for r in conn.execute("SELECT id,due_date,description,status FROM deadlines WHERE case_id=%s", (case_id,))]
TOOL_MAP = {
    "get_case": t_get_case,
    "search_evidence": t_search_evidence,
    "list_issues": t_list_issues,
    "list_deadlines": t_list_deadlines,
}


# ---------- graph execution (runs synchronously in v1) ----------

def _emit(task_id: str, kind: str, message: str) -> None:
    with _db() as conn:
        conn.execute("INSERT INTO agent_events (task_id,kind,message) VALUES (%s,%s,%s)", (task_id, kind, message))

def _log_tool(task_id: str, name: str, inp: dict, out) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO agent_actions (task_id,tool_name,tool_input,result) VALUES (%s,%s,%s,%s)",
            (task_id, name, psycopg.types.json.Json(inp), psycopg.types.json.Json(out)),
        )


class AgentTaskIn(BaseModel):
    case_id: UUID
    instruction: str


@router.post("/tasks", status_code=202)
def submit_task(body: AgentTaskIn, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "INSERT INTO agent_tasks (case_id,instruction) VALUES (%s,%s) RETURNING id",
            (str(body.case_id), body.instruction),
        ).fetchone()
    tid = str(r[0])
    audit("USER", user_id, "AGENT_TASK_CREATED", "agent_task", tid, new=body.model_dump())
    _run_task(tid)  # synchronous v1; D11+ moves to worker
    return {"id": tid, "status": "COMPLETED"}


def _run_task(task_id: str) -> None:
    with _db() as conn:
        task = conn.execute("SELECT case_id,instruction FROM agent_tasks WHERE id=%s", (task_id,)).fetchone()
        case_id, instruction = str(task[0]), task[1]
        conn.execute("UPDATE agent_tasks SET status='RUNNING' WHERE id=%s", (task_id,))
    audit("AGENT", task_id, "TASK_STARTED", "agent_task", task_id)
    _emit(task_id, "reading_documents", "Reading case…")
    case = t_get_case(case_id); _log_tool(task_id, "get_case", {"case_id": case_id}, case)
    issues = t_list_issues(case_id); _log_tool(task_id, "list_issues", {"case_id": case_id}, issues)
    deadlines = t_list_deadlines(case_id); _log_tool(task_id, "list_deadlines", {"case_id": case_id}, deadlines)
    _emit(task_id, "searching_evidence", f"Searching evidence for: {instruction[:80]}…")
    evidence = t_search_evidence(case_id, instruction, limit=5); _log_tool(task_id, "search_evidence", {"q": instruction}, evidence)

    context = json.dumps({"case": case, "issues": issues, "deadlines": deadlines, "evidence": evidence}, indent=2)
    _emit(task_id, "synthesizing", "Synthesizing answer…")
    try:
        answer = llm.complete(
            prompt=f"Case context (JSON):\n{context}\n\nTask: {instruction}",
            system=SYSTEM,
        )
        status = "COMPLETED"
    except Exception as e:  # noqa: BLE001
        answer = f"LLM call failed: {type(e).__name__}: {e}"
        status = "FAILED"
    with _db() as conn:
        conn.execute("UPDATE agent_tasks SET status=%s, finished_at=now() WHERE id=%s", (status, task_id))
        conn.execute(
            "INSERT INTO agent_actions (task_id,tool_name,tool_input,result) VALUES (%s,'llm.complete',NULL,%s)",
            (task_id, psycopg.types.json.Json({"status": status, "answer": answer})),
        )
    audit("AGENT", task_id, f"TASK_{status}", "agent_task", task_id)


@router.get("/tasks/{task_id}")
def get_task(task_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        t = conn.execute(
            "SELECT id,case_id,instruction,role,status,created_at,finished_at FROM agent_tasks WHERE id=%s",
            (str(task_id),),
        ).fetchone()
        if not t:
            raise HTTPException(404, "Not found")
        llm_row = conn.execute(
            "SELECT result FROM agent_actions WHERE task_id=%s AND tool_name='llm.complete' ORDER BY created_at DESC LIMIT 1",
            (str(task_id),),
        ).fetchone()
    return {
        "id": str(t[0]), "case_id": str(t[1]), "instruction": t[2], "role": t[3], "status": t[4],
        "output": (llm_row[0].get("answer") if llm_row else None),
    }


@router.get("/tasks/{task_id}/events")
def get_events(task_id: UUID, since: int = Query(0), user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,kind,message,created_at FROM agent_events WHERE task_id=%s ORDER BY id OFFSET %s",
            (str(task_id), since),
        ).fetchall()
    return [{"id": str(r[0]), "kind": r[1], "message": r[2], "at": r[3].isoformat()} for r in rows]
