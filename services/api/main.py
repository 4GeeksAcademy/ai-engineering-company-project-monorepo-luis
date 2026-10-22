"""Nexova central operations backend API."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Ensure monorepo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.database import init_db
from services.api.routers.auth import router as auth_router
from services.api.routers.incidents import router as incidents_router
from services.api.routers.inventory import router as inventory_router
from services.api.routers.profiles import router as profiles_router
from services.api.routers.suppliers import router as suppliers_router
from services.api.routers.users import router as users_router
from services.api.security import load_jwt_settings

_NO_PREVIOUS_JWT_SETTINGS = object()


@asynccontextmanager
async def lifespan(application: FastAPI):
    previous_settings = getattr(
        application.state, "jwt_settings", _NO_PREVIOUS_JWT_SETTINGS
    )
    application.state.jwt_settings = load_jwt_settings()
    init_db()
    try:
        yield
    finally:
        if previous_settings is _NO_PREVIOUS_JWT_SETTINGS:
            del application.state.jwt_settings
        else:
            application.state.jwt_settings = previous_settings

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
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(inventory_router)


@app.exception_handler(RequestValidationError)
async def sanitize_auth_validation_errors(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    if request.url.path == "/api/incidents" or request.url.path.startswith("/api/incidents"):
        errors = []
        for item in error.errors():
            loc = [str(x) for x in item.get("loc", ()) if str(x) not in ("body", "query", "path")]
            field = ".".join(loc) or "payload"
            msg = item.get("msg", "Invalid value")
            errors.append({"field": field, "message": msg})
        first_field = errors[0]["field"] if errors else "payload"
        first_msg = errors[0]["message"] if errors else "Validation error"
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Validation error for '{first_field}': {first_msg}",
                "errors": errors,
            },
        )
    if request.url.path == "/users" or request.url.path.startswith("/users/"):
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid user request"},
        )
    if request.url.path in (
        "/auth/forgot-password", "/auth/reset-password", "/auth/change-password"
    ):
        if request.url.path == "/auth/reset-password" and any(
            tuple(item["loc"]) == ("body", "token") for item in error.errors()
        ):
            return JSONResponse(status_code=400, content={"detail": "Invalid password reset token"})
        return JSONResponse(status_code=422, content={"detail": "Invalid password request"})
    sanitized = [
        {
            "loc": list(item.get("loc", ())),
            "msg": item.get("msg", "Invalid value"),
            "type": item.get("type", "value_error"),
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": sanitized})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health verification endpoint."""
    return {"status": "ok", "service": "nexova-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="127.0.0.1", port=8000, reload=True)
