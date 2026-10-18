# LitigationOS

**AI-assisted legal case management & litigation agent — Belgium-first, self-hosted.**

LitigationOS turns a legal dispute into a persistent **Case** object: documents, evidence,
timeline, issues, research, correspondence, deadlines and drafts — with an AI agent that
analyzes and researches, but never acts externally without human approval and must cite a
source for every factual or legal claim.

- Not a legal chatbot — the database is the source of truth, chat is only an interface.
- Not a lawyer replacement — the lawyer stays the legal decision-maker.
- Belgian sources are first-class: JuPortal, Justel, EUR-Lex, e-Deposit.

---

## TL;DR

```bash
cp .env.example .env              # then edit the passwords inside
docker compose up -d --build      # first run builds images: ~5–10 min
open http://localhost:3000        # log in: owner@localhost.dev / change-me-now (or your OWNER_*)
```

Details and troubleshooting below.

---

## Run it (about 5 minutes)

The whole platform runs in Docker. **You do not need Node.js, Python, Postgres, Redis or an
S3 server installed on your machine** — everything is containerized.

### 0. What you need

| Requirement | Notes |
|---|---|
| Docker Desktop (macOS/Windows) or Docker Engine + Compose v2 (Linux) | Verified with Docker `29.4.0` / Compose `v5.1.1` |
| ~4 GB RAM and ~2–3 GB free disk for Docker | PostgreSQL, Redis, SeaweedFS, n8n and three app images |
| Free ports | `3000`, `8000`, `5678` (and `80`/`443` only if you use the production profile) |
| Optional: OpenAI or Anthropic API key | Only for the AI features (analysis, chat, drafting) |

### 1. Get the code

```bash
git clone <repo-url> litigationos
cd litigationos
```

(If you already cloned it, just `cd` into the checkout.)

### 2. Create the configuration file

```bash
cp .env.example .env
```

`.env` is git-ignored and is read by every container. Defaults are fine for local play, but
change these before starting:

| Variable | What it is | Default |
|---|---|---|
| `POSTGRES_PASSWORD` | Database password | `change-me-now` |
| `OWNER_PASSWORD` | Password of the first user account | `change-me-now` |
| `JWT_SECRET` | Signs login tokens — set a long random string | `dev-secret-change-me` |
| `OWNER_EMAIL` | Email of the first user account (pre-filled in the login form) | `owner@localhost.dev` |
| `N8N_PASSWORD` | n8n (email automation) password | `change-me-now` |
| `LLM_PROVIDER` + `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Enables the AI features | unset |

> **Two rules that bite people:**
> 1. Set `POSTGRES_PASSWORD` **before** the first start. PostgreSQL applies it only when its
>    data volume is created; changing it later makes the backend unable to connect (fix: keep
>    the old value, or wipe the data with the reset command below).
> 2. The owner account is seeded **once** from `OWNER_EMAIL` / `OWNER_PASSWORD`. Editing
>    `OWNER_PASSWORD` afterwards does nothing — log in with the original password, or reset.

### 3. Start the stack

```bash
docker compose up -d --build
```

On the first run this builds three images (Python backend, OCR worker with Tesseract,
Next.js frontend): expect **~5–10 minutes**. Later runs take seconds.

Check that everything came up:

```bash
docker compose ps
```

Every service should be `Up` (`db`, `redis` and `s3` also `healthy`).

### 4. Open the app

👉 **<http://localhost:3000>**

Log in with the `OWNER_EMAIL` / `OWNER_PASSWORD` from your `.env`
(defaults: `owner@localhost.dev` / `change-me-now`). The home page shows
`Backend: ok` when the GUI can reach the API.

### 5. Confirm it is healthy

```bash
curl localhost:8000/health
# {"status":"ok","db":"ok","redis":"ok","s3":"ok"}

