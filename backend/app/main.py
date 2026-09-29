"""FastAPI application entrypoint — LitigationOS backend (D01)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import health

app = FastAPI(title="LitigationOS API", version="0.1.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
