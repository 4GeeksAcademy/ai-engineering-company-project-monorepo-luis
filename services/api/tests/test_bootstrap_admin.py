"""Offline admin provisioning on temporary synthetic databases only."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from services.api.auth_models import UserCreate, UserUpdate
from services.api.bootstrap_admin import main
from services.api.user_service import create_user, get_profile_by_user_id, get_user_by_id, update_user


class TestBootstrapAdmin(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database_path = Path(directory.name) / "auth.json"
        environment = patch.dict(os.environ, {"NEXOVA_AUTH_DB_PATH": str(self.database_path)})
        environment.start()
        self.addCleanup(environment.stop)
        self.user = create_user(UserCreate(email="admin-test@example.com", password="synthetic-password", name="Synthetic Name"))

    def arguments(self, user_id=None):
        return ["--database", str(self.database_path), "--user-id", str(user_id or self.user.id), "--confirm"]

    def invoke(self, arguments):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = main(arguments)
        self.assertNotIn("synthetic-password", output.getvalue())
        self.assertNotIn("admin-test@example.com", output.getvalue())
        self.assertNotIn("$2", output.getvalue())
        return result

    def test_promotion_is_idempotent_and_preserves_credentials_and_profile(self):
        self.assertEqual(self.invoke(self.arguments()), 0)
        promoted = get_user_by_id(self.user.id)
        self.assertEqual(promoted.role.value, "admin")
        self.assertEqual(promoted.hashed_password, self.user.hashed_password)
        self.assertEqual(get_profile_by_user_id(self.user.id).name, "Synthetic Name")
        before = self.database_path.read_bytes()
        self.assertEqual(self.invoke(self.arguments()), 0)
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_inactive_or_missing_user_is_not_promoted(self):
        update_user(self.user.id, UserUpdate(is_active=False))
        before = self.database_path.read_bytes()
        self.assertEqual(self.invoke(self.arguments()), 1)
        self.assertEqual(self.invoke(self.arguments(999)), 1)
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_missing_database_is_not_created(self):
        missing_path = self.database_path.parent / "missing.json"
        self.assertEqual(self.invoke(["--database", str(missing_path), "--user-id", "1", "--confirm"]), 1)
        self.assertFalse(missing_path.exists())

    def test_confirmation_database_and_valid_id_are_required(self):
        before = self.database_path.read_bytes()
        for arguments in ([], self.arguments()[:-1], ["--user-id", "1", "--confirm"], ["--database", str(self.database_path), "--user-id", "0", "--confirm"]):
            with self.assertRaises(SystemExit) as raised:
                self.invoke(arguments)
            self.assertEqual(raised.exception.code, 2)
        self.assertEqual(self.database_path.read_bytes(), before)

    def test_explicit_path_overrides_and_restores_environment(self):
        unrelated = str(self.database_path.parent / "unrelated.json")
        with patch.dict(os.environ, {"NEXOVA_AUTH_DB_PATH": unrelated}):
            self.assertEqual(self.invoke(self.arguments()), 0)
            self.assertEqual(os.environ["NEXOVA_AUTH_DB_PATH"], unrelated)
            self.assertFalse(Path(unrelated).exists())

    def test_installed_entrypoint_works_outside_repository_cwd(self):
        script = Path(sys.executable).parent / "promote-admin"
        if sys.platform == "win32" and not script.exists():
            script = Path(sys.executable).parent / "Scripts" / "promote-admin.exe"
        if not script.is_file():
            self.skipTest("promote-admin entrypoint is not installed in the current Python environment")
        result = subprocess.run(
            [str(script), *self.arguments()],
            cwd=self.database_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "User promoted to admin")
        self.assertEqual(get_user_by_id(self.user.id).role.value, "admin")
        self.assertNotIn("synthetic-password", result.stdout + result.stderr)

    def test_io_failure_is_generic_and_preserves_data(self):
        before = self.database_path.read_bytes()
        with patch("services.api.auth_storage.os.replace", side_effect=OSError("Synthetic failure")):
            self.assertEqual(self.invoke(self.arguments()), 1)
        self.assertEqual(self.database_path.read_bytes(), before)
