"""HTTP contract tests for the supplier directory API."""

import json
import os
import secrets
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.main import app
from services.api.response_models import DeletionResponse
from services.api.seed import seed_suppliers


class TestSuppliersAPI(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        database_path = os.path.join(self.temporary_directory.name, "suppliers.json")
        auth_database_path = os.path.join(self.temporary_directory.name, "auth.json")
        self.database_environment = patch.dict(
            os.environ,
            {
                "NEXOVA_SUPPLIERS_DB_PATH": database_path,
                "NEXOVA_AUTH_DB_PATH": auth_database_path,
                "JWT_SECRET_KEY": secrets.token_urlsafe(48),
                "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            },
        )
        self.database_environment.start()
        self.addCleanup(self.database_environment.stop)
        seed_suppliers()
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        registration = self.client.post(
            "/users",
            json={"email": "supplier-tests@example.com", "password": "synthetic-password"},
        )
        self.assertEqual(registration.status_code, 201)
        login = self.client.post(
            "/auth/login",
            json={"email": "supplier-tests@example.com", "password": "synthetic-password"},
        )
        self.assertEqual(login.status_code, 200)
        self.client.headers.update(
            {"Authorization": "Bearer " + login.json()["access_token"]}
        )

    def test_all_supplier_routes_reject_missing_and_invalid_bearer_tokens(self):
        supplier_id = self.supplier_id("Workable")
        requests = (
            ("POST", "/api/suppliers", {"json": self.valid_payload()}),
            ("GET", "/api/suppliers", {}),
            ("GET", f"/api/suppliers/{supplier_id}", {}),
            ("PATCH", f"/api/suppliers/{supplier_id}/rate", {"json": {"monthly_rate": 333}}),
            ("PATCH", f"/api/suppliers/{supplier_id}/status", {"json": {"status": "suspended"}}),
            ("DELETE", f"/api/suppliers/{supplier_id}", {}),
        )
        with TestClient(app) as anonymous_client:
            for method, path, kwargs in requests:
                for headers in ({}, {"Authorization": "Bearer malformed"}):
                    with self.subTest(method=method, path=path, authenticated=bool(headers)):
                        response = anonymous_client.request(method, path, headers=headers, **kwargs)
                        self.assertEqual(response.status_code, 401)
                        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_supplier_routes_are_marked_protected_in_openapi(self):
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        expected = {
            ("/api/suppliers", "post"),
            ("/api/suppliers", "get"),
            ("/api/suppliers/{supplier_id}", "get"),
            ("/api/suppliers/{supplier_id}/rate", "patch"),
            ("/api/suppliers/{supplier_id}/status", "patch"),
            ("/api/suppliers/{supplier_id}", "delete"),
        }
        for path, method in expected:
            with self.subTest(path=path, method=method):
                self.assertIn("security", paths[path][method])
                for code in ("401", "500"):
                    self.assertTrue(paths[path][method]["responses"][code]["content"]["application/json"]["schema"]["$ref"].endswith("/DetailErrorResponse"))
                if "{supplier_id}" in path:
                    self.assertIn("404", paths[path][method]["responses"])
        self.assertNotIn("security", paths["/health"]["get"])
        list_ref = paths["/api/suppliers"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"]
        self.assertTrue(list_ref.endswith("/SupplierListItem"))
        row = schema["components"]["schemas"]["SupplierListItem"]
        detail = schema["components"]["schemas"]["SupplierRecord"]
        self.assertEqual(set(row["properties"]), set(detail["properties"]) - {"updated_at"})
        self.assertFalse(row["additionalProperties"])
        self.assertNotIn("id", schema["components"]["schemas"]["SupplierCreate"]["properties"])
        for path, method, code in (
            ("/api/suppliers", "post", "201"),
            ("/api/suppliers/{supplier_id}", "get", "200"),
            ("/api/suppliers/{supplier_id}/rate", "patch", "200"),
            ("/api/suppliers/{supplier_id}/status", "patch", "200"),
        ):
            self.assertTrue(paths[path][method]["responses"][code]["content"]["application/json"]["schema"]["$ref"].endswith("/SupplierRecord"))

    def supplier_id(self, name):
        response = self.client.get("/api/suppliers")
        return next(
            supplier["id"]
            for supplier in response.json()
            if supplier["name"] == name
        )

    def valid_payload(self):
        return {
            "name": "Example Supplier",
            "country": "Spain",
            "categories": ["job_boards"],
            "monthly_rate": 100.0,
            "currency": "EUR",
            "status": "active",
        }

    def test_create_returns_server_id_and_timestamp(self):
        payload = {
            **self.valid_payload(),
            "contact_email": "synthetic@example.com",
            "notes": "Synthetic supplier notes",
            "contract_renewal_date": "2030-01-02",
        }
        response = self.client.post("/api/suppliers", json=payload)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertGreater(data["id"], 0)
        self.assertTrue(data["updated_at"].endswith("Z"))
        self.assertEqual(data["name"], "Example Supplier")
        self.assertEqual(set(data), set(payload) | {"id", "updated_at"})
        self.assertEqual(self.client.get(f"/api/suppliers/{data['id']}").json(), data)
        listed = self.client.get("/api/suppliers").json()
        row = next(item for item in listed if item["id"] == data["id"])
        self.assertEqual(row, {key: value for key, value in data.items() if key != "updated_at"})
        self.assertEqual(row["contact_email"], payload["contact_email"])
        self.assertEqual(row["notes"], payload["notes"])

    def test_create_rejects_client_managed_fields(self):
        for field_name, value in (
            ("id", 99),
            ("updated_at", "2026-10-13T00:00:00Z"),
        ):
            with self.subTest(field_name=field_name):
                payload = {**self.valid_payload(), field_name: value}
                response = self.client.post("/api/suppliers", json=payload)
                self.assertEqual(response.status_code, 422)

    def test_list_filters_country_and_category_together(self):
        all_suppliers = self.client.get("/api/suppliers")
        response = self.client.get(
            "/api/suppliers",
            params={"country": "Spain", "category": "job_boards"},
        )

        self.assertEqual(all_suppliers.status_code, 200)
        self.assertEqual(len(all_suppliers.json()), 15)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {supplier["name"] for supplier in response.json()},
            {"LinkedIn Talent Solutions", "InfoJobs Premium"},
        )
        details = []
        for row in all_suppliers.json():
            detail = self.client.get(f"/api/suppliers/{row['id']}").json()
            details.append(detail)
            self.assertEqual(row, {key: value for key, value in detail.items() if key != "updated_at"})
            self.assertEqual(set(row), {
                "id", "name", "country", "categories", "monthly_rate", "currency",
                "status", "contract_renewal_date", "contact_email", "notes",
            })
        self.assertLess(
            len(json.dumps(all_suppliers.json(), separators=(",", ":")).encode()),
            len(json.dumps(details, separators=(",", ":")).encode()),
        )
        for row in all_suppliers.json():
            deleted = self.client.delete(f"/api/suppliers/{row['id']}")
            self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/suppliers").json(), [])

    def test_list_rejects_invalid_filter_values(self):
        for params in ({"country": "France"}, {"category": "other"}):
            with self.subTest(params=params):
                response = self.client.get("/api/suppliers", params=params)
                self.assertEqual(response.status_code, 422)

    def test_get_supplier_and_missing_supplier(self):
        supplier_id = self.supplier_id("Workable")

        response = self.client.get(f"/api/suppliers/{supplier_id}")
        missing = self.client.get("/api/suppliers/99999")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Workable")
        self.assertEqual(set(response.json()), {
            "id", "name", "country", "categories", "monthly_rate", "currency",
            "status", "contract_renewal_date", "contact_email", "notes", "updated_at",
        })
        self.assertEqual(missing.status_code, 404)

    def test_rate_update_changes_timestamp_and_persists(self):
        supplier_id = self.supplier_id("Workable")
        original = self.client.get(f"/api/suppliers/{supplier_id}").json()
        fixed_timestamp = "2030-01-02T03:04:05+00:00"

        with patch("services.api.routers.suppliers.datetime") as mocked_datetime:
            from datetime import datetime, timezone

            mocked_datetime.now.return_value = datetime.fromisoformat(fixed_timestamp)
            response = self.client.patch(
                f"/api/suppliers/{supplier_id}/rate",
                json={"monthly_rate": 333.0},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["monthly_rate"], 333.0)
        self.assertEqual(response.json()["updated_at"], fixed_timestamp.replace("+00:00", "Z"))
        persisted = self.client.get(f"/api/suppliers/{supplier_id}").json()
        self.assertEqual(persisted["monthly_rate"], 333.0)
        self.assertEqual(persisted["updated_at"], response.json()["updated_at"])
        self.assertEqual(response.json(), persisted)
        for field in set(original) - {"monthly_rate", "updated_at"}:
            self.assertEqual(persisted[field], original[field])
        row = next(item for item in self.client.get("/api/suppliers").json() if item["id"] == supplier_id)
        self.assertEqual(row["monthly_rate"], 333.0)
        self.assertNotIn("updated_at", row)

    def test_rate_update_rejects_invalid_rate_and_missing_id(self):
        supplier_id = self.supplier_id("Workable")

        invalid = self.client.patch(
            f"/api/suppliers/{supplier_id}/rate",
            json={"monthly_rate": 0},
        )
        missing = self.client.patch(
            "/api/suppliers/99999/rate",
            json={"monthly_rate": 100},
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(missing.status_code, 404)
        for payload in (
            {"monthly_rate": 100, "updated_at": "synthetic"},
            {"monthly_rate": 100, "id": 99},
            {"monthly_rate": None},
        ):
            self.assertEqual(
                self.client.patch(f"/api/suppliers/{supplier_id}/rate", json=payload).status_code,
                422,
            )

    def test_status_update_and_invalid_status(self):
        supplier_id = self.supplier_id("Workable")
        original_timestamp = self.client.get(
            f"/api/suppliers/{supplier_id}"
        ).json()["updated_at"]

        response = self.client.patch(
            f"/api/suppliers/{supplier_id}/status",
            json={"status": "suspended"},
        )
        invalid = self.client.patch(
            f"/api/suppliers/{supplier_id}/status",
            json={"status": "deleted"},
        )
        missing = self.client.patch(
            "/api/suppliers/99999/status",
            json={"status": "active"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "suspended")
        self.assertEqual(response.json()["updated_at"], original_timestamp)
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(missing.status_code, 404)
        persisted = self.client.get(f"/api/suppliers/{supplier_id}").json()
        self.assertEqual(persisted, response.json())
        for payload in (
            {"status": "active", "monthly_rate": 1},
            {"status": "active", "updated_at": "synthetic"},
            {"status": None},
        ):
            self.assertEqual(
                self.client.patch(f"/api/suppliers/{supplier_id}/status", json=payload).status_code,
                422,
            )
        self.assertEqual(self.client.get(f"/api/suppliers/{supplier_id}").json(), persisted)

    def test_delete_and_missing_id(self):
        supplier_id = self.supplier_id("Workable")

        response = self.client.delete(f"/api/suppliers/{supplier_id}")
        missing = self.client.delete("/api/suppliers/99999")
        detail = self.client.get(f"/api/suppliers/{supplier_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": supplier_id, "deleted": True})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "Supplier not found"})
        self.assertEqual(detail.status_code, 404)
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/api/suppliers/{supplier_id}"]["delete"]
        reference = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        self.assertTrue(reference.endswith("/DeletionResponse"))
        contract = schema["components"]["schemas"]["DeletionResponse"]
        self.assertEqual(set(contract["properties"]), {"id", "deleted"})
        self.assertEqual(set(contract["required"]), {"id", "deleted"})
        self.assertFalse(contract["additionalProperties"])
        self.assertEqual(contract["properties"]["id"]["exclusiveMinimum"], 0)
        self.assertIs(contract["properties"]["deleted"]["const"], True)
        for payload in (
            {"id": 0, "deleted": True},
            {"id": -1, "deleted": True},
            {"id": "1", "deleted": True},
            {"id": True, "deleted": True},
            {"id": 1},
            {"deleted": True},
            {"id": 1, "deleted": False},
            {"id": 1, "deleted": True, "internal": "hidden"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                DeletionResponse.model_validate(payload)


if __name__ == "__main__":
    unittest.main()