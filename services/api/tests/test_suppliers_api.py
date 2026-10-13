"""HTTP contract tests for the supplier directory API."""

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.main import app
from services.api.seed import seed_suppliers


class TestSuppliersAPI(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temporary_directory.name, "suppliers.json")
        self.database_environment = patch.dict(
            os.environ,
            {"NEXOVA_SUPPLIERS_DB_PATH": database_path},
        )
        self.database_environment.start()
        seed_suppliers()
        self.client = TestClient(app)

    def tearDown(self):
        self.database_environment.stop()
        self.temporary_directory.cleanup()

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
        response = self.client.post("/api/suppliers", json=self.valid_payload())

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertGreater(data["id"], 0)
        self.assertTrue(data["updated_at"].endswith("Z"))
        self.assertEqual(data["name"], "Example Supplier")

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
        self.assertEqual(missing.status_code, 404)

    def test_rate_update_changes_timestamp_and_persists(self):
        supplier_id = self.supplier_id("Workable")
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

    def test_delete_and_missing_id(self):
        supplier_id = self.supplier_id("Workable")

        response = self.client.delete(f"/api/suppliers/{supplier_id}")
        missing = self.client.delete("/api/suppliers/99999")
        detail = self.client.get(f"/api/suppliers/{supplier_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": supplier_id, "deleted": True})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(detail.status_code, 404)


if __name__ == "__main__":
    unittest.main()