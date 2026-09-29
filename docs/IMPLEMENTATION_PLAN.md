# IMPLEMENTATION_PLAN.md

**LitigationOS — Master Implementation Plan. Version 1.0.**
This is the authoritative build contract. If code and this document disagree, the code is wrong until this document is amended per §0.4.

---

## 0. How to use this document

### 0.1 Structure
Four levels: **Phase → Deliverable (D01…D18) → Task (D05-T02) → Acceptance.** Never reference work by name in status updates — always by ID.

### 0.2 Status table (update after every verified deliverable)

| ID | Deliverable | Status | Verified by | Date |
|----|---|---|---|---|
| D01 | Infrastructure & dev environment | IN PROGRESS (awaiting human verification) | code+static checks verified on dev VPS | 2026-09-29 |
| D02 | Authentication (single-user) | NOT STARTED | | |
| D03 | Case management (CRUD + Parties) | NOT STARTED | | |
| D04 | Document storage (MinIO, hashing, originals) | NOT STARTED | | |
| D05 | OCR pipeline | NOT STARTED | | |
| D06 | Inbox & classification + review queue | NOT STARTED | | |
| D07 | Timeline + provenance | NOT STARTED | | |
| D08 | Evidence, Claims & Issue tree | NOT STARTED | | |
| D09 | Search (full-text + semantic) | NOT STARTED | | |
| D10 | Agent runtime core (LangGraph + tools + activity feed) | NOT STARTED | | |
| D11 | Agent roles (incl. Adversarial loop) | NOT STARTED | | |
| D12 | Citation-verification gate | NOT STARTED | | |
| D13 | Email ingestion via n8n | NOT STARTED | | |
| D14 | Drafting & approval workflow | NOT STARTED | | |
| D15 | Deadlines & dashboard | NOT STARTED | | |
| D16 | Audit & approvals enforcement | NOT STARTED | | |
| D17 | Security hardening & backup | NOT STARTED | | |
| D18 | Production deployment (Belgium go-live) | NOT STARTED | | |

Statuses: `NOT STARTED | IN PROGRESS | BLOCKED (reason) | DONE`. A deliverable is DONE only when its Acceptance block has been executed with real output pasted into its **Verification record**, and this table row updated.

### 0.3 Verification ritual (developer + reviewer)
- Developer: implement one deliverable → run acceptance commands honestly → paste **actual** output under "Verification record" → mark DONE → commit `D05: OCR pipeline (acceptance passed)` → push.
- Reviewer (local): `git pull` → run the commands under "Human verification" → confirm → optionally flip status table's "Verified by" to self.
- Never mark DONE from intent. Failed acceptance ⇒ BLOCKED with reason ⇒ re-plan that deliverable in §0.4.

### 0.4 Change control
Appendices A (schema) and B (API) are **frozen contracts for the current milestone**. Changes are allowed but must be recorded:
1. Edit the appendix row/table.
2. Add a line to **Changelog** (§11) describing what changed and why.
3. Any task referencing the change must note the revision date.

### 0.5 Exit criteria per phase
- **P1 (D01–D03):** stack boots; a case can be created/read/updated/listed via API with auth; events audited.
- **P2 (D04–D06):** a scanned PDF uploaded → OCR'd → searchable; an incoming item lands in Inbox and can be reviewed/approved.
- **P3 (D07–D09):** asked "when was the exit inspection?", the system returns an answer with a page-level citation; a claim can be linked to evidence provenance; full-text + semantic search return the same document.
- **P4 (D10–D12):** "summarize my case" produces an answer where **every factual and legal claim carries a verified citation**; "attack my case" runs the adversarial loop.
- **P5 (D13–D15):** email arrives → n8n → Inbox → approve → attached to case; "email lawyer an update" produces a draft that sends **only after approval**; deadlines appear on the dashboard.
- **P6 (D16–D18):** audit trail proves approvals; backups restore cleanly; system runs on the target host.

