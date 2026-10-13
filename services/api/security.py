"""Environment-only JWT configuration and signed access tokens."""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from jose import jwt
from pydantic import SecretStr

from services.api.auth_models import UserRecord

JWT_ALGORITHM = "HS256"


@dataclass(frozen=True)
class JWTSettings:
    signing_key: SecretStr = field(repr=False)
    expire_minutes: int


def load_jwt_settings() -> JWTSettings:
    signing_key = os.environ.get("JWT_SECRET_KEY", "")
    if len(signing_key.encode("utf-8")) < 32 or not signing_key.strip():
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
    try:
        expire_minutes = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", ""))
        if expire_minutes <= 0:
            raise ValueError
        datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    except (ValueError, OverflowError):
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be a positive, representable integer"
        ) from None
    return JWTSettings(SecretStr(signing_key), expire_minutes)


def create_access_token(user: UserRecord, settings: JWTSettings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "id": user.id,
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.expire_minutes),
        },
        settings.signing_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )