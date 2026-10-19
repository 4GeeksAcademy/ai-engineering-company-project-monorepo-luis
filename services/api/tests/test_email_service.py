"""Resend configuration and transport tests without network or real credentials."""

import json
import os
import secrets
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
from pydantic import SecretStr

from services.api.email_service import (
    EmailDeliveryError,
    load_password_reset_settings,
    send_password_reset_email,
)


class TestEmailService(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_urlsafe(32)
        self.environment = patch.dict(os.environ, {
            "RESEND_API_KEY": self.key,
            "RESEND_FROM_EMAIL": "sender@example.com",
            "NEXOVA_FRONTEND_URL": "http://127.0.0.1:3000",
            "PASSWORD_RESET_EXPIRE_MINUTES": "30",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_email_payload_has_functional_link_and_secret_header_only(self):
        settings = load_password_reset_settings()
        token = SecretStr(secrets.token_urlsafe(32))

        def receive(request):
            self.assertEqual(str(request.url), "https://api.resend.com/emails")
            self.assertTrue(request.headers["Authorization"] == f"Bearer {self.key}")
            self.assertEqual(request.extensions["timeout"]["read"], 10.0)
            body = json.loads(request.content)
            self.assertEqual(body["from"], "sender@example.com")
            self.assertEqual(body["to"], ["recipient@example.com"])
            self.assertTrue(self.key not in body["text"])
            link = next(line for line in body["text"].splitlines() if line.startswith("http"))
            parsed = urlsplit(link)
            self.assertEqual(parsed.path, "/reset-password")
            self.assertTrue(parse_qs(parsed.query)["token"] == [token.get_secret_value()])
            return httpx.Response(200, json={"id": "synthetic-message-id"})

        send_password_reset_email(
            "recipient@example.com", token, settings, transport=httpx.MockTransport(receive)
        )
        self.assertTrue(self.key not in repr(settings))

    def test_provider_errors_are_sanitized_and_redirects_not_followed(self):
        for status in (302, 401, 429, 500):
            requests = []

            def fail(request):
                requests.append(request)
                return httpx.Response(
                    status,
                    headers={"Location": "https://untrusted.example.com"},
                    text=self.key,
                )

            with self.subTest(status=status), self.assertRaises(EmailDeliveryError) as context:
                send_password_reset_email(
                    "recipient@example.com", SecretStr("synthetic-token"),
                    load_password_reset_settings(), transport=httpx.MockTransport(fail),
                )
            self.assertEqual(len(requests), 1)
            self.assertEqual(str(context.exception), "Password reset email delivery failed")

    def test_timeout_is_sanitized(self):
        def timeout(request):
            raise httpx.ReadTimeout(self.key, request=request)

        with self.assertRaises(EmailDeliveryError) as context:
            send_password_reset_email(
                "recipient@example.com", SecretStr("synthetic-token"),
                load_password_reset_settings(), transport=httpx.MockTransport(timeout),
            )
        self.assertEqual(str(context.exception), "Password reset email delivery failed")
        self.assertTrue(context.exception.__suppress_context__)

    def test_invalid_settings_are_rejected_without_echoing_values(self):
        invalid = {
            "RESEND_API_KEY": ("", "bad key", "bad\x01key", "bad\u00f1key"),
            "RESEND_FROM_EMAIL": ("", "invalid", "name\r\n@example.com"),
            "NEXOVA_FRONTEND_URL": (
                "", "javascript:invalid", "http://example.com", "https://user:secret@example.com",
                "https://example.com/path", "https://example.com?token=secret",
                "https://example.com/#secret", "https://example.com:0",
            ),
            "PASSWORD_RESET_EXPIRE_MINUTES": ("", "14", "61", "true", "30.0"),
        }
        for name, values in invalid.items():
            for value in values:
                with self.subTest(variable=name), patch.dict(os.environ, {name: value}):
                    with self.assertRaises(RuntimeError) as context:
                        load_password_reset_settings()
                    self.assertEqual(str(context.exception), "Invalid password reset configuration")

    def test_defaults_and_supported_origins(self):
        os.environ.pop("PASSWORD_RESET_EXPIRE_MINUTES", None)
        self.assertEqual(load_password_reset_settings().expire_minutes, 30)
        for origin in ("https://example.com/", "http://localhost:3000", "http://[::1]:3000"):
            with patch.dict(os.environ, {"NEXOVA_FRONTEND_URL": origin}):
                self.assertEqual(load_password_reset_settings().frontend_url, origin.rstrip("/"))
        for minutes in ("15", "60"):
            with patch.dict(os.environ, {"PASSWORD_RESET_EXPIRE_MINUTES": minutes}):
                self.assertEqual(load_password_reset_settings().expire_minutes, int(minutes))