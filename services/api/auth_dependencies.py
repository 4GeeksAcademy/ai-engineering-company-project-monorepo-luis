"""Reusable Bearer authentication using the current TinyDB user record."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from services.api.auth_models import UserRecord
from services.api.security import JWT_ALGORITHM, JWTSettings
from services.api.user_service import UserNotFoundError, get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_settings(request: Request) -> JWTSettings:
    settings = getattr(request.app.state, "jwt_settings", None)
    if settings is None:
        raise RuntimeError("JWT configuration has not been initialized at startup")
    return settings


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    settings: JWTSettings = Depends(get_auth_settings),
) -> UserRecord:
    if not token:
        raise unauthorized()
    try:
        claims = jwt.decode(
            token,
            settings.signing_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True},
        )
        user_id = claims.get("id")
        if type(user_id) is not int or user_id <= 0:
            raise unauthorized()
        if "sub" in claims and claims["sub"] != str(user_id):
            raise unauthorized()
        user = get_user_by_id(user_id)
        if not user.is_active:
            raise unauthorized()
        return user
    except (JWTError, ValueError, TypeError, OverflowError, UserNotFoundError):
        raise unauthorized() from None