---

## 1. Project overview

LitigationOS is a **personal litigation agent** for Belgian disputes (first case: deposit dispute, Vrederechter). It is not a chatbot and not a lawyer replacement. The agent maintains the case workspace (facts, documents, law, correspondence, filings, strategy), produces lawyer-meeting briefs, and maps claims to evidence and gaps.

Bellwether capability — asked **"prepare for my meeting with the lawyer"**, the system produces: (1) what happened, (2) what is disputed, (3) evidence for us, (4) evidence for the other side, (5) applicable legislation, (6) relevant Belgian judgments (ECLI-cited), (7) arguments, (8) weak points, (9) questions for the lawyer, (10) deadlines, (11) documents still to obtain, (12) draft instructions.

**Non-goals (v1):** no legal advice, no autonomous filing/communication with opposing parties, no multi-user law-firm mode (single-user v1; multi-user deferred behind the existing `users` schema).

**Belgian specificity:** JuPortal, Justel, Lex.be, EUR-Lex as legal sources; e-Deposit recognized but filing is manual-only in v1. See `docs/specs/BELGIAN_SOURCES.md`.

---

## 2. Stack & repo layout

See `docs/specs/ARCHITECTURE.md` for the full diagram and ADRs. TL;DR: Next.js + FastAPI + LangGraph + PostgreSQL(pgvector) + MinIO + Redis + n8n, all in docker-compose. Repo layout as in README. Configuration exclusively via `.env` (see `.env.example`); secrets never committed.

---

## 3. Phase 1 — Foundation

### D01 — Infrastructure & dev environment
**Goal:** one command boots the whole local platform. **Depends on:** —

**Tasks**
- D01-T01 `docker-compose.yml`: services `db` (postgres:17 + pgvector + pg_trgm), `minio`, `redis`, `backend` (FastAPI), `frontend` (Next.js), `worker`, `n8n`; named volumes `pgdata`, `miniodata`.
- D01-T02 `.env.example` documenting every variable.
- D01-T03 `Makefile`/`scripts/`: `up`, `down`, `logs`, `psql`, `test`.
- D01-T04 Backend health endpoint `GET /health` → `{"status":"ok","db":"ok","minio":"ok","redis":"ok"}`.
- D01-T05 Frontend dev server reachable on `:3000`.

**Acceptance**
```bash
cp .env.example .env && docker compose up -d
./scripts/verify_d01.sh
# expect: all services healthy; curl localhost:8000/health → 200 {"status":"ok",...}
#         curl localhost:3000 → 200
```

**Verification record:** dev VPS has no Docker daemon, so full compose boot runs on the reviewer's machine (Human verification). Verified here instead:
- `docker-compose.yml` parses, all 7 services defined (db/redis/minio/backend/worker/frontend/n8n)
- backend imports cleanly; `GET /health` via FastAPI TestClient → `200 {'status':'degraded','db':'error','redis':'error','minio':'error'}` (expected with services down; connectivity checks wired)
- `worker.py` AST parses; `verify_d01.sh` `bash -n` clean; frontend `npx tsc --noEmit` clean

**Human verification (reviewer, on any Docker machine, e.g. your Mac):**
```bash
cp .env.example .env    # set the three change-me passwords
./scripts/verify_d01.sh # expect: ... == D01 PASS ==
```

---

### D02 — Authentication (single-user)
**Goal:** one owner account; all API routes protected. **Depends on:** D01

**Tasks**
- D02-T01 `users` table per Appendix A; password hashed (argon2/bcrypt).
- D02-T02 `POST /auth/login` → JWT (access + refresh); `POST /auth/refresh`.
- D02-T03 Auth middleware guarding all `/api/*` except `/health` and `/auth/*`.
- D02-T04 First-run seed: create owner from `.env` (`OWNER_EMAIL`, `OWNER_PASSWORD`); refuse re-seed.

**Acceptance**
```bash
curl -X POST localhost:8000/api/auth/login -d '{"email":"...","password":"..."}' → 200 + tokens
curl localhost:8000/api/cases            (no token)   → 401
curl localhost:8000/api/cases -H "Authorization: Bearer $T" → 200 []
```

**Verification record / Human verification:** as above.

---

### D03 — Case management (CRUD + Parties)
**Goal:** create, read, update, list cases; parties attached. **Depends on:** D02

**Tasks**
- D03-T01 Migration: `cases`, `parties` (Appendix A).
- D03-T02 Endpoints per Appendix B: `POST/GET/PATCH/DELETE /api/cases`, `GET /api/cases/{id}`.
- D03-T03 Soft archive (`status=ARCHIVED`) — never hard-delete a case.
- D03-T04 All mutating calls write `audit_logs` rows.
- D03-T05 Frontend: case list + create/edit form.

**Acceptance**
```bash
curl -X POST /api/cases -d '{"title":"CASE-001 deposit","jurisdiction":"BE-Vrederechter-Leuven"}'
curl /api/cases → contains the new case
psql -c "select action,entity_type from audit_logs order by created_at desc limit 1" → INSERT/case
```

---

## 4. Phase 2 — Documents & Ingestion

### D04 — Document storage (immutability)
**Goal:** originals in MinIO, hashed, never modified. **Depends on:** D03

**Tasks**
- D04-T01 Migration: `documents`, `document_versions` (Appendix A).
- D04-T02 `POST /api/cases/{id}/documents` (multipart): compute SHA-256, store original under `originals/{uuid}/{filename}`, insert `documents` + `document_versions(type=ORIGINAL)`.
- D04-T03 `GET /api/documents/{id}` (metadata + download URL); `GET /api/documents/{id}/text` (empty until D05).
- D04-T04 Immutability: any write to an existing original object is rejected at the application layer; MinIO bucket versioning ON.

**Acceptance**
```bash
H1=$(sha256sum scan.pdf | cut -d' ' -f1)
curl -X POST /api/cases/$CID/documents -F file=@scan.pdf
H2=$(psql -tc "select file_hash from documents where id=$DID")
[ "$H1" = "$H2" ] && echo OK
# re-run upload of a modified same-name file → new document row, original untouched
```

---

### D05 — OCR pipeline
**Goal:** scanned PDFs/images become searchable text with page-level provenance. **Depends on:** D04

**Tasks**
- D05-T01 Worker (Redis queue) on `document.uploaded` event.
- D05-T02 Tesseract OCR, languages `nld+fra+rus` per `.env`; per-page text into `document_text`; `document_versions(type=OCR)`.
- D05-T03 Processing status transitions `UPLOADED → PROCESSING → READY|FAILED`; failures logged with error.
- D05-T04 Full-text GIN index on `document_text` per Appendix A.

**Acceptance**
```bash
curl -X POST /api/cases/$CID/documents -F file=@lease_scan.pdf   # image-only PDF
sleep 5; curl /api/documents/$DID/text → contains "huurovereenkomst"
sha256sum check → original hash unchanged; document_versions has OCR row referencing original
psql audit_logs → UPLOAD, OCR_COMPLETE rows
```

---

### D06 — Inbox & classification + review queue
**Goal:** everything enters through the Inbox; nothing commits to a case without review. **Depends on:** D05

**Tasks**
- D06-T01 Migration: inbox item model per Appendix A (statuses NEW/PROCESSING/REVIEW_REQUIRED/APPROVED/REJECTED/DUPLICATE).
- D06-T02 Classifier: document type (COURT_LETTER/LAWYER_EMAIL/INVOICE/LEASE/PHOTO/AUDIO/NOTE), sender, date; entity extraction (people, case numbers, dates, amounts).
- D06-T03 Case matching: case-number → participant → email-thread → semantic similarity → `MATCHED` or `CASE_MATCH_NEEDED`.
- D06-T04 Proposal generation (new timeline event / deadline / evidence) — stored as proposals, none committed.
- D06-T05 API + UI: Inbox list, item detail, **Accept / Reject / Modify**.

**Acceptance**
```bash
curl -X POST /api/inbox -F file=@court_letter.pdf
curl /api/inbox → one item, status REVIEW_REQUIRED
curl -X POST /api/inbox/$IID/approve → proposals committed; timeline event exists with provenance
psql audit_logs → REVIEW_APPROVED row with actor
```

---

## 5. Phase 3 — Case intelligence

### D07 — Timeline + provenance
**Goal:** chronology where every event is sourced. **Depends on:** D05

**Tasks**
- D07-T01 Migration: `timeline_events`, `timeline_sources`, `provenance` (Appendix A).
- D07-T02 Endpoints per Appendix B; events carry `verification_status` (PROPOSED/APPROVED/REJECTED).
- D07-T03 Auto-extraction from OCR'd docs creates PROPOSED events with provenance (doc + page).
- D07-T04 UI: case timeline view; click event → source excerpt.

**Acceptance**
```bash
curl -X POST /api/cases/$CID/timeline -d '{"event_date":"2026-02-12","title":"Exit inspection"}'
curl /api/cases/$CID/timeline → event present with source_id
GET /api/search?q=keuring → returns the event's source document
```

### D08 — Evidence, Claims & Issue tree
**Goal:** `ISSUE → arguments FOR/AGAINST → claims → evidence` with gaps. **Depends on:** D07

**Tasks**
- D08-T01 Migration: `issues`, `arguments` (SUPPORTING/OPPOSING/COUNTERARGUMENT), `claims`, `claim_sources`, `evidence` (Appendix A).
- D08-T02 Endpoints per Appendix B; claim↔provenance many-to-many.
- D08-T03 "Evidence matrix" view: per issue, FOR/AGAINST columns + **Missing** list.

**Acceptance**
```bash
POST issue "Was the property delivered in good condition?"
POST claim "Landlord confirmed good condition at exit" + link provenance (doc p.4)
GET /api/cases/$CID/issues/$ISID → claim listed with citation; missing-evidence field visible
```

### D09 — Search (full-text + semantic)
**Goal:** retrieve by keywords and by meaning. **Depends on:** D05 (text), D08 (entities)

**Tasks**
- D09-T01 Embeddings: chunk `document_text`, store in `document_embeddings` (VECTOR(3072)), hnsw or ivfflat per Appendix A.
- D09-T02 `GET /api/search?q=&case_id=&type=` combining pg_trgm + full-text + vector rank.
- D09-T03 Result items always include provenance pointer (doc/page or audio timestamp).

**Acceptance**
```bash
curl "/api/search?q=waarborg"        → finds lease clause (full-text)
curl "/api/search?q=deposit repayment"&semantic=1 → finds same doc without keyword "waarborg"
```

---

## 6. Phase 4 — Agent runtime

### D10 — Agent core (LangGraph, tools, activity feed)
**Goal:** agent operates **on the case database** through tools only. **Depends on:** D09

**Tasks**
- D10-T01 Task model `agent_tasks` + `agent_actions` (Appendix A); states QUEUED → RUNNING → WAITING_APPROVAL → COMPLETED|FAILED.
- D10-T02 LangGraph graph per `AGENT_SYSTEM.md`: Planner → Tool selection → Execution → Review → Result.
- D10-T03 Tool catalog v1 per Appendix C (case/evidence/search tools; action tools stubbed behind approval).
- D10-T04 `POST /api/agent/tasks`, `GET /api/agent/tasks/{id}`, `GET /api/agent/tasks/{id}/events` (SSE): activity feed shows "Reading documents / Searching evidence / Found contradiction / Waiting for approval" — **never chain-of-thought**.
- D10-T05 Output format enforced: Answer / Sources / Confidence / Open questions / Proposed next actions.

**Acceptance**
```bash
curl -X POST /api/agent/tasks -d '{"case_id":"'$CID'","instruction":"summarize my case"}'
GET /api/agent/tasks/$TID/events → activity items streaming
GET /api/agent/tasks/$TID → COMPLETED, answer with ≥1 citation block {court|document, passage, url|null}
```

### D11 — Agent roles (incl. adversarial loop)
**Goal:** Case Manager / Evidence / Timeline / Research / Adversarial / Drafting roles. **Depends on:** D10

**Tasks**
- D11-T01 Role routing in planner.
- D11-T02 **Adversarial Agent**: `attack_case(case_id)` → weaknesses, contradictions, adverse jurisprudence, missing evidence; then `defend_case(...)`. Both passes logged.
- D11-T03 Research Agent: `search_legislation`, `search_jurisprudence` against Belgian sources (BELGIAN_SOURCES.md); each proposition normalized to PROPOSITION → SOURCE → ARTICLE → CASE → RELEVANCE → CONFIDENCE.
- D11-T04 Lawyer-meeting brief generator (12 sections, §1).

**Acceptance**
```bash
POST /api/agent/tasks {instruction:"attack my case"} → COMPLETED with ≥3 weakness items, each sourced
POST /api/agent/tasks {instruction:"prepare lawyer meeting"} → brief with all 12 sections present
```

### D12 — Citation-verification gate
**Goal:** no legal proposition ships without a resolvable citation. **Depends on:** D11

**Tasks**
- D12-T01 Citation record: court, date, case number, ECLI, source (JuPortal/Justel/Lex.be), URL, exact passage, relevance.
- D12-T02 Verification: resolver re-fetches the source URL (or checks local copy) and compares passage; result VERIFIED | UNVERIFIABLE | MISMATCH.
- D12-T03 UI: unverified citations rendered as such; cannot be marked APPROVED while UNVERIFIABLE.
- D12-T04 Property-style test: for N sampled agent answers, 100% of legal claims carry a citation record and ≥1 passage match is attempted.

**Acceptance**
```bash
POST task asking for applicable law on huurwaarborg
→ every legal claim in answer has legal_citations row with status VERIFIED or explicit UNVERIFIABLE flag
```

---

## 7. Phase 5 — Communications

### D13 — Email ingestion via n8n
**Goal:** case emails flow into the Inbox automatically. **Depends on:** D06

**Tasks**
- D13-T01 n8n workflow (importable JSON in `n8n/`): Gmail/Outlook trigger → normalize → `POST /api/webhooks/email`.
- D13-T02 Backend webhook: dedupe (`provider_message_id`), thread reconstruction, Inbox item creation.
- D13-T03 `communications` + `emails` tables (Appendix A).

**Acceptance**
```bash
Send email to watched mailbox with subject "CASE-001 ..."
→ within 60s: /api/inbox contains it, matched to the case, attachments stored as documents
```

### D14 — Drafting & approval workflow
**Goal:** agent drafts; human sends. **Depends on:** D10, D13

**Tasks**
- D14-T01 `drafts` + `approvals` tables (Appendix A); states DRAFT → REVIEW → APPROVED → EXECUTED|REJECTED.
- D14-T02 Endpoints per Appendix B incl. `POST /api/approvals/{id}/approve|reject`.
- D14-T03 Send execution via n8n (email) only on APPROVED; sent copy stored in `communications`.

**Acceptance**
```bash
POST /api/agent/tasks {instruction:"update lawyer on case status"}
→ draft exists; NO email sent yet
POST /api/approvals/$AID/approve → email actually sent; audit rows DRAFT_CREATED, APPROVED, SENT
# regression: same flow without approve → nothing sent (verified in mailbox)
```

### D15 — Deadlines & dashboard
**Goal:** no missed procedural date. **Depends on:** D06

