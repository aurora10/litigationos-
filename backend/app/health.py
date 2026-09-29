"""Health endpoint: verifies DB, Redis and MinIO connectivity (D01-T04)."""
import os

import psycopg
import redis as redis_lib
from fastapi import APIRouter
from minio import Minio

router = APIRouter()


def _check_db() -> str:
    try:
        url = os.environ["DATABASE_URL"]
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> str:
    try:
        r = redis_lib.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"), socket_connect_timeout=3)
        return "ok" if r.ping() else "error"
    except Exception:
        return "error"


def _check_minio() -> str:
    try:
        client = Minio(
            os.environ.get("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", "litigation"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
            secure=False,
        )
        client.list_buckets()
        return "ok"
    except Exception:
        return "error"


@router.get("/health")
def health():
    checks = {"db": _check_db(), "redis": _check_redis(), "minio": _check_minio()}
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}
