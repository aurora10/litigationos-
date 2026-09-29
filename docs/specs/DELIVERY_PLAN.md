# DELIVERY_PLAN.md — Delivery Plan

Version 1.0 · See `IMPLEMENTATION_PLAN.md` for deliverable details and the live status table.

## Milestones (≈2–3 weeks per phase, one deliverable at a time)

- **M1 — Foundation (D01–D03):** boots locally; authenticated case CRUD with audit.
- **M2 — Ingestion (D04–D06):** upload a scan → OCR → searchable; Inbox with review queue.
- **M3 — Case intelligence (D07–D09):** sourced timeline; issue tree with evidence gaps; hybrid search.
- **M4 — Agent (D10–D12):** agent answers with citations; adversarial attack/defend; citation-verification gate.
- **M5 — Communications (D13–D15):** email ingestion; draft→approve→send; deadlines dashboard.
- **M6 — Hardening & go-live (D16–D18):** audit enforcement, backups, production deploy, runbook.

## Working agreement (developer ↔ reviewer)

1. Developer builds **one deliverable** at a time, stepwise (same rhythm as the SEO-agent project).
2. After each: run its **Acceptance** block, paste **real output** into the deliverable's "Verification record", set its status row to DONE, commit as `D05: OCR pipeline (acceptance passed)`, **push to GitHub**.
3. Reviewer pulls locally and re-runs the "Human verification" commands before signing off.
4. BLOCKED is stated with a reason and re-planned via the plan's change control (§0.4) — never silently descoped.
5. Build and first verification happen on the dev machine; the reviewer verifies on their own machine from the GitHub repo.

## Definition of done (per deliverable)
Acceptance commands pass + audit rows exist (where applicable) + verification record filled + status table updated + pushed.

## Next documents after this plan (if needed)
- `docs/openapi.json` generated from code at D10.
- Screen-by-screen UI wireframes only if the review queue / evidence-matrix UI grows ambiguous.
