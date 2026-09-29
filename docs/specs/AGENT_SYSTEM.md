# AGENT_SYSTEM.md — Agent System Specification (Appendix C)

Version 1.0

## Purpose
The agent helps the user understand, organize, analyze and act on information stored in a Case. **The agent is not a chatbot — it is an operator working on a structured case database.**

## Design goals
Must: understand case context · retrieve evidence · identify contradictions · build chronology · find missing evidence · perform legal research (Belgian sources) · prepare drafts · monitor deadlines.
Must not: invent facts · silently modify evidence · perform external actions without approval.

## Architecture
User → Task → Planner → Tool Selection → Execution → Review → Result.

## Roles (one agent UI; internal logical roles)
1. **Case Manager** — overall case understanding, task planning/routing ("summarize case", "next actions").
2. **Evidence Agent** — supporting/opposing evidence, evidence gaps ("what supports claim A? what's missing?").
3. **Timeline Agent** — chronology, date extraction, contradiction detection.
4. **Research Agent** — Belgian legislation/jurisprudence/commentary; every proposition normalized: PROPOSITION → SOURCE → EXACT ARTICLE/PARAGRAPH → CASE → RELEVANCE → CONFIDENCE.
5. **Adversarial Agent** — "assume you represent the opposing party; attack my case": weaknesses, contradictory evidence, adverse jurisprudence, procedural problems, missing evidence; then a defense pass. Iterative, both passes logged. (First-class, not optional.)
6. **Drafting Agent** — emails, letters, lawyer briefings, hearing-prep notes.

## Tool system (agents interact with the world only through tools)
- Case: `search_case()` · `get_case()` · `list_issues()` · `list_deadlines()`
- Evidence: `search_evidence()` · `get_document()` · `get_transcript()` · `get_source_excerpt()`
- Research: `search_legislation()` · `search_jurisprudence()` · `get_legal_source()`
- Drafting: `create_draft()` · `update_draft()` · `submit_for_review()`
- Action (permission-gated): `request_approval()` · `send_email()` · `create_calendar_event()`

## Approval gates
Send email · file document · update verified facts. Flow: DRAFT → REVIEW → APPROVE → EXECUTE.

## Activity feed
Never expose chain-of-thought. Show: "Reading documents… / Searching evidence… / Found contradiction… / Preparing draft… / Waiting for approval…".

## Memory
Source of memory is the **case database**, not conversation history. The agent always retrieves fresh context.

## Task state
QUEUED → RUNNING → WAITING_APPROVAL → COMPLETED | FAILED.

## Output format (enforced)
Answer · Sources · Confidence · Open Questions · Proposed Next Actions.

## Citation-verification gate (D12)
No legal proposition ships without: court · date · case number · ECLI · source (JuPortal/Justel/Lex.be) · URL · exact passage · why relevant. The verifier re-fetches the source and compares the passage; result VERIFIED / UNVERIFIABLE / MISMATCH. Unverified citations are displayed as such and cannot be approved.
