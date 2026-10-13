"""Credential and profile schemas for the internal authentication service."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    TypeAdapter,
    field_validator,
    model_validator,
)


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


def normalize_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("email must be a string")
    return str(TypeAdapter(EmailStr).validate_python(value.strip())).lower()


def validate_password(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    if len(password) < 8 or len(password.encode("utf-8")) > 72 or "\x00" in password:
        raise ValueError(
            "password must have at least 8 characters and at most 72 UTF-8 bytes, "
            "without null bytes"
        )
    return value


class AuthSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class ProfileUpdate(AuthSchema):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class UserCreate(ProfileUpdate):
    email: EmailStr
    password: SecretStr = Field(exclude=True, repr=False)
    role: UserRole = UserRole.USER

    @field_validator("email", mode="before")
    @classmethod
    def email_must_be_normalized(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def password_must_be_valid(cls, value: SecretStr) -> SecretStr:
        return validate_password(value)


class UserUpdate(AuthSchema):
    email: EmailStr | None = None
    password: SecretStr | None = Field(default=None, exclude=True, repr=False)
    role: UserRole | None = None
    is_active: bool | None = Field(default=None, strict=True)

    @field_validator("email", mode="before")
    @classmethod
    def email_must_be_normalized(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def password_must_be_valid(cls, value: SecretStr | None) -> SecretStr | None:
        return validate_password(value) if value is not None else None

    @model_validator(mode="after")
    def supplied_fields_must_not_be_null(self) -> "UserUpdate":
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("credential updates cannot contain null values")
        return self


class UserResponse(AuthSchema):
    id: int = Field(gt=0, strict=True)
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value.astimezone(timezone.utc)


class UserRecord(UserResponse):
    hashed_password: SecretStr = Field(exclude=True, repr=False)


class ProfileResponse(ProfileUpdate):
    id: int = Field(gt=0, strict=True)
    user_id: int = Field(gt=0, strict=True)


class LoginRequest(AuthSchema):
    email: EmailStr
    password: SecretStr = Field(exclude=True, repr=False)

    @field_validator("email", mode="before")
    @classmethod
    def email_must_be_normalized(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(AuthSchema):
    access_token: str = Field(repr=False)
    token_type: Literal["bearer"] = "bearer"


class AuthMeResponse(AuthSchema):
    email: EmailStr
    role: UserRole
    profile: ProfileResponse