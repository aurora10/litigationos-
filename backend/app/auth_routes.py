"""Auth routes (D02-T02, D02-T04): login, refresh, first-run owner seed."""
import os

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.auth import create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()


def _db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def seed_owner() -> None:
    """Create the owner account once, from env. Refuse to re-seed."""
    email = os.getenv("OWNER_EMAIL", "owner@localhost.dev")
    password = os.getenv("OWNER_PASSWORD", "change-me-now")
    with _db() as conn:
        count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        if count > 0:
            return
        conn.execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s,%s,%s,'OWNER')",
            (email, ph.hash(password), "Owner"),
        )


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(body: LoginIn):
    with _db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email=%s", (body.email,)
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    try:
        ph.verify(row[1], body.password)
    except VerifyMismatchError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    sub = str(row[0])
    return {"access_token": create_token(sub, "access"), "refresh_token": create_token(sub, "refresh"), "token_type": "bearer"}


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh(body: RefreshIn):
    sub = decode_token(body.refresh_token, expected_kind="refresh")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return {"access_token": create_token(sub, "access"), "token_type": "bearer"}
