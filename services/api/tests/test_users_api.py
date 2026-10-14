"""HTTP authorization tests for user credentials and self-owned profiles."""

import os
import secrets
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.auth_models import UserCreate, UserRole, UserUpdate
from services.api.auth_storage import open_auth_database
from services.api.main import app
from services.api.user_service import create_user, get_profile_by_user_id, update_user


class TestUsersAPI(unittest.TestCase):
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
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.owner = self.register("owner@example.com", "Owner")
        self.other = self.register("other@example.com", "Other")
        self.manager = self.register("manager@example.com", "Manager")
        self.admin = self.register("admin@example.com", "Admin")
        update_user(self.manager["id"], UserUpdate(role=UserRole.MANAGER))
        update_user(self.admin["id"], UserUpdate(role=UserRole.ADMIN))

    def register(self, email, name):
        response = self.client.post("/users", json={
            "email": email,
            "password": "synthetic-password",
            "name": f"Synthetic {name}",
            "phone": f"synthetic-{name.lower()}-phone",
            "address": f"synthetic-{name.lower()}-address",
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def token(self, email, password="synthetic-password"):
        response = self.client.post("/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def headers(self, user, password="synthetic-password"):
        return {"Authorization": "Bearer " + self.token(user["email"], password)}

    def test_public_registration_creates_default_user_and_profile_without_secrets(self):
        response = self.client.post("/users", json={"email": "new@example.com", "password": "synthetic-password"})
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["role"], "user")
        self.assertTrue(body["is_active"])
        self.assertNotIn("hashed_password", response.text)
        self.assertNotIn("synthetic-password", response.text)
        profile = get_profile_by_user_id(body["id"])
        self.assertIsNone(profile.name)
        self.assertEqual(profile.user_id, body["id"])

    def test_registration_rejects_role_escalation_and_sanitizes_password_errors(self):
        for payload in (
            {"email": "attack@example.com", "password": "synthetic-password", "role": "admin"},
            {"email": "attack@example.com", "password": "synthetic-password", "role": "owner"},
            {"email": "attack@example.com", "password": "synthetic-password", "id": 10},
            {"email": "invalid", "password": "synthetic-password"},
            {"email": "attack@example.com", "password": "short"},
            {"email": "attack@example.com", "password": "synthetic-password", "hashed_password": "secret-hash"},
        ):
            response = self.client.post("/users", json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Invalid user request"})
            self.assertNotIn("synthetic-password", response.text)
            self.assertNotIn("secret-hash", response.text)

    def test_duplicate_registration_and_email_update_return_409(self):
        response = self.client.post("/users", json={"email": "OWNER@EXAMPLE.COM", "password": "synthetic-password"})
        self.assertEqual(response.status_code, 409)
        response = self.client.put(f"/users/{self.other['id']}", json={"email": self.owner["email"]}, headers=self.headers(self.admin))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f"/users/{self.other['id']}", headers=self.headers(self.other)).json()["email"], self.other["email"])

    def test_all_protected_user_and_profile_endpoints_return_401_without_token(self):
        requests = (
            lambda: self.client.get("/users"),
            lambda: self.client.get(f"/users/{self.owner['id']}"),
            lambda: self.client.put(f"/users/{self.owner['id']}", json={"email": "changed@example.com"}),
            lambda: self.client.delete(f"/users/{self.owner['id']}"),
            lambda: self.client.get("/profiles/me"),
            lambda: self.client.put("/profiles/me", json={"name": "Unauthorized"}),
        )
        for request in requests:
            response = request()
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_user_listing_is_admin_only_and_never_exposes_hashes(self):
        for user in (self.owner, self.manager):
            response = self.client.get("/users", headers=self.headers(user))
            self.assertEqual(response.status_code, 403)
        response = self.client.get("/users", headers=self.headers(self.admin))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 4)
        self.assertTrue(all("hashed_password" not in user for user in response.json()))
        self.assertNotIn("hashed_password", str(self.client.get("/openapi.json").json()))

    def test_owner_can_read_and_update_own_credentials(self):
        headers = self.headers(self.owner)
        response = self.client.get(f"/users/{self.owner['id']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hashed_password", response.text)
        updated = self.client.put(f"/users/{self.owner['id']}", json={"email": "OWNER-NEW@example.com"}, headers=headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["email"], "owner-new@example.com")
        updated = self.client.put(f"/users/{self.owner['id']}", json={"password": "new-synthetic-password"}, headers=headers)
        self.assertEqual(updated.status_code, 200)
        self.assertNotIn("new-synthetic-password", updated.text)
        self.assertEqual(self.client.post("/auth/login", json={"email": "owner-new@example.com", "password": "new-synthetic-password"}).status_code, 200)

    def test_manager_is_not_admin_and_users_cannot_access_another_user(self):
        for actor in (self.owner, self.manager):
            headers = self.headers(actor)
            self.assertEqual(self.client.get(f"/users/{self.other['id']}", headers=headers).status_code, 403)
            self.assertEqual(self.client.put(f"/users/{self.other['id']}", json={"email": "stolen@example.com"}, headers=headers).status_code, 403)
            self.assertEqual(self.client.delete(f"/users/{self.other['id']}", headers=headers).status_code, 403)

    def test_owner_cannot_change_role_or_active_state(self):
        headers = self.headers(self.owner)
        before = self.client.get(f"/users/{self.owner['id']}", headers=headers).json()
        for field, value in (("role", "admin"), ("role", "manager"), ("is_active", False)):
            response = self.client.put(f"/users/{self.owner['id']}", json={field: value}, headers=headers)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.client.get(f"/users/{self.owner['id']}", headers=headers).json(), before)

    def test_only_admin_can_change_roles_or_account_state(self):
        headers = self.headers(self.admin)
        response = self.client.put(f"/users/{self.other['id']}", json={"role": "manager"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "manager")
        response = self.client.put(f"/users/{self.other['id']}", json={"is_active": False}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])
        self.assertEqual(self.client.post("/auth/login", json={"email": self.other["email"], "password": "synthetic-password"}).status_code, 401)

    def test_admin_can_read_update_and_delete_another_user_with_profile_cascade(self):
        headers = self.headers(self.admin)
        self.assertEqual(self.client.get(f"/users/{self.other['id']}", headers=headers).status_code, 200)
        response = self.client.put(f"/users/{self.other['id']}", json={"email": "updated-other@example.com"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(f"/users/{self.other['id']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": self.other["id"], "deleted": True})
        self.assertEqual(self.client.get(f"/users/{self.other['id']}", headers=headers).status_code, 404)

    def test_delete_with_missing_profile_returns_404_without_deleting_user(self):
        headers = self.headers(self.admin)
        with open_auth_database() as database:
            database.table("profiles").remove(doc_ids=[self.other["id"]])
        response = self.client.delete(f"/users/{self.other['id']}", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Profile not found"})
        self.assertEqual(self.client.get(f"/users/{self.other['id']}", headers=headers).status_code, 200)

    def test_owner_can_access_and_update_only_own_profile(self):
        headers = self.headers(self.owner)
        profile = self.client.get("/profiles/me", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["user_id"], self.owner["id"])
        updated = self.client.put("/profiles/me", json={"name": "Updated Owner", "phone": None}, headers=headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Updated Owner")
        self.assertIsNone(updated.json()["phone"])
        self.assertEqual(self.client.get("/auth/me", headers=headers).json()["profile"]["name"], "Updated Owner")
        self.assertEqual(self.client.get(f"/profiles/{self.other['id']}", headers=headers).status_code, 404)

    def test_admin_cannot_use_self_profile_route_to_edit_another_profile(self):
        response = self.client.put("/profiles/me", json={"name": "Admin Profile"}, headers=self.headers(self.admin))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/profiles/me", headers=self.headers(self.admin)).json()["name"], "Admin Profile")
        self.assertEqual(self.client.get(f"/profiles/{self.other['id']}", headers=self.headers(self.admin)).status_code, 404)
        self.assertEqual(get_profile_by_user_id(self.other["id"]).name, "Synthetic Other")

    def test_missing_user_is_404_after_authorization(self):
        owner_headers = self.headers(self.owner)
        self.assertEqual(self.client.get("/users/99999", headers=owner_headers).status_code, 403)
        self.assertEqual(self.client.put("/users/99999", json={"email": "missing@example.com"}, headers=owner_headers).status_code, 403)
        self.assertEqual(self.client.delete("/users/99999", headers=owner_headers).status_code, 403)
        admin_headers = self.headers(self.admin)
        self.assertEqual(self.client.get("/users/99999", headers=admin_headers).status_code, 404)
        self.assertEqual(self.client.put("/users/99999", json={"email": "missing@example.com"}, headers=admin_headers).status_code, 404)
        self.assertEqual(self.client.delete("/users/99999", headers=admin_headers).status_code, 404)

    def test_explicit_null_and_malformed_credential_updates_are_sanitized(self):
        headers = self.headers(self.owner)
        for payload in (
            {"email": None},
            {"password": None},
            {"role": None},
            {"is_active": None},
            {"password": "short"},
            {"password": "synthetic-password", "hashed_password": "sensitive-hash"},
        ):
            response = self.client.put(f"/users/{self.owner['id']}", json=payload, headers=headers)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Invalid user request"})
            self.assertNotIn("synthetic-password", response.text)
            self.assertNotIn("sensitive-hash", response.text)
        response = self.client.put("/profiles/me", json={"user_id": self.other["id"]}, headers=headers)
        self.assertEqual(response.status_code, 422)

    def test_registered_endpoints_are_in_openapi(self):
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        self.assertEqual(set(paths["/users"]), {"get", "post"})
        self.assertEqual(set(paths["/users/{user_id}"]), {"get", "put", "delete"})
        self.assertEqual(set(paths["/profiles/me"]), {"get", "put"})
        self.assertIn("security", paths["/users/{user_id}"]["put"])
        self.assertNotIn("security", paths["/users"]["post"])
        self.assertEqual(paths["/users"]["post"]["responses"]["201"]["description"], "Successful Response")
        registration_ref = paths["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        registration_name = registration_ref.rsplit("/", 1)[-1]
        registration_schema = schema["components"]["schemas"][registration_name]
        self.assertNotIn("role", registration_schema["properties"])
        self.assertNotIn("hashed_password", str(schema))


if __name__ == "__main__":
    unittest.main()