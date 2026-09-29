"""FastAPI application entrypoint — LitigationOS backend."""
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import auth_routes, cases_stub, health
from app.auth import decode_token
from app.db import apply_migrations

app = FastAPI(title="LitigationOS API", version="0.2.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=False)


def current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    sub = decode_token(creds.credentials)
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return sub


@app.on_event("startup")
def _startup() -> None:
    applied = apply_migrations(os.environ["DATABASE_URL"])
    if applied:
        print("migrations applied:", applied, flush=True)
    auth_routes.seed_owner()
    print("owner seed ensured", flush=True)


app.include_router(health.router)
app.include_router(auth_routes.router, prefix="/api")
app.include_router(cases_stub.router, prefix="/api", dependencies=[Depends(current_user_id)])
