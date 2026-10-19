"""JSON/OAuth2 login and current-user profile endpoints."""

import logging
import secrets
from functools import lru_cache
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import SecretStr, ValidationError

from services.api.auth_dependencies import get_auth_settings, get_current_user, unauthorized
from services.api.auth_models import (
    AuthActionResponse,
    AuthMeResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRecord,
)
from services.api.email_service import (
    PasswordResetSettings,
    load_password_reset_settings,
    send_password_reset_email,
)
from services.api.password_reset_service import (
    CurrentPasswordMismatchError,
    InvalidPasswordResetTokenError,
    change_password,
    issue_password_reset_token,
    reset_password,
)
from services.api.passwords import hash_password, verify_password
from services.api.security import JWTSettings, create_access_token
from services.api.user_service import (
    ProfileNotFoundError,
    UserNotFoundError,
    get_profile_by_user_id,
    get_user_by_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
PasswordResetSender = Callable[[str, SecretStr, PasswordResetSettings], None]


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


def get_password_reset_settings() -> PasswordResetSettings:
    try:
        return load_password_reset_settings()
    except RuntimeError:
        raise HTTPException(
            status_code=503, detail="Password recovery is temporarily unavailable"
        ) from None


def get_password_reset_sender() -> PasswordResetSender:
    return send_password_reset_email


def _deliver_password_reset(
    email: str, settings: PasswordResetSettings, sender: PasswordResetSender
) -> None:
    try:
        token = issue_password_reset_token(email, settings.expire_minutes)
        if token is not None:
            sender(email, token, settings)
    except Exception:
        logger.error("Password reset request processing failed")


@router.post("/forgot-password", response_model=AuthActionResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    settings: PasswordResetSettings = Depends(get_password_reset_settings),
    sender: PasswordResetSender = Depends(get_password_reset_sender),
) -> AuthActionResponse:
    try:
        background_tasks.add_task(_deliver_password_reset, str(payload.email), settings, sender)
    except Exception:
        raise HTTPException(
            status_code=503, detail="Password recovery is temporarily unavailable"
        ) from None
    return AuthActionResponse(
        message="Si esa direcci\u00f3n est\u00e1 registrada, recibir\u00e1s un enlace en breve."
    )


@router.post("/reset-password", response_model=AuthActionResponse)
def reset_forgotten_password(payload: ResetPasswordRequest) -> AuthActionResponse:
    try:
        reset_password(payload.token, payload.new_password)
    except InvalidPasswordResetTokenError:
        raise HTTPException(status_code=400, detail="Invalid password reset token") from None
    except (OSError, ValueError):
        logger.error("Password reset persistence failed")
        raise HTTPException(
            status_code=503, detail="Password operation is temporarily unavailable"
        ) from None
    return AuthActionResponse(message="Password reset successfully")


@router.post("/change-password", response_model=AuthActionResponse)
def change_current_password(
    payload: ChangePasswordRequest, user: UserRecord = Depends(get_current_user)
) -> AuthActionResponse:
    try:
        change_password(user.id, payload.current_password, payload.new_password)
    except CurrentPasswordMismatchError:
        raise HTTPException(status_code=400, detail="Current password is incorrect") from None
    except UserNotFoundError:
        raise unauthorized() from None
    except (OSError, ValueError):
        logger.error("Password change persistence failed")
        raise HTTPException(
            status_code=503, detail="Password operation is temporarily unavailable"
        ) from None
    return AuthActionResponse(message="Password changed successfully")