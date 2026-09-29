"""JWT helpers (D02-T02)."""
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60
REFRESH_TTL_DAYS = 30


def create_token(subject: str, kind: str) -> str:
    ttl = timedelta(minutes=ACCESS_TTL_MIN) if kind == "access" else timedelta(days=REFRESH_TTL_DAYS)
    payload = {"sub": subject, "typ": kind, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str, expected_kind: str = "access") -> str | None:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("typ") != expected_kind:
        return None
    return payload.get("sub")
