"""Bcrypt operations without exposing plaintext or hashes in return diagnostics."""

from passlib.hash import bcrypt
from pydantic import SecretStr

from services.api.auth_models import validate_password


def hash_password(password: SecretStr) -> SecretStr:
    validate_password(password)
    return SecretStr(bcrypt.hash(password.get_secret_value()))


def verify_password(password: str, hashed_password: SecretStr) -> bool:
    if len(password.encode("utf-8")) > 72 or "\x00" in password:
        return False
    try:
        return bcrypt.verify(password, hashed_password.get_secret_value())
    except (ValueError, TypeError):
        return False