"""Observability (D19): structured logs written to a single file the UI and
reviewer can read. Status rules in IMPLEMENTATION_PLAN §0.2 remain the same;
this just makes failures greppable and the UI log page possible."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(os.getenv("APP_LOG", "/app/logs/app.jsonl"))


def _ensure_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log(scope: str, level: str, event: str, **fields) -> None:
    _ensure_dir()
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "level": level, "scope": scope, "event": event,
        **{k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v) for k, v in fields.items()},
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(row) + "\n")


def log_middleware_factory(app):
    @app.middleware("http")
    async def log_requests(request, call_next):
        resp = await call_next(request)
        if resp.status_code >= 400:
            log("http", "warn", "http_error", path=str(request.url.path), method=request.method,
                status=resp.status_code, client=str(request.client))
        return resp
    return log_requests


def tail(n: int = 100, level: str | None = None):
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text().splitlines()[-10000:]
    rows = [json.loads(line) for line in lines if line.strip()]
    if level:
        rows = [r for r in rows if r.get("level") == level]
    return rows[-n:]


logger = logging.getLogger("litigationos")
