"""Observability API (D19) — the single source of truth for "what happened"."""
from fastapi import APIRouter, Depends, Query

from app.deps import current_user_id
from app.observability import tail

router = APIRouter(tags=["logs"])


@router.get("/logs")
def get_logs(level: str | None = Query(None), limit: int = Query(200, le=1000),
             user_id: str = Depends(current_user_id)):
    """JWT-protected view into the central app log."""
    return {"entries": tail(n=limit, level=level)}
