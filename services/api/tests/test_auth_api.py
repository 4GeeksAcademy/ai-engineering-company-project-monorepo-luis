"""Business-logic, edge-case, and failure-mode unit tests for all authentication endpoints (AUTH-088).

This test suite covers all 5 authentication endpoints defined under `/auth/*`:
  1. POST /auth/login
  2. GET /auth/me
  3. POST /auth/forgot-password
  4. POST /auth/reset-password
  5. POST /auth/change-password
"""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import SecretStr

from services.api.auth_models import UserCreate, UserUpdate
from services.api.email_service import PasswordResetSettings
from services.api.main import app
from services.api.password_reset_service import (
    issue_password_reset_token,
)
from services.api.routers.auth import (
    get_password_reset_sender,
    get_password_reset_settings,
)
from services.api.user_service import (
    ProfileNotFoundError,
    create_user,
    delete_user,
    update_user,
)


class BaseAuthAPITestCase(unittest.TestCase):
    """Base setup with temporary isolated database, JWT secrets and mock email sender."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.key = secrets.token_urlsafe(48)
        self.email_key = secrets.token_urlsafe(32)
        self.database_path = os.path.join(self.directory.name, "auth.json")

        self.environment = patch.dict(
            os.environ,
            {
                "NEXOVA_AUTH_DB_PATH": self.database_path,
                "JWT_SECRET_KEY": self.key,
                "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
                "RESEND_API_KEY": self.email_key,
                "RESEND_FROM_EMAIL": "sender@example.com",
                "NEXOVA_FRONTEND_URL": "http://127.0.0.1:3000",
                "PASSWORD_RESET_EXPIRE_MINUTES": "30",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

        # In-memory record of dispatched emails
        self.deliveries = []

        def mock_sender(email, token, settings):
            self.deliveries.append((email, token, settings))

        # Backup & override FastAPI dependencies
        previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_password_reset_sender] = lambda: mock_sender
        self.addCleanup(self._restore_overrides, previous_overrides)

        # Create baseline synthetic user
        self.user = create_user(
            UserCreate(
                email="login@example.com",
                password="synthetic-password",
                name="Synthetic Name",
                phone="synthetic-phone",
                address="synthetic-address",
            )
        )

        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def _restore_overrides(self, previous):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)

    def login(self, email="login@example.com", password="synthetic-password"):
        return self.client.post("/auth/login", json={"email": email, "password": password})


# ==============================================================================
# 1. POST /auth/login
# ==============================================================================
class TestAuthLoginEndpoint(BaseAuthAPITestCase):
    """Business logic tests for POST /auth/login (happy path, edge case, failure mode)."""

    def test_login_happy_path_json(self):
        """Happy path: valid credentials produce bearer access token with valid claims."""
        response = self.login()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("token_type"), "bearer")
        self.assertIn("access_token", data)

        claims = jwt.decode(data["access_token"], self.key, algorithms=["HS256"])
        self.assertEqual(claims["id"], self.user.id)
        self.assertEqual(claims["sub"], str(self.user.id))

    def test_login_happy_path_oauth2_form(self):
        """Happy path: valid credentials supplied as OAuth2 x-www-form-urlencoded."""
        response = self.client.post(
            "/auth/login",
            data={
                "username": "login@example.com",
                "password": "synthetic-password",
                "grant_type": "password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_login_edge_case_content_type_with_charset(self):
        """Edge case: Content-Type header with extra parameters (charset) is supported."""
        response = self.client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "synthetic-password"},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_login_edge_case_whitespace_and_uppercase_email(self):
        """Edge case: email with surrounding spaces and uppercase letters is normalized."""
        response = self.client.post(
            "/auth/login",
            data={
                "username": "  LOGIN@EXAMPLE.COM  ",
                "password": "synthetic-password",
                "grant_type": "password",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_login_failure_invalid_password(self):
        """Failure mode: wrong password returns generic 401 without timing/credential leak."""
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(response.json(), {"detail": "Invalid authentication credentials"})

    def test_login_failure_unknown_user(self):
        """Failure mode: non-existent email returns identical generic 401."""
        response = self.login(email="unknown@example.com")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid authentication credentials"})

    def test_login_failure_inactive_user(self):
        """Failure mode: deactivated user returns 401."""
        update_user(self.user.id, UserUpdate(is_active=False))
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid authentication credentials"})

    def test_login_failure_unsupported_content_type(self):
        """Failure mode: unsupported media type returns 415."""
        response = self.client.post(
            "/auth/login",
            content="email=login@example.com",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["detail"], "Unsupported login content type")

    def test_login_failure_malformed_payload(self):
        """Failure mode: invalid payload format returns 422 without echoing password."""
        response = self.client.post(
            "/auth/login",
            json={"email": "invalid-email-format", "password": "short"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("short", response.text)


# ==============================================================================
# 2. GET /auth/me
# ==============================================================================
class TestAuthMeEndpoint(BaseAuthAPITestCase):
    """Business logic tests for GET /auth/me (happy path, edge case, failure mode)."""

    def test_me_happy_path(self):
        """Happy path: valid bearer token returns authenticated user and business profile."""
        token = self.login().json()["access_token"]
        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "login@example.com")
        self.assertEqual(data["role"], "user")
        self.assertEqual(data["profile"]["name"], "Synthetic Name")
        self.assertEqual(data["profile"]["user_id"], self.user.id)
        self.assertNotIn("hashed_password", response.text)

    def test_me_edge_case_orphan_profile_returns_404(self):
        """Edge case: valid authenticated user whose profile record is missing returns 404."""
        token = self.login().json()["access_token"]
        with patch("services.api.routers.auth.get_profile_by_user_id", side_effect=ProfileNotFoundError("Missing")):
            response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["detail"], "Profile not found")

    def test_me_edge_case_role_dynamically_reflected(self):
        """Edge case: token remains valid while database role changes take effect immediately."""
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        update_user(self.user.id, UserUpdate(role="admin"))
        response = self.client.get("/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "admin")

    def test_me_failure_missing_or_bad_authorization_header(self):
        """Failure mode: missing, non-bearer, or empty Authorization header returns 401."""
        for auth_header in (None, "", "Basic invalid", "Bearer", "Bearer malformed.token"):
            headers = {"Authorization": auth_header} if auth_header is not None else {}
            response = self.client.get("/auth/me", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_failure_expired_token(self):
        """Failure mode: expired JWT is rejected with 401."""
        expired_token = jwt.encode({"id": self.user.id, "exp": 1}, self.key, algorithm="HS256")
        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(response.status_code, 401)

    def test_me_failure_deleted_user(self):
        """Failure mode: user deleted from database after token issuance is rejected."""
        token = self.login().json()["access_token"]
        delete_user(self.user.id)
        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)


# ==============================================================================
# 3. POST /auth/forgot-password
# ==============================================================================
class TestAuthForgotPasswordEndpoint(BaseAuthAPITestCase):
    """Business logic tests for POST /auth/forgot-password (happy path, edge case, failure mode)."""

    def test_forgot_password_happy_path(self):
        """Happy path: registered email queues background reset email and returns safe message."""
        response = self.client.post(
            "/auth/forgot-password",
            json={"email": "login@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("recibirás un enlace", response.json()["message"])

        # Check delivery mock was invoked with valid token
        self.assertEqual(len(self.deliveries), 1)
        recipient, token, _ = self.deliveries[0]
        self.assertEqual(recipient, "login@example.com")
        self.assertEqual(len(token.get_secret_value()), 43)

    def test_forgot_password_edge_case_unknown_or_inactive_user_prevents_enumeration(self):
        """Edge case: unknown or inactive email returns IDENTICAL message without sending email."""
        for email in ("unknown@example.com", "other@example.com"):
            response = self.client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(response.status_code, 200)
            self.assertIn("recibirás un enlace", response.json()["message"])

        # Deactivated user should also not receive email
        update_user(self.user.id, UserUpdate(is_active=False))
        response = self.client.post("/auth/forgot-password", json={"email": "login@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.deliveries), 0)

    def test_forgot_password_failure_service_unavailable(self):
        """Failure mode: misconfigured settings returns 503 Service Unavailable."""
        with patch("services.api.routers.auth.load_password_reset_settings", side_effect=RuntimeError("Settings failure")):
            response = self.client.post("/auth/forgot-password", json={"email": "login@example.com"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], "Password recovery is temporarily unavailable")

    def test_forgot_password_failure_invalid_email_format(self):
        """Failure mode: malformed email string returns 422."""
        response = self.client.post("/auth/forgot-password", json={"email": "not-an-email"})
        self.assertEqual(response.status_code, 422)


# ==============================================================================
# 4. POST /auth/reset-password
# ==============================================================================
class TestAuthResetPasswordEndpoint(BaseAuthAPITestCase):
    """Business logic tests for POST /auth/reset-password (happy path, edge case, failure mode)."""

    def test_reset_password_happy_path(self):
        """Happy path: valid token resets password, allows new login, and prevents token replay."""
        token = issue_password_reset_token("login@example.com", 30)
        self.assertIsNotNone(token)

        response = self.client.post(
            "/auth/reset-password",
            json={"token": token.get_secret_value(), "new_password": "new-strong-password123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password reset successfully")

        # Verify old password no longer works
        old_login = self.login(password="synthetic-password")
        self.assertEqual(old_login.status_code, 401)

        # Verify new password allows login
        new_login = self.login(password="new-strong-password123")
        self.assertEqual(new_login.status_code, 200)

        # Verify token replay is rejected
        replay_response = self.client.post(
            "/auth/reset-password",
            json={"token": token.get_secret_value(), "new_password": "another-password123"},
        )
        self.assertEqual(replay_response.status_code, 400)
        self.assertEqual(replay_response.json()["detail"], "Invalid password reset token")

    def test_reset_password_edge_case_boundary_password_length(self):
        """Edge case: exactly 8 characters (minimum boundary) is accepted."""
        token = issue_password_reset_token("login@example.com", 30)
        response = self.client.post(
            "/auth/reset-password",
            json={"token": token.get_secret_value(), "new_password": "eight_ch"},
        )
        self.assertEqual(response.status_code, 200)

    def test_reset_password_failure_invalid_or_manipulated_token(self):
        """Failure mode: invalid, corrupted, or non-existent token returns 400."""
        for bad_token in ("invalid-token-string", secrets.token_urlsafe(32)):
            response = self.client.post(
                "/auth/reset-password",
                json={"token": bad_token, "new_password": "new-password123"},
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["detail"], "Invalid password reset token")

    def test_reset_password_failure_short_password(self):
        """Failure mode: password with less than 8 characters returns 422 without echoing."""
        token = issue_password_reset_token("login@example.com", 30)
        response = self.client.post(
            "/auth/reset-password",
            json={"token": token.get_secret_value(), "new_password": "short"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("short", response.text)

    def test_reset_password_failure_storage_io_error(self):
        """Failure mode: persistence storage failure returns 503."""
        token = issue_password_reset_token("login@example.com", 30)
        with patch("services.api.routers.auth.reset_password", side_effect=OSError("Disk full")):
            response = self.client.post(
                "/auth/reset-password",
                json={"token": token.get_secret_value(), "new_password": "new-password123"},
            )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], "Password operation is temporarily unavailable")


# ==============================================================================
# 5. POST /auth/change-password
# ==============================================================================
class TestAuthChangePasswordEndpoint(BaseAuthAPITestCase):
    """Business logic tests for POST /auth/change-password (happy path, edge case, failure mode)."""

    def test_change_password_happy_path(self):
        """Happy path: authenticated user with correct current password successfully updates credentials."""
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = self.client.post(
            "/auth/change-password",
            headers=headers,
            json={
                "current_password": "synthetic-password",
                "new_password": "brand-new-password123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password changed successfully")

        # Verify old password is now invalid
        self.assertEqual(self.login(password="synthetic-password").status_code, 401)

        # Verify new password works
        self.assertEqual(self.login(password="brand-new-password123").status_code, 200)

    def test_change_password_edge_case_boundary_password_length(self):
        """Edge case: exactly 8 characters for new password boundary is accepted."""
        token = self.login().json()["access_token"]
        response = self.client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "synthetic-password",
                "new_password": "eight_ch",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_change_password_failure_unauthenticated(self):
        """Failure mode: missing or invalid bearer token returns 401."""
        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "synthetic-password",
                "new_password": "new-password123",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_change_password_failure_incorrect_current_password(self):
        """Failure mode: wrong current password returns 400 without changing credentials."""
        token = self.login().json()["access_token"]
        response = self.client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrong-current-password",
                "new_password": "new-password123",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Current password is incorrect")

        # Confirm old password remains intact
        self.assertEqual(self.login(password="synthetic-password").status_code, 200)

    def test_change_password_failure_user_not_found(self):
        """Failure mode: user deleted after token issuance returns 401."""
        token = self.login().json()["access_token"]
        delete_user(self.user.id)

        response = self.client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "synthetic-password",
                "new_password": "new-password123",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_change_password_failure_short_new_password(self):
        """Failure mode: new password shorter than 8 characters returns 422."""
        token = self.login().json()["access_token"]
        response = self.client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "synthetic-password",
                "new_password": "short",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("short", response.text)

    def test_change_password_failure_storage_io_error(self):
        """Failure mode: persistence failure returns 503."""
        token = self.login().json()["access_token"]
        with patch("services.api.routers.auth.change_password", side_effect=OSError("Disk failure")):
            response = self.client.post(
                "/auth/change-password",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "current_password": "synthetic-password",
                    "new_password": "new-password123",
                },
            )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], "Password operation is temporarily unavailable")


# ==============================================================================
# 6. OpenAPI contract & subprocess verification
# ==============================================================================
class TestAuthContractsAndProcess(BaseAuthAPITestCase):
    def test_openapi_documents_both_login_formats_and_oauth2(self):
        schema = self.client.get("/openapi.json").json()
        content = schema["paths"]["/auth/login"]["post"]["requestBody"]["content"]
        self.assertEqual(set(content), {"application/json", "application/x-www-form-urlencoded"})
        self.assertIn("password", content["application/json"]["schema"]["properties"])
        scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
        self.assertEqual(scheme["flows"]["password"]["tokenUrl"], "/auth/login")
        self.assertIn("security", schema["paths"]["/auth/me"]["get"])
        self.assertNotIn("security", schema["paths"]["/auth/login"]["post"])
        self.assertNotIn("hashed_password", str(schema))
        self.assertEqual(self.client.get("/health").status_code, 200)

    @unittest.skipIf(sys.platform == "win32", "pass_fds not supported on Windows")
    def test_real_uvicorn_process_serves_login_and_me(self):
        with socket.socket() as server_socket:
            server_socket.bind(("127.0.0.1", 0))
            server_socket.listen(128)
            port = server_socket.getsockname()[1]
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "services.api.main:app",
                    "--fd",
                    str(server_socket.fileno()),
                    "--log-level",
                    "error",
                    "--no-access-log",
                ],
                cwd=Path(__file__).resolve().parents[3],
                pass_fds=(server_socket.fileno(),),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
                    self.assertEqual(client.get("/health").status_code, 200)
                    self.assertEqual(client.get("/docs").status_code, 200)
                    self.assertEqual(client.get("/auth/me").status_code, 401)
                    response = client.post(
                        "/auth/login",
                        json={"email": "login@example.com", "password": "synthetic-password"},
                        headers={"Content-Type": "application/json ; charset=utf-8"},
                    )
                    self.assertEqual(response.status_code, 200)
                    me = client.get(
                        "/auth/me",
                        headers={"Authorization": "Bearer " + response.json()["access_token"]},
                    )
                    self.assertEqual(me.status_code, 200)
                    self.assertEqual(me.json()["profile"]["user_id"], self.user.id)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


# ==============================================================================
# 7. Environment configuration failure at startup
# ==============================================================================
class TestAuthStartup(unittest.TestCase):
    def test_startup_fails_with_missing_secret(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "", "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass

    def test_startup_fails_with_invalid_expiration(self):
        with patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": secrets.token_urlsafe(48), "ACCESS_TOKEN_EXPIRE_MINUTES": "0"},
        ):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass
