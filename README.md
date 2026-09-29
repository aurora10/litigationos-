# LitigationOS

**AI-assisted legal case management & litigation agent — Belgium-first, self-hosted.**

LitigationOS turns a legal dispute (e.g. a deposit dispute at the Vrederechter) into a structured, persistent **Case** object: documents, evidence, timeline, issues, research, correspondence, deadlines, drafts — with an AI agent that analyzes, researches and prepares, but **never acts externally without human approval** and **must cite a verifiable source for every factual or legal claim**.

- Not a legal chatbot. The database is the source of truth; chat is only an interface.
- Not a lawyer replacement. The lawyer remains the legal decision-maker.
- Belgian legal sources are first-class: JuPortal, Justel, Lex.be, EUR-Lex, e-Deposit.

---

## Repository layout

```
litigationos/
├── docker-compose.yml          # D01 — full local stack
├── .env.example                # all configuration, documented
├── backend/                    # FastAPI application
├── worker/                     # ingestion/OCR/transcription workers
├── frontend/                   # Next.js application
├── n8n/                        # email/automation workflows (importable JSON)
├── scripts/                    # dev/verify/backup scripts
└── docs/
    ├── IMPLEMENTATION_PLAN.md  # ★ MASTER DOCUMENT — 18 deliverables, acceptance tests, status table
    └── specs/
        ├── PRODUCT_SPEC.md
        ├── ARCHITECTURE.md
        ├── DATABASE_SCHEMA.md
        ├── API_SPEC.md
        ├── AGENT_SYSTEM.md
        ├── INGESTION_PIPELINE.md
        ├── BELGIAN_SOURCES.md
        ├── SECURITY.md
        └── DELIVERY_PLAN.md
```

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | FastAPI (Python) |
| Agent runtime | LangGraph (vendor-independent LLM: Claude / GPT / Gemini) |
| Database | PostgreSQL 17 + pgvector + pg_trgm |
| Object storage | MinIO (immutable originals) |
| Queue | Redis |
| Automation | n8n (email ingestion, notifications) |
| OCR / audio / video | Tesseract (nld/fra/rus) / Whisper / FFmpeg |

## How the build works

`docs/IMPLEMENTATION_PLAN.md` is the contract. It contains **18 deliverables (D01–D18)** across **6 phases**. Every deliverable has:

1. **Tasks** with stable IDs (`D05-T02`)
2. **Acceptance** — literal commands and expected output
3. **Verification record** — filled in by the developer with actual output
4. A **status table** at the top tracking NOT STARTED / IN PROGRESS / DONE / BLOCKED

Workflow: developer builds one deliverable → runs its acceptance block → records real output → marks DONE → pushes. The reviewer pulls and re-runs the commands under "Human verification" to sign off.

## Quick start (available from D01 onward)

```bash
cp .env.example .env
docker compose up -d
./scripts/verify_d01.sh
```

## Core principles (from PRODUCT_SPEC.md)

1. **Case first** — structured data, not conversation history
2. **Immutable evidence** — originals are never modified; processing creates derived artifacts
3. **Provenance** — every material fact links to a source (document + page / audio + timestamp)
4. **Human approval** — sending, filing, changing verified facts all require explicit approval
5. **Auditability** — every important action is logged, never deleted
6. **Replaceable components** — no hard dependency on any single LLM vendor
