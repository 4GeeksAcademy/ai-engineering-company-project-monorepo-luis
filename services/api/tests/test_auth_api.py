"""Real-login Bearer HTTP tests with synthetic users and temporary TinyDB."""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from jose import jwt

from services.api.auth_models import UserCreate, UserUpdate
from services.api.main import app
from services.api.user_service import create_user, delete_user, update_user


class TestAuthAPI(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.key = secrets.token_urlsafe(48)
        environment = patch.dict(os.environ, {
            "NEXOVA_AUTH_DB_PATH": os.path.join(directory.name, "auth.json"),
            "JWT_SECRET_KEY": self.key,
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.user = create_user(UserCreate(email="login@example.com", password="synthetic-password", name="Synthetic Name", phone="synthetic-phone", address="synthetic-address"))
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def login(self):
        return self.client.post("/auth/login", json={"email": "login@example.com", "password": "synthetic-password"})

    def test_json_login_and_me_return_only_public_data(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"access_token", "token_type"})
        self.assertEqual(response.json()["token_type"], "bearer")
        token = response.json()["access_token"]
        claims = jwt.decode(token, self.key, algorithms=["HS256"])
        self.assertEqual(claims["id"], self.user.id)
        me = self.client.get("/auth/me", headers={"Authorization": "Bearer " + token})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(set(me.json()), {"email", "role", "profile"})
        self.assertEqual(me.json()["profile"]["name"], "Synthetic Name")
        self.assertEqual(me.json()["profile"]["user_id"], self.user.id)
        self.assertNotIn("hashed_password", me.text)
        self.assertNotIn("synthetic-password", me.text)

    def test_oauth2_form_login_supports_swagger_username(self):
        response = self.client.post("/auth/login", data={"username": " LOGIN@EXAMPLE.COM ", "password": "synthetic-password", "grant_type": "password", "scope": ""})
        self.assertEqual(response.status_code, 200)
        me = self.client.get("/auth/me", headers={"Authorization": "Bearer " + response.json()["access_token"]})
        self.assertEqual(me.status_code, 200)

    def test_bad_credentials_have_same_generic_401(self):
        responses = [self.client.post("/auth/login", json=payload) for payload in (
            {"email": "login@example.com", "password": "wrong"},
            {"email": "missing@example.com", "password": "synthetic-password"},
            {"email": "login@example.com", "password": "a" * 73},
        )]
        update_user(self.user.id, UserUpdate(is_active=False))
        responses.append(self.login())
        for response in responses:
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
            self.assertEqual(response.json(), {"detail": "Invalid authentication credentials"})

    def test_me_rejects_missing_wrong_scheme_and_malformed_tokens(self):
        for authorization in (None, "Basic invalid", "Bearer", "Bearer malformed"):
            headers = {"Authorization": authorization} if authorization else {}
            response = self.client.get("/auth/me", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_me_rejects_expired_token(self):
        token = jwt.encode({"id": self.user.id, "exp": 1}, self.key, algorithm="HS256")
        self.assertEqual(self.client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code, 401)

    def test_me_rechecks_changed_roles_and_inactive_user(self):
        token = self.login().json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        update_user(self.user.id, UserUpdate(role="manager"))
        self.assertEqual(self.client.get("/auth/me", headers=headers).json()["role"], "manager")
        update_user(self.user.id, UserUpdate(is_active=False))
        self.assertEqual(self.client.get("/auth/me", headers=headers).status_code, 401)

    def test_deleted_user_token_is_rejected(self):
        token = self.login().json()["access_token"]
        delete_user(self.user.id)
        self.assertEqual(self.client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code, 401)

    def test_invalid_payload_errors_do_not_echo_password(self):
        for payload in (
            {"email": "invalid", "password": "synthetic-password"},
            {"email": "login@example.com"},
            {"email": "login@example.com", "password": None},
            {"email": "login@example.com", "password": "synthetic-password", "role": "admin"},
        ):
            response = self.client.post("/auth/login", json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("synthetic-password", response.text)
        malformed = self.client.post("/auth/login", content='{"password":"synthetic-password",', headers={"Content-Type": "application/json"})
        self.assertEqual(malformed.status_code, 422)
        self.assertNotIn("synthetic-password", malformed.text)

    def test_invalid_form_and_unsupported_content_are_rejected(self):
        response = self.client.post("/auth/login", data={"username": "login@example.com", "password": "synthetic-password", "grant_type": "client_credentials"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("synthetic-password", response.text)
        response = self.client.post("/auth/login", content="synthetic-password", headers={"Content-Type": "text/plain"})
        self.assertEqual(response.status_code, 415)

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

    def test_real_uvicorn_process_serves_login_and_me(self):
        with socket.socket() as server_socket:
            server_socket.bind(("127.0.0.1", 0))
            server_socket.listen(128)
            port = server_socket.getsockname()[1]
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn", "services.api.main:app",
                    "--fd", str(server_socket.fileno()), "--log-level", "error",
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
                    me = client.get("/auth/me", headers={"Authorization": "Bearer " + response.json()["access_token"]})
                    self.assertEqual(me.status_code, 200)
                    self.assertEqual(me.json()["profile"]["user_id"], self.user.id)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


class TestAuthStartup(unittest.TestCase):
    def test_startup_fails_with_missing_secret(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "", "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass

    def test_startup_fails_with_invalid_expiration(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": secrets.token_urlsafe(48), "ACCESS_TOKEN_EXPIRE_MINUTES": "0"}):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass