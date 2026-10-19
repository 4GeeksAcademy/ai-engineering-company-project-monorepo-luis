"""Isolated TinyDB lifecycle, persistence and failure-coordination tests."""

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from pydantic import SecretStr
from tinydb import TinyDB
from tinydb.table import Table

from services.api.auth_models import ProfileUpdate, UserCreate, UserRole, UserUpdate
from services.api.auth_storage import DEFAULT_DATABASE_PATH, get_auth_database_path
from services.api.password_reset_service import (
    InvalidPasswordResetTokenError,
    issue_password_reset_token,
    reset_password,
)
from services.api.passwords import verify_password
from services.api.user_service import (
    DuplicateEmailError,
    ProfileNotFoundError,
    RegistrationRoleError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_profile_by_user_id,
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_profile,
    update_user,
)


class TestUserService(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database_path = Path(self.directory.name) / "auth.json"
        self.environment = patch.dict(os.environ, {"NEXOVA_AUTH_DB_PATH": str(self.database_path)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def register(self, email="user@example.com", **fields):
        return create_user(UserCreate(email=email, password="synthetic-password", **fields))

    def test_storage_path_is_configurable(self):
        self.assertEqual(get_auth_database_path(), self.database_path)
        with patch.dict(os.environ, {"NEXOVA_AUTH_DB_PATH": ""}):
            self.assertEqual(get_auth_database_path(), DEFAULT_DATABASE_PATH)

    def test_registration_stores_hash_and_separates_contact(self):
        user = self.register(name="Synthetic Name", phone="synthetic-phone", address="synthetic-address")
        self.assertEqual(user.role, UserRole.USER)
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.created_at.tzinfo)
        profile = get_profile_by_user_id(user.id)
        self.assertEqual(profile.name, "Synthetic Name")
        self.assertEqual(profile.user_id, user.id)
        with TinyDB(self.database_path) as database:
            stored = database.table("users").get(doc_id=user.id)
            self.assertEqual(set(stored), {"email", "hashed_password", "is_active", "role", "created_at"})
            self.assertTrue(verify_password("synthetic-password", user.hashed_password))
            self.assertEqual(len(database.table("profiles")), 1)
        self.assertNotIn("synthetic-password", self.database_path.read_text())
        self.assertNotIn("hashed_password", user.model_dump())

    def test_registration_always_creates_empty_profile(self):
        user = self.register()
        profile = get_profile_by_user_id(user.id)
        self.assertIsNone(profile.name)
        self.assertIsNone(profile.phone)
        self.assertIsNone(profile.address)

    def test_public_registration_rejects_elevated_roles(self):
        for role in (UserRole.ADMIN, UserRole.MANAGER):
            with self.subTest(role=role), self.assertRaises(RegistrationRoleError):
                self.register(role=role)
        self.assertEqual(list_users(), [])

    def test_email_lookup_and_duplicate_are_case_insensitive(self):
        user = self.register(" Mixed@EXAMPLE.COM ")
        self.assertEqual(get_user_by_email("MIXED@example.com").id, user.id)
        self.assertIsNone(get_user_by_email("missing@example.com"))
        with self.assertRaises(DuplicateEmailError):
            self.register("mixed@example.com")
        self.assertEqual(len(list_users()), 1)

    def test_update_credentials_hashes_password_and_preserves_profile(self):
        user = self.register(name="Synthetic Name")
        updated = update_user(user.id, UserUpdate(email=" NEW@EXAMPLE.COM ", password="new-synthetic-password", role="manager", is_active=False))
        self.assertEqual(updated.email, "new@example.com")
        self.assertEqual(updated.role, UserRole.MANAGER)
        self.assertFalse(updated.is_active)
        self.assertEqual(updated.created_at, user.created_at)
        self.assertTrue(verify_password("new-synthetic-password", updated.hashed_password))
        self.assertFalse(verify_password("synthetic-password", updated.hashed_password))
        self.assertEqual(get_profile_by_user_id(user.id).name, "Synthetic Name")
        self.assertIsNone(get_user_by_email("user@example.com"))
        self.assertNotIn("new-synthetic-password", self.database_path.read_text())

    def test_duplicate_email_update_does_not_change_password(self):
        first = self.register("first@example.com")
        second = self.register("second@example.com")
        before = self.database_path.read_bytes()
        with self.assertRaises(DuplicateEmailError):
            update_user(second.id, UserUpdate(email=first.email, password="new-synthetic-password"))
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertTrue(verify_password("synthetic-password", get_user_by_id(second.id).hashed_password))

    def test_empty_update_and_reads_do_not_rewrite_file(self):
        user = self.register()
        before = self.database_path.stat().st_mtime_ns
        self.assertEqual(update_user(user.id, UserUpdate()).id, user.id)
        self.assertEqual(get_user_by_id(user.id).id, user.id)
        self.assertEqual(len(list_users()), 1)
        self.assertEqual(self.database_path.stat().st_mtime_ns, before)

    def test_profile_update_is_partial_and_can_clear_fields(self):
        user = self.register(name="Synthetic Name", phone="synthetic-phone")
        updated = update_profile(user.id, ProfileUpdate(address="synthetic-address", phone=None))
        self.assertEqual(updated.name, "Synthetic Name")
        self.assertIsNone(updated.phone)
        self.assertEqual(updated.address, "synthetic-address")
        self.assertEqual(get_user_by_id(user.id).email, user.email)

    def test_delete_cascades_and_ids_are_not_reused_after_reopen(self):
        first = self.register()
        first_profile = get_profile_by_user_id(first.id)
        delete_user(first.id)
        self.assertEqual(list_users(), [])
        second = self.register("second@example.com")
        second_profile = get_profile_by_user_id(second.id)
        self.assertGreater(second.id, first.id)
        self.assertGreater(second_profile.id, first_profile.id)
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("profiles")), 1)
            self.assertFalse(database.table("profiles").contains(doc_id=first_profile.id))
        with self.assertRaises(UserNotFoundError):
            get_user_by_id(first.id)

    def test_missing_user_operations_raise_domain_errors(self):
        operations = (
            lambda: get_user_by_id(999),
            lambda: update_user(999, UserUpdate(email="missing@example.com")),
            lambda: delete_user(999),
            lambda: get_profile_by_user_id(999),
            lambda: update_profile(999, ProfileUpdate(name="Synthetic Name")),
        )
        for operation in operations:
            with self.assertRaises(UserNotFoundError):
                operation()

    def test_profile_creation_failure_leaves_existing_database_unchanged(self):
        self.register("existing@example.com")
        before = self.database_path.read_bytes()
        original_insert = Table.insert

        def fail_profile(table, document):
            if table.name == "profiles":
                raise OSError("Synthetic profile failure")
            return original_insert(table, document)

        with patch.object(Table, "insert", autospec=True, side_effect=fail_profile):
            with self.assertRaises(OSError):
                self.register("failed@example.com")
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertIsNone(get_user_by_email("failed@example.com"))

    def test_profile_deletion_failure_preserves_user_and_profile(self):
        user = self.register()
        before = self.database_path.read_bytes()
        original_remove = Table.remove

        def fail_profile(table, cond=None, doc_ids=None):
            if table.name == "profiles":
                raise OSError("Synthetic deletion failure")
            return original_remove(table, cond=cond, doc_ids=doc_ids)

        with patch.object(Table, "remove", autospec=True, side_effect=fail_profile):
            with self.assertRaises(OSError):
                delete_user(user.id)
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertEqual(get_profile_by_user_id(user.id).user_id, user.id)

    def test_failed_file_commit_keeps_original_and_removes_temporary_file(self):
        user = self.register()
        before = self.database_path.read_bytes()
        with patch("services.api.auth_storage.os.replace", side_effect=OSError("Synthetic disk failure")):
            with self.assertRaises(OSError):
                update_profile(user.id, ProfileUpdate(name="Not committed"))
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertEqual(list(self.database_path.parent.glob(".auth-*.tmp")), [])

    def test_concurrent_duplicate_registration_has_one_profile(self):
        def register_once(_attempt):
            try:
                return self.register().id
            except DuplicateEmailError:
                return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(register_once, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("users")), 1)
            self.assertEqual(len(database.table("profiles")), 1)

    def test_missing_profile_does_not_silently_delete_user(self):
        user = self.register()
        with TinyDB(self.database_path) as database:
            database.table("profiles").truncate()
        with self.assertRaises(ProfileNotFoundError):
            delete_user(user.id)
        self.assertEqual(get_user_by_id(user.id).id, user.id)

    def test_persisted_file_remains_valid_tinydb_json(self):
        self.register()
        data = json.loads(self.database_path.read_text())
        self.assertEqual(set(data), {"users", "profiles", "auth_metadata"})

    def test_sensitive_updates_invalidate_only_own_reset(self):
        updates = (
            UserUpdate(password="new-synthetic-password"),
            UserUpdate(email="updated@example.com"),
            UserUpdate(is_active=False),
        )
        other = self.register("other@example.com")
        other_token = issue_password_reset_token(other.email)
        for index, update in enumerate(updates):
            with self.subTest(fields=update.model_fields_set):
                user = self.register(f"target{index}@example.com")
                token = issue_password_reset_token(user.email)
                update_user(user.id, update)
                with self.assertRaises(InvalidPasswordResetTokenError):
                    reset_password(token, SecretStr("reset-synthetic-password"))
        reset_password(other_token, SecretStr("reset-synthetic-password"))

    def test_unrelated_updates_preserve_pending_reset(self):
        user = self.register()
        token = issue_password_reset_token(user.email)
        update_user(user.id, UserUpdate())
        update_user(user.id, UserUpdate(role="manager"))
        update_profile(user.id, ProfileUpdate(name="Synthetic Name"))
        reset_password(token, SecretStr("reset-synthetic-password"))
        self.assertEqual(get_user_by_id(user.id).role, UserRole.MANAGER)
        self.assertEqual(get_profile_by_user_id(user.id).name, "Synthetic Name")

    def test_failed_sensitive_update_preserves_pending_reset(self):
        user = self.register()
        token = issue_password_reset_token(user.email)
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace",
            side_effect=OSError("Synthetic disk failure"),
        ), self.assertRaises(OSError):
            update_user(user.id, UserUpdate(password="new-synthetic-password"))
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("reset-synthetic-password"))

    def test_failed_deletion_preserves_pending_reset(self):
        user = self.register()
        token = issue_password_reset_token(user.email)
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace",
            side_effect=OSError("Synthetic disk failure"),
        ), self.assertRaises(OSError):
            delete_user(user.id)
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("reset-synthetic-password"))