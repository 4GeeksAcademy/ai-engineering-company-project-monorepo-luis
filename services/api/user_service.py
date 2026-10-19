"""Internal credential/profile operations; HTTP authorization is added in stage 4."""

from datetime import datetime, timezone

from tinydb import Query, TinyDB
from tinydb.table import Document

from services.api.auth_models import (
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserRecord,
    UserRole,
    UserUpdate,
    normalize_email,
)
from services.api.auth_storage import invalidate_password_reset_tokens, open_auth_database
from services.api.passwords import hash_password


class UserNotFoundError(ValueError):
    pass


class ProfileNotFoundError(ValueError):
    pass


class DuplicateEmailError(ValueError):
    pass


class RegistrationRoleError(ValueError):
    pass


def _next_id(database: TinyDB, table_name: str) -> int:
    metadata = database.table("auth_metadata")
    counters = dict(metadata.get(doc_id=1) or {})
    largest_id = max(
        (document.doc_id for document in database.table(table_name).all()), default=0
    )
    next_id = max(counters.get(table_name, 0), largest_id) + 1
    metadata.upsert(Document({**counters, table_name: next_id}, doc_id=1))
    return next_id


def _require_user(database: TinyDB, user_id: int) -> Document:
    document = database.table("users").get(doc_id=user_id)
    if document is None:
        raise UserNotFoundError("User not found")
    return document


def _require_profile(database: TinyDB, user_id: int) -> Document:
    document = database.table("profiles").get(Query().user_id == user_id)
    if document is None:
        raise ProfileNotFoundError("Profile not found")
    return document


def _to_user(document: Document) -> UserRecord:
    return UserRecord.model_validate({**dict(document), "id": document.doc_id})


def _to_profile(document: Document) -> ProfileResponse:
    return ProfileResponse.model_validate({**dict(document), "id": document.doc_id})


def create_user(user: UserCreate) -> UserRecord:
    if user.role != UserRole.USER:
        raise RegistrationRoleError("Public registration cannot assign privileged roles")
    hashed = hash_password(user.password)
    with open_auth_database() as database:
        users = database.table("users")
        if users.contains(Query().email == user.email):
            raise DuplicateEmailError("Email already registered")
        user_id = _next_id(database, "users")
        profile_id = _next_id(database, "profiles")
        record = {
            "email": str(user.email),
            "hashed_password": hashed.get_secret_value(),
            "is_active": True,
            "role": UserRole.USER.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        users.insert(Document(record, doc_id=user_id))
        database.table("profiles").insert(
            Document(
                {
                    "user_id": user_id,
                    "name": user.name,
                    "phone": user.phone,
                    "address": user.address,
                },
                doc_id=profile_id,
            )
        )
        return _to_user(_require_user(database, user_id))


def get_user_by_id(user_id: int) -> UserRecord:
    with open_auth_database() as database:
        return _to_user(_require_user(database, user_id))


def get_user_by_email(email: str) -> UserRecord | None:
    normalized = normalize_email(email)
    with open_auth_database() as database:
        document = database.table("users").get(Query().email == normalized)
        return _to_user(document) if document is not None else None


def list_users() -> list[UserRecord]:
    with open_auth_database() as database:
        return [_to_user(document) for document in database.table("users").all()]


def update_user(user_id: int, update: UserUpdate) -> UserRecord:
    fields = update.model_dump(mode="json", exclude_unset=True)
    if update.password is not None:
        fields["hashed_password"] = hash_password(update.password).get_secret_value()
    with open_auth_database() as database:
        _require_user(database, user_id)
        users = database.table("users")
        if update.email is not None:
            duplicate = users.get(Query().email == update.email)
            if duplicate is not None and duplicate.doc_id != user_id:
                raise DuplicateEmailError("Email already registered")
        if fields:
            users.update(fields, doc_ids=[user_id])
        if (
            update.password is not None
            or update.email is not None
            or update.is_active is False
        ):
            invalidate_password_reset_tokens(database, user_id)
        return _to_user(_require_user(database, user_id))


def delete_user(user_id: int) -> None:
    with open_auth_database() as database:
        _require_user(database, user_id)
        profile = _require_profile(database, user_id)
        database.table("profiles").remove(doc_ids=[profile.doc_id])
        database.table("users").remove(doc_ids=[user_id])
        invalidate_password_reset_tokens(database, user_id)


def get_profile_by_user_id(user_id: int) -> ProfileResponse:
    with open_auth_database() as database:
        _require_user(database, user_id)
        return _to_profile(_require_profile(database, user_id))


def update_profile(user_id: int, update: ProfileUpdate) -> ProfileResponse:
    with open_auth_database() as database:
        _require_user(database, user_id)
        profile = _require_profile(database, user_id)
        fields = update.model_dump(exclude_unset=True)
        if fields:
            database.table("profiles").update(fields, doc_ids=[profile.doc_id])
        return _to_profile(_require_profile(database, user_id))