./scripts/verify_d01.sh
# ... == D01 PASS ==
```

`./scripts/verify_d01.sh` (also available as `make test`) starts the stack, waits for the
backend, and prints `== D01 PASS ==` when all seven services are healthy.

---

## What runs where

| Service | URL / access | Purpose |
|---|---|---|
| `frontend` | <http://localhost:3000> | Next.js GUI (login, cases, case workspace, logs) |
| `backend` | <http://localhost:8000> · docs at [/docs](http://localhost:8000/docs) | FastAPI; `/health` for status, `/docs` for the full API |
| `worker` | no port | Consumes the OCR queue (PDF → text) |
| `db` | `make psql` (internal only, no host port) | PostgreSQL 17 + pgvector + pg_trgm |
| `redis` | internal only | Queue between backend and worker |
| `s3` | internal only | SeaweedFS, stores immutable original documents |
| `n8n` | <http://localhost:5678> | Optional email ingestion / automation |

Only the frontend, the backend and n8n publish ports; the database and object store are
reachable only from inside the Docker network.

---

## Using it

What works today (backend verified through **D19**; the GUI is still being filled in):

1. **Home** (<http://localhost:3000>) — log in, see your cases, create a case.
2. **Case page** (`/cases/<id>`, click a case) — four steps:
   1. *Tell the agent what's going on* — free text; the agent reads the case, issues,
      deadlines and evidence, then answers (needs an LLM key, see below).
   2. *Attach your evidence* — upload PDFs or scans/photos; the worker OCRs them in the
      background (`processing_status` goes `READY` within seconds).
   3. *Analysis* — "Generate" runs a lawyer-meeting brief.
   4. *Letters to your lawyer* — draft list with **Approve / Reject** (approval is required
      before anything is sent).
3. **Logs** (<http://localhost:3000/logs>) — the central structured log, filterable by level.

### Try the API directly

```bash
# 1. log in and keep the token (password: your OWNER_PASSWORD — default shown)
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@localhost.dev","password":"change-me-now"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 2. create a case
curl -s -X POST localhost:8000/api/cases \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Deposit dispute — Vrederechter"}'

# 3. list cases
curl -s localhost:8000/api/cases -H "Authorization: Bearer $TOKEN"
```

Browsable documentation for every endpoint: <http://localhost:8000/docs>.

---

## Optional: AI features

Set one provider in `.env`, then restart the backend:

```bash
LLM_PROVIDER=openai          # openai | anthropic  (google is listed in .env.example but not implemented yet)
OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY=...
```

```bash
docker compose up -d backend
```

Without a key everything still runs — only *ask the agent*, *analysis* and *drafting* fail
(the GUI shows `LLM call failed: KeyError: 'OPENAI_API_KEY'`). Legal-source lookups also need
outbound internet from the container; when they fail, citations are reported as
`UNVERIFIABLE` rather than invented.

## Optional: email ingestion (n8n)

<http://localhost:5678> runs n8n. On first visit n8n asks you to create its own admin account
(n8n 2.x — the `N8N_BASIC_AUTH_*` variables in `docker-compose.yml` are legacy and ignored).
Import `n8n/email-webhook.json`, connect a Gmail credential, set `WEBHOOK_TOKEN` in `.env`
(the workflow forwards it as `X-Webhook-Token`), and incoming mail lands in the Inbox.

---

## Everyday commands

```bash
make up      # docker compose up -d            (start)
make down    # docker compose down             (stop, keeps data)
make logs    # docker compose logs -f          (follow all logs)
make psql    # psql shell inside the db container
make test    # ./scripts/verify_d01.sh
```

**Code changes require a rebuild.** Sources are copied into the images (there are no bind
mounts), so after editing backend/worker/frontend code run:

```bash
docker compose up -d --build backend     # or worker, frontend, or all of them
```

Per-deliverable smoke tests live in `scripts/verify_d01.sh` … `scripts/verify_d19.sh`; they
expect the stack to be running and the owner credentials from `.env`.

## Logs and troubleshooting

App logs are written as JSONL to `/app/logs/app.jsonl` inside the backend container (the
`logdata` volume) and are visible in the GUI under **/logs** or via `GET /api/logs`.

| Symptom | Cause / fix |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop / `sudo systemctl start docker`. |
| `port is already allocated` on 3000/8000/5678 | Another stack is running: `docker compose down` in the old checkout, or check with `lsof -iTCP:3000 -sTCP:LISTEN`. |
| `/health` returns `"status":"degraded"`, `db: error` | `POSTGRES_PASSWORD` was changed after the data volume was created. Restore the old value, or reset (below). |
| Login says `login failed` | The owner account was seeded with a different password. Use the original one, or reset. |
| GUI shows an older version than the code | Rebuild: `docker compose up -d --build frontend`. |
| Analysis/chat says `LLM call failed` | No provider key in `.env` (see *AI features*). |
| Uploaded document stays `PROCESSING` or `FAILED` | Only PDFs and images are OCR'd. Check `docker compose logs worker`. |
| n8n asks to create an account / ignores admin password | Normal for n8n 2.x; create the account on first visit. |
| `WARNING: Found orphan containers ([...caddy-1])` | You previously ran the production profile: `docker compose down --remove-orphans`. |

### Reset everything (deletes all data)

```bash
docker compose down -v      # removes the pgdata / s3data / n8ndata / logdata volumes
docker compose up -d --build
```

The owner account is re-seeded from `.env` on the next start, so this is also how you change
`OWNER_PASSWORD`.

## Backups

```bash
./scripts/backup.sh                     # pg_dump + SeaweedFS volume snapshot → backups/<date>/
./scripts/restore.sh backups/<date>     # restore into a fresh stack (destroys current data)
```

Both scripts assume the default `litigation` database user and this checkout's Docker volume
names (`litigationos-_*`) — if you changed `POSTGRES_USER` or cloned into a differently named
directory, adjust them first.

## Production deployment (not yet turn-key)

`docker-compose.prod.yml` + `Caddyfile` are the intended go-live shape: Caddy takes 80/443,
the backend/frontend host ports are closed, and everything is proxied.

```bash
DOMAIN=localhost ./scripts/verify_d18.sh         # local smoke: http://localhost/health -> 200
```

This profile takes over ports 80/443, so stop the dev stack first (`make down`).
TLS needs a **public domain** pointing at the host (there is no certificate for `localhost`),
and real secrets in `.env` first.

⚠️ **Known gap:** the overlay never passes `DOMAIN` into the Caddy container (the `caddy`
service has no `environment:` block — `docker exec litigationos--caddy-1 printenv | grep DOMAIN`
is empty), so the `https://{$DOMAIN}` site block currently has an empty hostname. Add
`environment: { DOMAIN: ${DOMAIN} }` to the `caddy` service before using this for a real domain.
See `docs/IMPLEMENTATION_PLAN.md` (D17, D18) for the deployment contract.

