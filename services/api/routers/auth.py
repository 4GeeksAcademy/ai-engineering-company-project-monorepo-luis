"""JSON/OAuth2 login and current-user profile endpoints."""

import secrets
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import SecretStr, ValidationError

from services.api.auth_dependencies import get_auth_settings, get_current_user, unauthorized
from services.api.auth_models import AuthMeResponse, LoginRequest, TokenResponse, UserRecord
from services.api.passwords import hash_password, verify_password
from services.api.security import JWTSettings, create_access_token
from services.api.user_service import (
    ProfileNotFoundError,
    get_profile_by_user_id,
    get_user_by_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@lru_cache(maxsize=1)
def _dummy_hash() -> SecretStr:
    return hash_password(SecretStr(secrets.token_urlsafe(32)))


async def parse_login(request: Request) -> LoginRequest:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    try:
        if content_type == "application/json":
            payload = await request.json()
        elif content_type == "application/x-www-form-urlencoded":
            form = await request.form()
            allowed = {"username", "password", "grant_type", "scope", "client_id", "client_secret"}
            if set(form) - allowed or form.get("grant_type") not in (None, "", "password"):
                raise ValueError
            if len(form.getlist("username")) != 1 or len(form.getlist("password")) != 1:
                raise ValueError
            payload = {"email": form.get("username"), "password": form.get("password")}
        else:
            raise HTTPException(status_code=415, detail="Unsupported login content type")
        return LoginRequest.model_validate(payload)
    except (ValidationError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid login payload") from None


@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": LoginRequest.model_json_schema()},
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "required": ["username", "password"],
                        "properties": {
                            "username": {"type": "string", "format": "email"},
                            "password": {"type": "string", "format": "password", "writeOnly": True},
                            "grant_type": {"type": "string", "enum": ["password"]},
                            "scope": {"type": "string"},
                            "client_id": {"type": "string"},
                            "client_secret": {"type": "string", "format": "password", "writeOnly": True},
                        },
                    }
                },
            },
        }
    },
)
def login(
    credentials: LoginRequest = Depends(parse_login),
    settings: JWTSettings = Depends(get_auth_settings),
) -> TokenResponse:
    user = get_user_by_email(str(credentials.email))
    hashed = user.hashed_password if user is not None else _dummy_hash()
    valid_password = verify_password(credentials.password.get_secret_value(), hashed)
    if user is None or not user.is_active or not valid_password:
        raise unauthorized()
    return TokenResponse(access_token=create_access_token(user, settings))


@router.get("/me", response_model=AuthMeResponse)
def current_user(user: UserRecord = Depends(get_current_user)) -> AuthMeResponse:
    try:
        profile = get_profile_by_user_id(user.id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found") from None
    return AuthMeResponse(email=user.email, role=user.role, profile=profile)