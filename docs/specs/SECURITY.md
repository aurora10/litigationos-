# SECURITY.md — Security & Data Protection

Version 1.0 · Scope: single-user self-hosted v1 (a litigation file is highly sensitive).

## Secrets & config
- All configuration via `.env`; **never committed** (`.gitignore`). `.env.example` documents keys without values.
- Owner credentials seeded from `.env` at first run only; passwords stored hashed (argon2/bcrypt).

## Transport & network
- Reverse proxy (Caddy/Traefik) terminates TLS in production (D18).
- CORS locked to the frontend origin.
- MinIO is **not publicly exposed**; downloads via short-lived pre-signed URLs from the backend.
- n8n webhooks authenticate with a shared token.

## Data protection
- **Evidence immutability:** MinIO bucket versioning ON; application rejects writes to existing originals; SHA-256 recorded at upload for integrity checks.
- **Audit trail:** `audit_logs` append-only (DB role without UPDATE/DELETE); every mutating API call writes a row (actor, action, entity, old/new JSONB).
- **Approval boundary:** sending emails, filing documents, changing verified facts require explicit approval; executions are themselves audited.
- Backups: nightly `pg_dump` + MinIO sync (D17); restore tested by `scripts/restore.sh`.

## LLM data handling
- LLM provider set via `.env`; documents sent to an LLM only for processing inside agent tasks; no training use (use provider terms / API settings accordingly).
- Citation verification (D12) treats LLM output as untrusted until a source passage resolves.

## Dependency & code hygiene
- Pinned dependencies; CI step runs `pip-audit` / `npm audit` (D17).
- No secrets in logs; audit payloads redact passwords/tokens.

## Explicit non-goals (v1)
- No e-Deposit integration (filing is manual).
- No multi-tenant isolation — single-user deployment; the schema remains multi-user capable for later.
