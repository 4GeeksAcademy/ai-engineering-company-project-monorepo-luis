"""Schema and bcrypt checks using synthetic credentials only."""

import unittest
from datetime import datetime, timezone

from pydantic import SecretStr, ValidationError

from services.api.auth_models import (
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserRecord,
    UserResponse,
    UserRole,
    UserUpdate,
)
from services.api.passwords import hash_password, verify_password


class TestAuthModels(unittest.TestCase):
    def test_registration_defaults_and_normalizes_email(self):
        user = UserCreate(email="  Example@EXAMPLE.COM  ", password="synthetic-password")
        self.assertEqual(user.email, "example@example.com")
        self.assertEqual(user.role, UserRole.USER)
        self.assertIsNone(user.name)
        self.assertNotIn("password", user.model_dump())
        self.assertNotIn("synthetic-password", repr(user))

    def test_roles_accept_only_declared_values(self):
        for role in UserRole:
            self.assertEqual(UserUpdate(role=role.value).role, role)
        with self.assertRaises(ValidationError):
            UserCreate(email="user@example.com", password="synthetic-password", role="owner")

    def test_server_managed_fields_are_forbidden(self):
        for field, value in (("id", 1), ("hashed_password", "hidden"), ("is_active", False), ("created_at", "now"), ("user_id", 2)):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                UserCreate.model_validate({"email": "user@example.com", "password": "synthetic-password", field: value})

    def test_profile_update_cannot_change_ownership(self):
        for field in ("id", "user_id", "email", "password", "role"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ProfileUpdate.model_validate({field: 2})

    def test_password_limits_are_measured_in_utf8_bytes(self):
        for password in ("short", "a" * 73, "\u00e9" * 37, "null\x00password"):
            with self.subTest(length=len(password)), self.assertRaises(ValidationError):
                UserCreate(email="user@example.com", password=password)
        self.assertIsInstance(UserCreate(email="user@example.com", password="\u00e9" * 36).password, SecretStr)

    def test_credential_updates_reject_null_and_contact_fields(self):
        self.assertEqual(UserUpdate().model_fields_set, set())
        for field in ("email", "password", "role", "is_active"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                UserUpdate.model_validate({field: None})
        with self.assertRaises(ValidationError):
            UserUpdate(name="Synthetic Name")
        with self.assertRaises(ValidationError):
            UserUpdate(is_active="false")

    def test_record_serialization_and_repr_hide_hashes(self):
        record = UserRecord(id=1, email="user@example.com", hashed_password="synthetic-hash", is_active=True, role=UserRole.USER, created_at=datetime.now(timezone.utc))
        self.assertNotIn("hashed_password", record.model_dump())
        self.assertNotIn("synthetic-hash", record.model_dump_json())
        self.assertNotIn("synthetic-hash", repr(record))
        self.assertEqual(UserResponse.model_validate(record.model_dump()).id, 1)
        self.assertNotIn("hashed_password", UserRecord.model_json_schema(mode="serialization")["properties"])

    def test_response_timestamp_requires_timezone(self):
        with self.assertRaises(ValidationError):
            UserResponse(id=1, email="user@example.com", is_active=True, role=UserRole.USER, created_at=datetime(2026, 10, 13))

    def test_profile_has_separate_contact_fields(self):
        profile = ProfileResponse(id=1, user_id=2, name="Synthetic Name", phone="synthetic-phone", address="synthetic-address")
        self.assertEqual(profile.user_id, 2)
        self.assertNotIn("email", profile.model_dump())

    def test_bcrypt_hash_verification_and_invalid_inputs(self):
        password = SecretStr("synthetic-password")
        hashed = hash_password(password)
        self.assertNotEqual(hashed.get_secret_value(), password.get_secret_value())
        self.assertTrue(hashed.get_secret_value().startswith("$2"))
        self.assertTrue(verify_password(password.get_secret_value(), hashed))
        self.assertFalse(verify_password("incorrect-password", hashed))
        self.assertFalse(verify_password("a" * 73, hashed))
        self.assertFalse(verify_password("synthetic-password", SecretStr("invalid-hash")))
        with self.assertRaises(ValueError):
            hash_password(SecretStr("short"))