"""Nexova central operations backend API."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure monorepo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.routers.auth import router as auth_router
from services.api.routers.incidents import router as incidents_router
from services.api.routers.suppliers import router as suppliers_router
from services.api.security import load_jwt_settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.jwt_settings = load_jwt_settings()
    try:
        yield
    finally:
        del application.state.jwt_settings

app = FastAPI(
    title="Nexova Operations API",
    description="Backend services supporting Nexova AI Engineering and Support Operations.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS to allow access from local backoffice UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(incidents_router)
app.include_router(suppliers_router)
app.include_router(auth_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health verification endpoint."""
    return {"status": "ok", "service": "nexova-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="127.0.0.1", port=8000, reload=True)
