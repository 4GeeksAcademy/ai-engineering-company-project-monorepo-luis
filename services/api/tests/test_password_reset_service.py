"""Password reset domain tests with synthetic users and temporary storage."""

import hashlib
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from pydantic import SecretStr
from tinydb import TinyDB

from services.api.auth_models import PasswordResetRecord, UserCreate, UserUpdate
from services.api.password_reset_service import (
    CurrentPasswordMismatchError,
    InvalidPasswordResetTokenError,
    change_password,
    issue_password_reset_token,
    reset_password,
)
from services.api.passwords import verify_password
from services.api.user_service import (
    UserNotFoundError,
    create_user,
    delete_user,
    get_user_by_id,
    update_user,
)


class TestPasswordResetService(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database_path = Path(self.directory.name) / "auth.json"
        self.environment = patch.dict(
            os.environ, {"NEXOVA_AUTH_DB_PATH": str(self.database_path)}
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.user = create_user(
            UserCreate(email="reset@example.com", password="synthetic-password")
        )

    def issue(self):
        token = issue_password_reset_token(self.user.email)
        if token is None:
            self.fail("Expected a token for the synthetic active user")
        return token

    def test_storage_contains_only_digest_and_expiration(self):
        now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        with patch("services.api.password_reset_service._utc_now", return_value=now):
            token = self.issue()
        data = json.loads(self.database_path.read_text())
        records = data["password_reset_tokens"]
        self.assertEqual(len(records), 1)
        record = next(iter(records.values()))
        self.assertEqual(set(record), {"user_id", "token_digest", "expires_at"})
        self.assertEqual(record["user_id"], self.user.id)
        expected = hashlib.sha256(token.get_secret_value().encode("ascii")).hexdigest()
        self.assertTrue(record["token_digest"] == expected)
        self.assertEqual(len(token.get_secret_value()), 43)
        self.assertTrue(token.get_secret_value() not in self.database_path.read_text())
        parsed = PasswordResetRecord.model_validate(record)
        self.assertEqual(parsed.expires_at, now + timedelta(minutes=30))
        self.assertNotIn("token_digest", parsed.model_dump())
        self.assertTrue(expected not in repr(parsed))
        self.assertTrue(token.get_secret_value() not in repr(token))

    def test_unknown_and_inactive_accounts_do_not_issue_tokens(self):
        before = self.database_path.read_bytes()
        self.assertIsNone(issue_password_reset_token("unknown@example.com"))
        self.assertEqual(self.database_path.read_bytes(), before)
        update_user(self.user.id, UserUpdate(is_active=False))
        before = self.database_path.read_bytes()
        self.assertIsNone(issue_password_reset_token(self.user.email))
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_email_lookup_is_normalized(self):
        token = issue_password_reset_token(" RESET@EXAMPLE.COM ")
        self.assertIsInstance(token, SecretStr)

    def test_lifetime_boundaries_and_exact_expiration(self):
        now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        for minutes in (15, 60):
            with self.subTest(minutes=minutes):
                with patch("services.api.password_reset_service._utc_now", return_value=now):
                    token = issue_password_reset_token(self.user.email, minutes)
                deadline = now + timedelta(minutes=minutes)
                with patch(
                    "services.api.password_reset_service._utc_now", return_value=deadline
                ), self.assertRaises(InvalidPasswordResetTokenError):
                    reset_password(token, SecretStr("new-synthetic-password"))
                with patch(
                    "services.api.password_reset_service._utc_now",
                    return_value=deadline - timedelta(microseconds=1),
                ):
                    reset_password(token, SecretStr("new-synthetic-password"))

    def test_invalid_lifetime_does_not_change_database(self):
        before = self.database_path.read_bytes()
        for lifetime in (14, 61, 0, -1, True, "30", 30.0):
            with self.subTest(lifetime=lifetime), self.assertRaises(ValueError):
                issue_password_reset_token(self.user.email, lifetime)
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_expired_token_preserves_password_and_record(self):
        now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        with patch("services.api.password_reset_service._utc_now", return_value=now):
            token = self.issue()
        before = self.database_path.read_bytes()
        with patch(
            "services.api.password_reset_service._utc_now",
            return_value=now + timedelta(minutes=31),
        ), self.assertRaises(InvalidPasswordResetTokenError):
            reset_password(token, SecretStr("new-synthetic-password"))
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_invalid_tokens_have_identical_safe_errors(self):
        token = self.issue()
        value = token.get_secret_value()
        modified = ("A" if value[0] != "A" else "B") + value[1:]
        candidates = ("", "bad", "a" * 5000, "\u00f1" * 43, "A" * 43, modified)
        before = self.database_path.read_bytes()
        for candidate in candidates:
            with self.assertRaises(InvalidPasswordResetTokenError) as context:
                reset_password(SecretStr(candidate), SecretStr("new-synthetic-password"))
            self.assertEqual(str(context.exception), "Invalid password reset token")
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_new_emission_replaces_previous_token(self):
        previous = self.issue()
        latest = self.issue()
        self.assertTrue(previous.get_secret_value() != latest.get_secret_value())
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("password_reset_tokens")), 1)
        with self.assertRaises(InvalidPasswordResetTokenError):
            reset_password(previous, SecretStr("new-synthetic-password"))
        reset_password(latest, SecretStr("new-synthetic-password"))

    def test_issuance_cleans_up_other_expired_records(self):
        now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        second = create_user(
            UserCreate(email="second@example.com", password="synthetic-password")
        )
        with patch("services.api.password_reset_service._utc_now", return_value=now):
            self.issue()
        with patch(
            "services.api.password_reset_service._utc_now",
            return_value=now + timedelta(minutes=31),
        ):
            issue_password_reset_token(second.email)
        with TinyDB(self.database_path) as database:
            records = database.table("password_reset_tokens").all()
            self.assertEqual([record["user_id"] for record in records], [second.id])

    def test_reopened_storage_retains_reset_until_consumed(self):
        token = self.issue()
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("password_reset_tokens")), 1)
        reset_password(token, SecretStr("new-synthetic-password"))
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("password_reset_tokens")), 0)

    def test_invalid_new_password_does_not_consume_token(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        for password in ("short", "a" * 73, "a" * 8 + "\x00", "\u00f1" * 37):
            with self.assertRaises(ValueError):
                reset_password(token, SecretStr(password))
            self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_failed_issuance_keeps_previous_link_valid(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace",
            side_effect=OSError("Synthetic disk failure"),
        ), self.assertRaises(OSError):
            self.issue()
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_deleted_and_inactive_accounts_cannot_reset(self):
        for operation in ("delete", "deactivate"):
            with self.subTest(operation=operation):
                user = create_user(
                    UserCreate(email=f"{operation}@example.com", password="synthetic-password")
                )
                token = issue_password_reset_token(user.email)
                with TinyDB(self.database_path) as database:
                    if operation == "delete":
                        database.table("users").remove(doc_ids=[user.id])
                    else:
                        database.table("users").update({"is_active": False}, doc_ids=[user.id])
                before = self.database_path.read_bytes()
                with self.assertRaises(InvalidPasswordResetTokenError):
                    reset_password(token, SecretStr("new-synthetic-password"))
                self.assertEqual(self.database_path.read_bytes(), before)

    def test_wrong_current_password_preserves_reset_and_credentials(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        with self.assertRaises(CurrentPasswordMismatchError):
            change_password(self.user.id, SecretStr("wrong-password"), SecretStr("changed-password"))
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_invalid_change_password_preserves_reset(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        with self.assertRaises(ValueError):
            change_password(self.user.id, SecretStr("synthetic-password"), SecretStr("short"))
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_failed_password_change_preserves_reset(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace",
            side_effect=OSError("Synthetic disk failure"),
        ), self.assertRaises(OSError):
            change_password(
                self.user.id, SecretStr("synthetic-password"), SecretStr("changed-password")
            )
        self.assertEqual(self.database_path.read_bytes(), before)
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_missing_or_inactive_user_cannot_change_password(self):
        with self.assertRaises(UserNotFoundError):
            change_password(999, SecretStr("synthetic-password"), SecretStr("changed-password"))
        update_user(self.user.id, UserUpdate(is_active=False))
        with self.assertRaises(UserNotFoundError):
            change_password(self.user.id, SecretStr("synthetic-password"), SecretStr("changed-password"))

    def test_concurrent_changes_verify_current_password_under_lock(self):
        barrier = Barrier(2)

        def change(new_password):
            barrier.wait(timeout=10)
            try:
                change_password(
                    self.user.id, SecretStr("synthetic-password"), SecretStr(new_password)
                )
                return True
            except CurrentPasswordMismatchError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(change, ["first-password", "second-password"]))
        self.assertEqual(results.count(True), 1)

    def test_user_deletion_removes_pending_reset(self):
        token = self.issue()
        delete_user(self.user.id)
        with TinyDB(self.database_path) as database:
            self.assertEqual(len(database.table("password_reset_tokens")), 0)
        with self.assertRaises(InvalidPasswordResetTokenError):
            reset_password(token, SecretStr("new-synthetic-password"))

    def test_reset_updates_password_and_consumes_token(self):
        token = self.issue()
        reset_password(token, SecretStr("new-synthetic-password"))
        current = get_user_by_id(self.user.id)
        self.assertTrue(verify_password("new-synthetic-password", current.hashed_password))
        self.assertFalse(verify_password("synthetic-password", current.hashed_password))
        before = self.database_path.read_bytes()
        with self.assertRaises(InvalidPasswordResetTokenError):
            reset_password(token, SecretStr("another-synthetic-password"))
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_concurrent_reset_has_exactly_one_success(self):
        token = self.issue()
        barrier = Barrier(2)

        def consume(password):
            barrier.wait(timeout=10)
            try:
                reset_password(token, SecretStr(password))
                return True
            except InvalidPasswordResetTokenError:
                return False

        passwords = ["first-synthetic-password", "second-synthetic-password"]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(consume, passwords))
        self.assertEqual(results.count(True), 1)
        current = get_user_by_id(self.user.id)
        for password, succeeded in zip(passwords, results):
            self.assertEqual(verify_password(password, current.hashed_password), succeeded)

    def test_failed_commit_preserves_password_and_unused_token(self):
        token = self.issue()
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace",
            side_effect=OSError("Synthetic disk failure"),
        ), self.assertRaises(OSError):
            reset_password(token, SecretStr("new-synthetic-password"))
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertEqual(list(self.database_path.parent.glob(".auth-*.tmp")), [])
        reset_password(token, SecretStr("new-synthetic-password"))

    def test_authenticated_change_invalidates_pending_reset(self):
        token = self.issue()
        change_password(
            self.user.id, SecretStr("synthetic-password"), SecretStr("changed-password")
        )
        current = get_user_by_id(self.user.id)
        self.assertTrue(verify_password("changed-password", current.hashed_password))
        with self.assertRaises(InvalidPasswordResetTokenError):
            reset_password(token, SecretStr("new-synthetic-password"))