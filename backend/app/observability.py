"""Observability (D19): structured logs written to a single file the UI and
reviewer can read. Status rules in IMPLEMENTATION_PLAN §0.2 remain the same;
this just makes failures greppable and the UI log page possible."""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Use a function to get the log path, allowing test-time override via env var
def _get_log_path() -> Path:
    return Path(os.getenv("APP_LOG", "/app/logs/app.jsonl"))


def _ensure_dir() -> None:
    lp = _get_log_path()
    try:
        lp.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback for test environments without /app/logs write access
        fallback = Path(tempfile.gettempdir()) / "litigationos_logs"
        fallback.mkdir(parents=True, exist_ok=True)
        os.environ["APP_LOG"] = str(fallback / "app.jsonl")


def log(scope: str, level: str, event: str, **fields) -> None:
    _ensure_dir()
    lp = _get_log_path()
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "level": level, "scope": scope, "event": event,
        **{k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v) for k, v in fields.items()},
    }
    with lp.open("a") as f:
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
    lp = _get_log_path()
    if not lp.exists():
        return []
    lines = lp.read_text().splitlines()[-10000:]
    rows = [json.loads(line) for line in lines if line.strip()]
    if level:
        rows = [r for r in rows if r.get("level") == level]
    return rows[-n:]


logger = logging.getLogger("litigationos")