**Tasks**
- D15-T01 `deadlines` table (PROPOSED/APPROVED/COMPLETED/MISSED) (Appendix A); auto-extraction from documents ("binnen 30 dagen", hearing dates) as PROPOSED.
- D15-T02 Dashboard: upcoming deadlines per case + overdue list; reminder job.

**Acceptance**
```bash
Upload letter containing "binnen 30 dagen" → PROPOSED deadline with provenance appears
Approve → dashboard shows it; audit row exists
```

---

## 8. Phase 6 — Hardening

### D16 — Audit & approvals enforcement
**Goal:** the audit trail alone can reconstruct who did what. **Depends on:** D14, D15

**Tasks**
- D16-T01 Code sweep: every mutating endpoint emits `audit_logs` (actor, action, entity, old/new JSONB). List-then-test.
- D16-T02 `audit_logs` append-only (no UPDATE/DELETE — enforced by DB role).
- D16-T03 Audit viewer UI per case + global.

**Acceptance**
```bash
# for each of: create case, upload doc, approve inbox item, approve draft, modify timeline event
psql -c "select actor_type,action,entity_type from audit_logs where ..." → expected rows
psql attempt UPDATE audit_logs → permission denied
```

### D17 — Security hardening & backup
**Goal:** sensible single-user security; recoverable data. **Depends on:** D01–D16

**Tasks**
- D17-T01 `SECURITY.md` implemented: `.env` secrets, CORS locked to frontend origin, hashed passwords, TLS at reverse proxy, MinIO not public.
- D17-T02 Nightly `pg_dump` + MinIO sync to backup dir; `scripts/backup.sh`, `scripts/restore.sh`.
- D17-T03 Dependency pinning + basic scan in CI (GitHub Action: `pip-audit`, `npm audit`).

**Acceptance**
```bash
./scripts/backup.sh && ./scripts/restore.sh /tmp/restore-check → cases/documents counts match
curl from unauthorized origin → blocked; /api/* without token → 401
```

### D18 — Production deployment (Belgium go-live)
**Goal:** runs on the target host reliably. **Depends on:** D17

**Tasks**
- D18-T01 Compose override for prod: reverse proxy (Caddy/Traefik) + TLS, restart policies, log rotation.
- D18-T02 Runbook: update procedure, restore procedure, disk-space monitoring.
- D18-T03 Court-filing procedure documented as **manual** (e-Deposit by hand; agent only prepares the bundle — non-goal remains).

**Acceptance**
```bash
# from a fresh machine following README + runbook:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
→ /health ok, login works, one real case imported end-to-end
```

---

## 9. Appendix A — Database schema (authoritative)
See `docs/specs/DATABASE_SCHEMA.md` — contains the full DDL contract for: `users`, `cases`, `parties`, `documents`, `document_versions`, `document_text`, `document_embeddings`, `evidence`, `provenance`, `claims`, `claim_sources`, `timeline_events`, `timeline_sources`, `issues`, `arguments`, `deadlines`, `communications`, `emails`, `legal_sources`, `legal_citations`, `agent_tasks`, `agent_actions`, `drafts`, `approvals`, `audit_logs`, inbox tables. Postgres 17, extensions uuid-ossp / pgvector / pg_trgm.

## 10. Appendix B — API contract
See `docs/specs/API_SPEC.md` — endpoint table with request/response shapes, auth, pagination, SSE events, approval endpoints. (OpenAPI 3.1 spec generated at D10.)

## 11. Appendix C — Agent tool catalog
See `docs/specs/AGENT_SYSTEM.md` §Tools — every tool with input/output schemas and required permissions. Action tools (`send_email`, `create_calendar_event`, filing) are always approval-gated.

## 12. Appendix D — Belgian sources
See `docs/specs/BELGIAN_SOURCES.md` — JuPortal, Justel, Lex.be, EUR-Lex, e-Deposit: access method, coverage limits, citation format (ECLI), verification approach.

## 13. Changelog
| Date | Change | Deliverables affected |
|---|---|---|
| v1.0 | Initial plan | D01–D18 |
