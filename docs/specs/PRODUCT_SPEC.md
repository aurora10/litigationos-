# PRODUCT_SPEC.md
# LitigationOS — AI-Assisted Legal Case Management & Litigation Agent

Version: 0.1 · Status: Draft · Author: Product Specification

---

## 1. Executive Summary

LitigationOS is an AI-assisted legal case management platform that helps individuals, legal professionals and organizations manage legal disputes and complex administrative cases — **Belgium first** (first use: deposit dispute, Vrederechter).

The system is a persistent case workspace: documents, emails, letters, photos, audio, video, legal research, deadlines, timelines, evidence, arguments and communications organized around a structured **Case** object.

The platform combines: case management · evidence management · timeline construction · legal research · AI-assisted analysis · draft generation · deadline monitoring · communication workflows.

It assists human decision-making. It does not replace lawyers and does not provide autonomous legal representation.

## 2. Product Vision

**Core concept: the Case is the primary object.** Traditional chatbots operate on conversation history; LitigationOS operates on structured case data. The AI agent can: review evidence · identify contradictions · summarize cases · prepare lawyer briefings · generate chronologies · assist legal research · draft communications · identify missing evidence · monitor deadlines — while maintaining traceability to source materials.

## 3. Product Principles

1. **Case First** — the database is the source of truth; chat is an interface.
2. **Immutable Evidence** — original files are never modified; all processing creates derived artifacts.
3. **Provenance** — every material fact links back to a document, email, letter, image, audio, video or legal source.
4. **Human Approval** — external actions require approval: sending emails, filing documents, changing verified facts.
5. **Auditability** — every important action is logged.
6. **Replaceable Components** — no dependency on a specific LLM vendor.

## 4. User Types

Primary: individual managing legal disputes. Secondary: lawyer. Future: law-firm staff, paralegals. (Multi-user deferred; v1 is single-user.)

## 5. High-Level Workflow

New Case → Import Data → Classify Evidence → Build Timeline → Identify Issues → Research → Prepare Arguments → Draft Communications → **Human Approval** → External Action → Monitor Outcome → Archive

## 6. Core Features

**Cases** — title, description, jurisdiction, case number, status, court, lawyer, parties.
**Evidence** — documents, photos, scans, screenshots, audio, video, web pages, notes.
**Timeline** — auto and manual events; every event includes source references.
**Issues** — a legal/factual question ("Was the property delivered in good condition?") with supporting evidence, opposing evidence, arguments, counterarguments, legal references.
**Research** — legal sources stored separately from case facts (JuPortal/Justel/Lex.be/EUR-Lex).
**Drafts** — emails, letters, lawyer briefings, hearing preparation.
**Deadlines** — filing deadlines, hearing dates, response deadlines.

## 7. Success Criteria

The user can: (1) upload a document, (2) extract information, (3) ask a question, (4) receive a **cited** answer, (5) trace every answer back to evidence, (6) create drafts, (7) approve actions, (8) maintain a complete audit trail.

## 8. Non-Goals

The system will not: act as a lawyer · provide guaranteed legal advice · autonomously file court documents · autonomously communicate with opposing parties.

## 9. Belgian Context (v1 focus)

Deposit-dispute/Vrederechter workflows; Dutch/French source documents (Russian for user notes); Belgian citation formats (ECLI); e-Deposit acknowledged but filing is manual in v1. See `BELGIAN_SOURCES.md`.
