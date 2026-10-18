"""AUTH-03 HTTP contracts with isolated storage and an injected email sender."""

import asyncio
import json
import os
import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import httpx
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from jose import jwt

from services.api.auth_models import UserCreate, UserUpdate
from services.api.email_service import EmailDeliveryError, send_password_reset_email
from services.api.main import app
from services.api.routers.auth import get_password_reset_sender
from services.api.user_service import create_user, delete_user, update_user


class TestPasswordResetAPI(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database_path = Path(self.directory.name) / "auth.json"
        self.key = secrets.token_urlsafe(48)
        self.email_key = secrets.token_urlsafe(32)
        self.environment = patch.dict(os.environ, {
            "NEXOVA_AUTH_DB_PATH": str(self.database_path),
            "JWT_SECRET_KEY": self.key,
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "RESEND_API_KEY": self.email_key,
            "RESEND_FROM_EMAIL": "sender@example.com",
            "NEXOVA_FRONTEND_URL": "http://127.0.0.1:3000",
            "PASSWORD_RESET_EXPIRE_MINUTES": "30",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.user = create_user(
            UserCreate(email="reset@example.com", password="synthetic-password")
        )
        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_password_reset_sender] = lambda: self.deliver
        self.addCleanup(self.restore_overrides, previous)
        self.deliveries = []
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def restore_overrides(self, previous):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)

    def deliver(self, email, token, settings):
        self.deliveries.append((email, token, settings))

    def login(self, password="synthetic-password"):
        return self.client.post(
            "/auth/login", json={"email": self.user.email, "password": password}
        )

    def request_reset(self):
        response = self.client.post("/auth/forgot-password", json={"email": self.user.email})
        self.assertEqual(response.status_code, 200)
        return self.deliveries[-1][1].get_secret_value()

    def test_forgot_returns_same_response_for_existing_and_unknown(self):
        existing = self.client.post("/auth/forgot-password", json={"email": self.user.email})
        unknown = self.client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(existing.json(), unknown.json())
        self.assertEqual(set(existing.json()), {"message"})
        self.assertEqual(len(self.deliveries), 1)
        self.assertTrue(self.deliveries[0][1].get_secret_value() not in existing.text)

    def test_reset_changes_login_and_rejects_reuse(self):
        token = self.request_reset()
        response = self.client.post(
            "/auth/reset-password", json={"token": token, "new_password": "changed-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"message"})
        self.assertEqual(self.login("changed-password").status_code, 200)
        self.assertEqual(self.login().status_code, 401)
        repeat = self.client.post(
            "/auth/reset-password", json={"token": token, "new_password": "another-password"}
        )
        self.assertEqual(repeat.status_code, 400)
        self.assertEqual(repeat.json(), {"detail": "Invalid password reset token"})

    def test_missing_token_is_generic_400(self):
        response = self.client.post("/auth/reset-password", json={"new_password": "changed-password"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid password reset token"})

    def test_change_requires_bearer_and_checks_current_password(self):
        payload = {"current_password": "synthetic-password", "new_password": "changed-password"}
        self.assertEqual(self.client.post("/auth/change-password", json=payload).status_code, 401)
        headers = {"Authorization": "Bearer " + self.login().json()["access_token"]}
        wrong = self.client.post(
            "/auth/change-password", headers=headers,
            json={**payload, "current_password": "wrong-password"},
        )
        self.assertEqual(wrong.status_code, 400)
        response = self.client.post("/auth/change-password", headers=headers, json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.login("changed-password").status_code, 200)
        self.assertEqual(self.login().status_code, 401)

    def test_validation_errors_do_not_echo_secrets(self):
        token = self.request_reset()
        headers = {"Authorization": "Bearer " + self.login().json()["access_token"]}
        payloads = (
            ("/auth/forgot-password", {"email": "invalid", "password": "synthetic-password"}),
            ("/auth/reset-password", {"token": token, "new_password": "short"}),
            ("/auth/change-password", {
                "current_password": "synthetic-password", "new_password": "short",
            }),
        )
        for endpoint, payload in payloads:
            response = self.client.post(endpoint, headers=headers, json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Invalid password request"})
            for secret in (token, "synthetic-password", "short", self.key, self.email_key):
                self.assertTrue(secret not in response.text)

    def test_missing_configuration_is_common_503_and_login_still_works(self):
        for variable in ("RESEND_API_KEY", "RESEND_FROM_EMAIL", "NEXOVA_FRONTEND_URL"):
            with self.subTest(variable=variable), patch.dict(os.environ, {variable: ""}):
                responses = [self.client.post("/auth/forgot-password", json={"email": email})
                             for email in (self.user.email, "unknown@example.com")]
                self.assertEqual([response.status_code for response in responses], [503, 503])
                self.assertEqual(responses[0].json(), responses[1].json())
                self.assertTrue(self.email_key not in responses[0].text)
                self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.deliveries, [])

    def test_invalid_configuration_is_common_503(self):
        for settings in (
            {"PASSWORD_RESET_EXPIRE_MINUTES": "14"},
            {"RESEND_FROM_EMAIL": "invalid"},
            {"NEXOVA_FRONTEND_URL": "https://untrusted.example.com/path"},
        ):
            with patch.dict(os.environ, settings):
                existing = self.client.post("/auth/forgot-password", json={"email": self.user.email})
                unknown = self.client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
                self.assertEqual(existing.status_code, 503)
                self.assertEqual(unknown.status_code, 503)
                self.assertEqual(existing.json(), unknown.json())

    def test_inactive_account_matches_unknown_response_without_delivery(self):
        update_user(self.user.id, UserUpdate(is_active=False))
        inactive = self.client.post("/auth/forgot-password", json={"email": self.user.email})
        unknown = self.client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
        self.assertEqual(inactive.status_code, 200)
        self.assertEqual(inactive.json(), unknown.json())
        self.assertEqual(self.deliveries, [])

    def test_malformed_emails_and_json_are_sanitized(self):
        for email in ("invalid", None, 123):
            response = self.client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Invalid password request"})
        headers = {"Authorization": "Bearer " + self.login().json()["access_token"],
                   "Content-Type": "application/json"}
        for endpoint in ("forgot-password", "reset-password", "change-password"):
            response = self.client.post(
                f"/auth/{endpoint}", headers=headers, content='{"password":"synthetic-password",'
            )
            self.assertEqual(response.status_code, 422)
            self.assertTrue("synthetic-password" not in response.text)
        self.assertEqual(self.deliveries, [])

    def test_provider_failure_does_not_change_public_response_or_log_secrets(self):
        def fail(email, token, settings):
            raise EmailDeliveryError(token.get_secret_value() + self.email_key)

        app.dependency_overrides[get_password_reset_sender] = lambda: fail
        with self.assertLogs("services.api.routers.auth", level="ERROR") as captured:
            existing = self.client.post("/auth/forgot-password", json={"email": self.user.email})
        unknown = self.client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(existing.json(), unknown.json())
        self.assertEqual(captured.records[0].getMessage(), "Password reset request processing failed")
        self.assertIsNone(captured.records[0].exc_info)
        self.assertTrue(self.email_key not in "".join(captured.output))

    def test_background_storage_failure_is_sanitized(self):
        with patch(
            "services.api.routers.auth.issue_password_reset_token", side_effect=OSError(self.email_key)
        ), self.assertLogs("services.api.routers.auth", level="ERROR") as captured:
            response = self.client.post("/auth/forgot-password", json={"email": self.user.email})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.deliveries, [])
        self.assertTrue(self.email_key not in "".join(captured.output))

    def test_task_acceptance_failure_is_common_503(self):
        with patch.object(BackgroundTasks, "add_task", side_effect=RuntimeError(self.email_key)):
            responses = [self.client.post("/auth/forgot-password", json={"email": email})
                         for email in (self.user.email, "unknown@example.com")]
        self.assertEqual([response.status_code for response in responses], [503, 503])
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertTrue(self.email_key not in responses[0].text)
        self.assertEqual(self.deliveries, [])

    def test_account_lookup_occurs_after_public_response_body(self):
        events = []
        body = json.dumps({"email": self.user.email}).encode()
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/auth/forgot-password",
            "raw_path": b"/auth/forgot-password", "root_path": "", "query_string": b"",
            "headers": [(b"content-type", b"application/json"), (b"host", b"testserver")],
            "server": ("testserver", 80), "client": ("127.0.0.1", 12345),
        }

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            events.append(message["type"])

        from services.api.password_reset_service import issue_password_reset_token

        def lookup(email, minutes):
            self.assertIn("http.response.body", events)
            events.append("account.lookup")
            return issue_password_reset_token(email, minutes)

        with patch("services.api.routers.auth.issue_password_reset_token", side_effect=lookup):
            asyncio.run(app(scope, receive, send))
        self.assertLess(events.index("http.response.body"), events.index("account.lookup"))
        self.assertEqual(len(self.deliveries), 1)

    def test_forgot_uses_injected_resend_transport_and_canonical_email(self):
        requests = []

        def accept(request):
            requests.append(request)
            return httpx.Response(200, json={"id": "synthetic-message"})

        def sender(email, token, settings):
            send_password_reset_email(email, token, settings, transport=httpx.MockTransport(accept))

        app.dependency_overrides[get_password_reset_sender] = lambda: sender
        response = self.client.post("/auth/forgot-password", json={"email": " RESET@EXAMPLE.COM "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(requests), 1)
        self.assertEqual(json.loads(requests[0].content)["to"], [self.user.email])
        self.assertTrue("reset-password?token=" in json.loads(requests[0].content)["text"])

    def test_expired_and_manipulated_tokens_have_same_400(self):
        now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        with patch("services.api.password_reset_service._utc_now", return_value=now):
            token = self.request_reset()
        with patch(
            "services.api.password_reset_service._utc_now", return_value=now + timedelta(minutes=30)
        ):
            expired = self.client.post(
                "/auth/reset-password", json={"token": token, "new_password": "changed-password"}
            )
        for candidate in (None, 123, "", "invalid", "A" * 43):
            response = self.client.post(
                "/auth/reset-password", json={"token": candidate, "new_password": "changed-password"}
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), expired.json())
        self.assertEqual(expired.status_code, 400)
        self.assertEqual(self.login().status_code, 200)

    def test_jwt_and_reset_tokens_cannot_be_used_interchangeably(self):
        access = self.login().json()["access_token"]
        reset = self.request_reset()
        response = self.client.post(
            "/auth/reset-password", json={"token": access, "new_password": "changed-password"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(access not in response.text)
        response = self.client.get("/auth/me", headers={"Authorization": "Bearer " + reset})
        self.assertEqual(response.status_code, 401)

    def test_change_rejects_invalid_expired_and_wrong_scheme_bearer(self):
        expired = jwt.encode({"id": self.user.id, "exp": 1}, self.key, algorithm="HS256")
        for authorization in ("Bearer invalid", "Basic invalid", "Bearer " + expired):
            response = self.client.post(
                "/auth/change-password", headers={"Authorization": authorization},
                json={"current_password": "synthetic-password", "new_password": "changed-password"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_change_cannot_target_another_user(self):
        other = create_user(UserCreate(email="other@example.com", password="synthetic-password"))
        headers = {"Authorization": "Bearer " + self.login().json()["access_token"]}
        payload = {"current_password": "synthetic-password", "new_password": "changed-password"}
        response = self.client.post(
            "/auth/change-password", headers=headers, json={**payload, "user_id": other.id}
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post("/auth/change-password", headers=headers, json=payload).status_code, 200)
        response = self.client.post(
            "/auth/login", json={"email": other.email, "password": "synthetic-password"}
        )
        self.assertEqual(response.status_code, 200)

    def test_concurrent_http_consumption_has_one_success(self):
        token = self.request_reset()
        barrier = Barrier(2)

        def consume(password):
            barrier.wait(timeout=10)
            return self.client.post(
                "/auth/reset-password", json={"token": token, "new_password": password}
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(consume, ["first-password", "second-password"]))
        self.assertEqual(sorted(statuses), [200, 400])

    def test_reset_disk_failure_is_503_and_keeps_token_valid(self):
        token = self.request_reset()
        payload = {"token": token, "new_password": "changed-password"}
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace", side_effect=OSError(self.email_key)
        ), self.assertLogs("services.api.routers.auth", level="ERROR") as captured:
            response = self.client.post("/auth/reset-password", json=payload)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertTrue(self.email_key not in "".join(captured.output))
        self.assertTrue(token not in response.text)
        self.assertEqual(self.client.post("/auth/reset-password", json=payload).status_code, 200)

    def test_change_disk_failure_is_503_without_partial_update(self):
        headers = {"Authorization": "Bearer " + self.login().json()["access_token"]}
        before = self.database_path.read_bytes()
        with patch(
            "services.api.auth_storage.os.replace", side_effect=OSError(self.email_key)
        ), self.assertLogs("services.api.routers.auth", level="ERROR"):
            response = self.client.post(
                "/auth/change-password", headers=headers,
                json={"current_password": "synthetic-password", "new_password": "changed-password"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertTrue(self.email_key not in response.text)
        self.assertEqual(self.login().status_code, 200)

    def test_deleted_or_inactive_user_token_is_rejected(self):
        token = self.request_reset()
        update_user(self.user.id, UserUpdate(is_active=False))
        payload = {"token": token, "new_password": "changed-password"}
        self.assertEqual(self.client.post("/auth/reset-password", json=payload).status_code, 400)
        update_user(self.user.id, UserUpdate(is_active=True))
        token = self.request_reset()
        delete_user(self.user.id)
        self.assertEqual(self.client.post(
            "/auth/reset-password", json={**payload, "token": token}
        ).status_code, 400)

    def test_openapi_has_public_recovery_and_protected_change(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertNotIn("security", paths["/auth/forgot-password"]["post"])
        self.assertNotIn("security", paths["/auth/reset-password"]["post"])
        self.assertIn("security", paths["/auth/change-password"]["post"])