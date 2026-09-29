"""FastAPI application entrypoint — LitigationOS backend."""
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import auth_routes, cases, documents, health
from app.db import apply_migrations
from app.deps import current_user_id

app = FastAPI(title="LitigationOS API", version="0.2.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup() -> None:
    applied = apply_migrations(os.environ["DATABASE_URL"])
    if applied:
        print("migrations applied:", applied, flush=True)
    auth_routes.seed_owner()
    print("owner seed ensured", flush=True)


app.include_router(health.router)
app.include_router(auth_routes.router, prefix="/api")
app.include_router(cases.router, prefix="/api", dependencies=[Depends(current_user_id)])
app.include_router(documents.router, prefix="/api", dependencies=[Depends(current_user_id)])
