# API_SPEC.md — API Specification (Appendix B)

Version 1.0 · Base URL `/api` · Auth: JWT bearer on everything except `/health` and `/auth/*` · Pagination: `?limit=&offset=` on all lists · Errors: RFC 7807 `application/problem+json`.

## Auth
- `POST /auth/login` → `{access_token, refresh_token}`
- `POST /auth/refresh` → `{access_token}`

## Cases
- `GET /cases` · `POST /cases` · `GET /cases/{id}` · `PATCH /cases/{id}` · `DELETE /cases/{id}` (soft archive)
- `GET/POST /cases/{id}/parties`

## Documents
- `POST /cases/{id}/documents` (multipart) → `{id, file_hash, processing_status}`
- `GET /cases/{id}/documents` · `GET /documents/{id}` (metadata + download URL) · `GET /documents/{id}/text?page=`

## Evidence
- `GET/POST /cases/{id}/evidence` · `PATCH /evidence/{id}`
- `POST /evidence/{id}/sources` (link provenance)

## Timeline
- `GET/POST /cases/{id}/timeline` · `PATCH /timeline/{id}` (incl. verification_status transitions)

## Issues / Claims
- `GET/POST /cases/{id}/issues` · `GET/PATCH /issues/{id}`
- `POST /issues/{id}/arguments` (type SUPPORTING/OPPOSING/COUNTERARGUMENT)
- `POST /cases/{id}/claims` · `POST /claims/{id}/sources`

## Inbox
- `GET /inbox?status=` · `GET /inbox/{id}`
- `POST /inbox/{id}/approve` · `POST /inbox/{id}/reject` · `POST /inbox/{id}/modify`
- `GET /inbox/{id}/proposals`

## Agent
- `POST /agent/tasks` `{case_id, instruction}` → `{id, status}`
- `GET /agent/tasks/{id}` → `{status, output:{answer, sources[], confidence, open_questions[], next_actions[]}}`
- `GET /agent/tasks/{id}/events` (SSE): activity feed items only — never chain-of-thought

## Search
- `GET /search?q=&case_id=&type=&semantic=1` → results each with provenance pointer `{document_id, page}` or `{document_id, t_start, t_end}`

## Drafts & Approvals
- `GET/POST /cases/{id}/drafts` · `GET/PATCH /drafts/{id}` · `POST /drafts/{id}/submit`
- `GET /approvals?status=` · `POST /approvals/{id}/approve` · `POST /approvals/{id}/reject`

## Deadlines
- `GET/POST /cases/{id}/deadlines` · `PATCH /deadlines/{id}` · `GET /deadlines?due_before=`

## Audit
- `GET /audit?entity_type=&entity_id=` (read-only UI backing)

## Webhooks (token-authenticated, from n8n)
- `POST /webhooks/email` · `POST /webhooks/outlook` · `POST /webhooks/telegram`

## Conventions
- Every mutating endpoint writes `audit_logs` synchronously.
- Approving an approval is itself audited (`APPROVED` → `EXECUTED` on execution).
- Full OpenAPI 3.1 document generated from code at D10 and checked into `docs/openapi.json`.
