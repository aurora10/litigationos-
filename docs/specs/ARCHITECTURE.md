# ARCHITECTURE.md
# Architecture — LitigationOS

## Overview

Frontend: Next.js · React · TypeScript
Backend: FastAPI · Python
Agent runtime: LangGraph (LLM vendor-independent: Claude / GPT / Gemini)
Database: PostgreSQL 17 + pgvector + pg_trgm
Object storage: MinIO (immutable originals, bucket versioning ON)
Queue: Redis
Automation: n8n (integrations at the edges)
Ingestion: Tesseract OCR (nld/fra/rus) · Whisper · FFmpeg

## Diagram

```
                        Next.js (:3000)
                             │
                         FastAPI (:8000)
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
  PostgreSQL             LangGraph               MinIO
  pgvector/pg_trgm        Agent                 Files (originals)
        │                    │
      Redis ◄────────── workers (OCR/Whisper/FFmpeg)
        │
       n8n  ◄── Gmail/Outlook webhooks ──→ /api/webhooks/*
```

## Service responsibilities

- **Frontend** — user interface (cases, inbox, timeline, evidence, research, correspondence, deadlines, agent, settings).
- **FastAPI** — business logic, REST API, auth, audit writes.
- **PostgreSQL** — source of truth (all structured data + full-text + vectors).
- **MinIO** — original evidence storage; originals immutable.
- **LangGraph** — agent orchestration on top of the case DB (see `AGENT_SYSTEM.md`).
- **Redis** — background jobs (ingestion, extraction, sends after approval).
- **n8n** — external integrations only (email in/out, calendar, notifications). No business logic lives in n8n.

## Agent execution pipeline

User Request → Planner → Retrieve Context → Search Evidence → Search Research → Synthesize → Generate Result → **Approval Gate** → Execute

## Repo layout

```
backend/    FastAPI app (routers/, models/, services/, agent/, tools/)
worker/     ingestion consumers (OCR, transcription, extraction)
frontend/   Next.js app
n8n/        importable workflow JSON
scripts/    up/down/backup/restore/verify_Dxx.sh
docs/       this file + IMPLEMENTATION_PLAN.md + specs/
```

## ADRs

- **ADR-1 Postgres as single source of truth** (incl. vectors via pgvector) — fewer moving parts, transactional provenance.
- **ADR-2 MinIO versioning + app-layer write-reject** for originals — immutability is a hard requirement (Principle 2).
- **ADR-3 LangGraph over ad-hoc chains** — explicit state machine matches the agent task lifecycle and approval gates.
- **ADR-4 n8n at the edges only** — keeps automation replaceable and the core testable.
- **ADR-5 LLM behind an interface** — provider set via `.env`; no vendor SDK calls outside `backend/agent/llm.py`.
