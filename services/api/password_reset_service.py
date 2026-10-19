"""Single-worker password recovery and coordinated credential changes."""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from pydantic import SecretStr
from tinydb import Query
from tinydb.table import Document

from services.api.auth_models import PasswordResetRecord, normalize_email
from services.api.auth_storage import invalidate_password_reset_tokens, open_auth_database
from services.api.passwords import hash_password, verify_password
from services.api.user_service import UserNotFoundError, _require_user


class InvalidPasswordResetTokenError(ValueError):
    pass


class CurrentPasswordMismatchError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _token_digest(token: SecretStr) -> str:
    value = token.get_secret_value()
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", value) is None:
        raise InvalidPasswordResetTokenError("Invalid password reset token")
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def issue_password_reset_token(
    email: str, lifetime_minutes: int = 30
) -> SecretStr | None:
    if type(lifetime_minutes) is not int or not 15 <= lifetime_minutes <= 60:
        raise ValueError("Reset lifetime must be between 15 and 60 minutes")
    normalized = normalize_email(email)
    with open_auth_database() as database:
        user = database.table("users").get(Query().email == normalized)
        if user is None or not user["is_active"]:
            return None
        now = _utc_now()
        token = SecretStr(secrets.token_urlsafe(32))
        record = PasswordResetRecord(
            user_id=user.doc_id,
            token_digest=SecretStr(_token_digest(token)),
            expires_at=now + timedelta(minutes=lifetime_minutes),
        )
        tokens = database.table("password_reset_tokens")
        tokens.remove(
            lambda document: PasswordResetRecord.model_validate(document).expires_at <= now
        )
        tokens.upsert(
            Document(
                {
                    **record.model_dump(mode="json"),
                    "token_digest": record.token_digest.get_secret_value(),
                },
                doc_id=user.doc_id,
            )
        )
        return token


def reset_password(token: SecretStr, new_password: SecretStr) -> None:
    digest = _token_digest(token)
    with open_auth_database() as database:
        record = None
        for document in database.table("password_reset_tokens").all():
            candidate = PasswordResetRecord.model_validate(document)
            if hmac.compare_digest(candidate.token_digest.get_secret_value(), digest):
                record = candidate
                break
        if record is None or record.expires_at <= _utc_now():
            raise InvalidPasswordResetTokenError("Invalid password reset token")
        try:
            user = _require_user(database, record.user_id)
        except UserNotFoundError:
            raise InvalidPasswordResetTokenError("Invalid password reset token") from None
        if not user["is_active"]:
            raise InvalidPasswordResetTokenError("Invalid password reset token")
        hashed = hash_password(new_password)
        database.table("users").update(
            {"hashed_password": hashed.get_secret_value()}, doc_ids=[record.user_id]
        )
        invalidate_password_reset_tokens(database, record.user_id)


def change_password(
    user_id: int, current_password: SecretStr, new_password: SecretStr
) -> None:
    with open_auth_database() as database:
        user = _require_user(database, user_id)
        if not user["is_active"]:
            raise UserNotFoundError("User not found")
        if not verify_password(
            current_password.get_secret_value(), SecretStr(user["hashed_password"])
        ):
            raise CurrentPasswordMismatchError("Current password is incorrect")
        hashed = hash_password(new_password)
        database.table("users").update(
            {"hashed_password": hashed.get_secret_value()}, doc_ids=[user_id]
        )
        invalidate_password_reset_tokens(database, user_id)