---

## Repository layout

```
litigationos/
├── docker-compose.yml          # local stack (7 services)
├── docker-compose.prod.yml     # production overlay (Caddy, 80/443 only)
├── Caddyfile                   # reverse proxy for the production profile
├── .env.example                # documented configuration — copy to .env
├── Makefile                    # up / down / logs / psql / test
├── backend/                    # FastAPI app (auth, cases, documents, agent, approvals)
├── worker/                     # OCR worker (Tesseract, nld+fra+rus)
├── frontend/                   # Next.js app (home, case workspace, logs)
├── n8n/                        # importable email-ingestion workflow (JSON)
├── db/init.sql                 # Postgres extensions (uuid-ossp, vector, pg_trgm)
├── scripts/                    # verify_dNN.sh acceptance tests, backup/restore
└── docs/
    ├── IMPLEMENTATION_PLAN.md  # ★ master contract: deliverables, acceptance, status
    └── specs/                  # PRODUCT_SPEC, ARCHITECTURE, API_SPEC, SECURITY, …
```

## Where the project stands

`docs/IMPLEMENTATION_PLAN.md` is the source of truth, including a status table
(D01–D19 verified; D20 *web case setup / upload* and D22 *analysis report* in progress;
D21, D23 not started). Update the table when a deliverable's acceptance output is pasted into
its verification record.

## Core principles

1. **Case first** — structured data, not conversation history.
2. **Immutable evidence** — originals are never modified; processing creates derived artifacts.
3. **Provenance** — every material fact links to a source (document + page / audio + timestamp).
4. **Human approval** — sending, filing, changing verified facts all require explicit approval.
5. **Auditability** — every important action is logged, never deleted.
6. **Replaceable components** — no hard dependency on a single LLM vendor.
