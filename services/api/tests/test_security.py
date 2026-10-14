"""JWT configuration and identity checks with disposable synthetic values."""

import os
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from jose import jwt

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import UserCreate, UserUpdate
from services.api.security import JWT_ALGORITHM, create_access_token, load_jwt_settings
from services.api.user_service import create_user, delete_user, update_user


class TestJWTSettings(unittest.TestCase):
    def test_valid_settings_hide_key(self):
        key = secrets.token_urlsafe(48)
        with patch.dict(os.environ, {"JWT_SECRET_KEY": key, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}):
            settings = load_jwt_settings()
        self.assertEqual(settings.expire_minutes, 15)
        self.assertNotIn(key, repr(settings))

    def test_missing_blank_or_short_secret_fails_without_disclosure(self):
        for key in ("", "short", " " * 32):
            with patch.dict(os.environ, {"JWT_SECRET_KEY": key, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}):
                with self.assertRaises(RuntimeError) as raised:
                    load_jwt_settings()
                self.assertEqual(str(raised.exception), "JWT_SECRET_KEY must contain at least 32 bytes")

    def test_expiration_must_be_positive_and_representable(self):
        for minutes in ("", "0", "-1", "nan", "inf", "1.5", "9" * 100):
            with patch.dict(os.environ, {"JWT_SECRET_KEY": secrets.token_urlsafe(48), "ACCESS_TOKEN_EXPIRE_MINUTES": minutes}):
                with self.assertRaises(RuntimeError):
                    load_jwt_settings()


class TestJWTIdentity(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {
            "NEXOVA_AUTH_DB_PATH": os.path.join(directory.name, "auth.json"),
            "JWT_SECRET_KEY": secrets.token_urlsafe(48),
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.settings = load_jwt_settings()
        self.user = create_user(UserCreate(email="jwt@example.com", password="synthetic-password"))

    def token(self, claims, key=None, algorithm=JWT_ALGORITHM):
        return jwt.encode(claims, key or self.settings.signing_key.get_secret_value(), algorithm=algorithm)

    def assert_unauthorized(self, token):
        with self.assertRaises(HTTPException) as raised:
            get_current_user(token, self.settings)
        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.headers, {"WWW-Authenticate": "Bearer"})

    def test_generated_token_has_identity_and_finite_expiration(self):
        token = create_access_token(self.user, self.settings)
        claims = jwt.decode(token, self.settings.signing_key.get_secret_value(), algorithms=[JWT_ALGORITHM])
        self.assertEqual(claims["id"], self.user.id)
        self.assertEqual(claims["sub"], str(self.user.id))
        self.assertEqual(claims["exp"] - claims["iat"], 15 * 60)
        self.assertNotIn("role", claims)
        self.assertNotIn("hashed_password", claims)
        self.assertEqual(get_current_user(token, self.settings).id, self.user.id)

    def test_missing_malformed_expired_or_wrong_signature_is_401(self):
        expiration = datetime.now(timezone.utc) + timedelta(minutes=1)
        for token in (None, "", "malformed", self.token({"id": self.user.id, "exp": 1}), self.token({"id": self.user.id, "exp": expiration}, key=secrets.token_urlsafe(48))):
            self.assert_unauthorized(token)

    def test_missing_or_invalid_identity_and_expiration_are_401(self):
        expiration = datetime.now(timezone.utc) + timedelta(minutes=1)
        for user_id in (None, True, 0, -1, "1", 1.5, []):
            self.assert_unauthorized(self.token({"id": user_id, "exp": expiration}))
        self.assert_unauthorized(self.token({"id": self.user.id}))
        self.assert_unauthorized(self.token({"id": self.user.id, "exp": "invalid"}))
        self.assert_unauthorized(self.token({"id": self.user.id, "sub": "999", "exp": expiration}))

    def test_unapproved_algorithm_is_401(self):
        token = self.token({"id": self.user.id, "exp": datetime.now(timezone.utc) + timedelta(minutes=1)}, algorithm="HS384")
        self.assert_unauthorized(token)

    def test_user_state_and_role_are_read_from_tinydb(self):
        token = create_access_token(self.user, self.settings)
        update_user(self.user.id, UserUpdate(role="manager"))
        self.assertEqual(get_current_user(token, self.settings).role.value, "manager")
        update_user(self.user.id, UserUpdate(is_active=False))
        self.assert_unauthorized(token)

    def test_deleted_or_missing_user_is_401(self):
        token = create_access_token(self.user, self.settings)
        delete_user(self.user.id)
        self.assert_unauthorized(token)
        self.assert_unauthorized(self.token({"id": 999, "exp": datetime.now(timezone.utc) + timedelta(minutes=1)}))