"""Health endpoint: verifies DB, Redis and S3 connectivity (D01-T04)."""
import os

import psycopg
import redis as redis_lib
import boto3
from botocore.config import Config
from fastapi import APIRouter

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


def _check_s3() -> str:
    try:
        client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("S3_ENDPOINT", "http://s3:8333"),
            aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "any"),
            aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "any"),
            config=Config(signature_version="s3v4"),
        )
        client.list_buckets()
        return "ok"
    except Exception:
        return "error"


@router.get("/health")
def health():
    checks = {"db": _check_db(), "redis": _check_redis(), "s3": _check_s3()}
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}
