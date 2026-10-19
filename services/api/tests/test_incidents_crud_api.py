"""Contract and integration tests for incident CRUD, filtering, lifecycle transitions and summary."""

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.seed_incidents import seed_incidents
from services.api.incident_models import (
    ALLOWED_BRANCHES,
    ALLOWED_CATEGORIES,
    ALLOWED_ORIGINS,
    ALLOWED_STATUSES,
)
from services.api.main import app


class TestIncidentsCrudAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, "incidents.json")
        self.env_patch = patch.dict(
            os.environ,
            {
                "NEXOVA_INCIDENTS_DB_PATH": self.db_path,
                "JWT_SECRET_KEY": "a" * 64,
                "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            },
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def valid_payload(self, **overrides):
        payload = {
            "title": "Portal login timeout",
            "description": "Users reporting 504 Gateway Timeout when submitting candidate profile.",
            "category": "technical_failure",
            "origin": "customer",
            "branch": "central",
        }
        payload.update(overrides)
        return payload

    # =========================================================================
    # POST /api/incidents
    # =========================================================================

    def test_create_incident_success(self):
        response = self.client.post("/api/incidents", json=self.valid_payload())
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsInstance(data["id"], int)
        self.assertGreater(data["id"], 0)
        self.assertEqual(data["title"], "Portal login timeout")
        self.assertEqual(data["status"], "open")
        self.assertEqual(data["origin"], "customer")
        self.assertEqual(data["branch"], "central")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_create_incident_validation_failures(self):
        # Missing required field
        for missing in ("title", "description", "category", "origin", "branch"):
            payload = self.valid_payload()
            del payload[missing]
            response = self.client.post("/api/incidents", json=payload)
            self.assertEqual(
                response.status_code,
                400,
                f"Missing '{missing}' should return 400 but returned {response.status_code}",
            )
            self.assertIn("errors", response.json())

        # Blank strings
        for blank_field in ("title", "description"):
            payload = self.valid_payload(**{blank_field: "   "})
            response = self.client.post("/api/incidents", json=payload)
            self.assertEqual(response.status_code, 400)

        # Invalid enums
        for field, invalid_val in (
            ("category", "unsupported_category"),
            ("origin", "external_partner"),
            ("branch", "headquarters"),  # headquarters must be central
        ):
            payload = self.valid_payload(**{field: invalid_val})
            response = self.client.post("/api/incidents", json=payload)
            self.assertEqual(response.status_code, 400)

    # =========================================================================
    # GET /api/incidents (List & Filters)
    # =========================================================================

    def test_list_incidents_empty_database(self):
        response = self.client.get("/api/incidents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_incidents_with_combinable_filters(self):
        self.client.post(
            "/api/incidents",
            json=self.valid_payload(
                title="Incident 1",
                category="technical_failure",
                origin="customer",
                branch="central",
            ),
        )
        self.client.post(
            "/api/incidents",
            json=self.valid_payload(
                title="Incident 2",
                category="process_error",
                origin="branch",
                branch="valencia_operations",
            ),
        )
        self.client.post(
            "/api/incidents",
            json=self.valid_payload(
                title="Incident 3",
                category="client_complaint",
                origin="branch",
                branch="miami_office",
            ),
        )

        # Filter by branch
        resp = self.client.get("/api/incidents?branch=miami_office")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["title"], "Incident 3")

        # Filter by origin
        resp = self.client.get("/api/incidents?origin=branch")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

        # Combinable filter
        resp = self.client.get(
            "/api/incidents?origin=branch&branch=valencia_operations&category=process_error"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["title"], "Incident 2")

        # Filter with no matches
        resp = self.client.get("/api/incidents?branch=remote")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_list_incidents_rejects_invalid_filter_values(self):
        for param, bad_val in (
            ("status", "pending"),
            ("origin", "vendor"),
            ("branch", "headquarters"),
            ("category", "hardware"),
        ):
            resp = self.client.get(f"/api/incidents?{param}={bad_val}")
            self.assertEqual(resp.status_code, 400)
            self.assertIn("Invalid", resp.json()["detail"])

    # =========================================================================
    # GET /api/incidents/{id}
    # =========================================================================

    def test_get_incident_by_id(self):
        created = self.client.post("/api/incidents", json=self.valid_payload()).json()
        inc_id = created["id"]

        resp = self.client.get(f"/api/incidents/{inc_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], inc_id)
        self.assertEqual(resp.json()["title"], created["title"])

        # Non-existing ID
        not_found = self.client.get("/api/incidents/999999")
        self.assertEqual(not_found.status_code, 404)
        self.assertIn("not found", not_found.json()["detail"].lower())

    # =========================================================================
    # PATCH /api/incidents/{id}/status (Lifecycle transitions)
    # =========================================================================

    def test_status_transitions_valid_path(self):
        created = self.client.post("/api/incidents", json=self.valid_payload()).json()
        inc_id = created["id"]
        self.assertEqual(created["status"], "open")

        # open -> in_progress
        patch1 = self.client.patch(
            f"/api/incidents/{inc_id}/status", json={"status": "in_progress"}
        )
        self.assertEqual(patch1.status_code, 200)
        self.assertEqual(patch1.json()["status"], "in_progress")

        # in_progress -> resolved
        patch2 = self.client.patch(
            f"/api/incidents/{inc_id}/status", json={"status": "resolved"}
        )
        self.assertEqual(patch2.status_code, 200)
        self.assertEqual(patch2.json()["status"], "resolved")

    def test_status_transitions_discard_path(self):
        # open -> discarded
        created1 = self.client.post("/api/incidents", json=self.valid_payload()).json()
        patch1 = self.client.patch(
            f"/api/incidents/{created1['id']}/status", json={"status": "discarded"}
        )
        self.assertEqual(patch1.status_code, 200)
        self.assertEqual(patch1.json()["status"], "discarded")

        # in_progress -> discarded
        created2 = self.client.post("/api/incidents", json=self.valid_payload()).json()
        self.client.patch(
            f"/api/incidents/{created2['id']}/status", json={"status": "in_progress"}
        )
        patch2 = self.client.patch(
            f"/api/incidents/{created2['id']}/status", json={"status": "discarded"}
        )
        self.assertEqual(patch2.status_code, 200)
        self.assertEqual(patch2.json()["status"], "discarded")

    def test_status_transitions_invalid_and_terminal(self):
        created = self.client.post("/api/incidents", json=self.valid_payload()).json()
        inc_id = created["id"]

        # open -> resolved is invalid (must go through in_progress)
        invalid_patch = self.client.patch(
            f"/api/incidents/{inc_id}/status", json={"status": "resolved"}
        )
        self.assertEqual(invalid_patch.status_code, 400)

        # Move to resolved (terminal)
        self.client.patch(
            f"/api/incidents/{inc_id}/status", json={"status": "in_progress"}
        )
        self.client.patch(
            f"/api/incidents/{inc_id}/status", json={"status": "resolved"}
        )

        # Attempt to change status from terminal resolved
        for target_status in ALLOWED_STATUSES:
            resp = self.client.patch(
                f"/api/incidents/{inc_id}/status", json={"status": target_status}
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("final", resp.json()["detail"].lower())

    def test_patch_status_not_found(self):
        resp = self.client.patch("/api/incidents/999999/status", json={"status": "in_progress"})
        self.assertEqual(resp.status_code, 404)

    # =========================================================================
    # GET /api/incidents/summary
    # =========================================================================

    def test_summary_empty_database(self):
        resp = self.client.get("/api/incidents/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 0)
        for st in ALLOWED_STATUSES:
            self.assertEqual(data["by_status"][st], 0)
        for cat in ALLOWED_CATEGORIES:
            self.assertEqual(data["by_category"][cat], 0)
        for orig in ALLOWED_ORIGINS:
            self.assertEqual(data["by_origin"][orig], 0)
        for br in ALLOWED_BRANCHES:
            self.assertEqual(data["by_branch"][br], 0)

    def test_summary_with_seed_data(self):
        seed_incidents()
        resp = self.client.get("/api/incidents/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 96)
        self.assertEqual(data["by_status"]["open"], 27)
        self.assertEqual(data["by_status"]["resolved"], 56)
        self.assertEqual(data["by_status"]["discarded"], 13)
        self.assertEqual(data["by_status"]["in_progress"], 0)

        self.assertEqual(data["by_category"]["technical_failure"], 49)
        self.assertEqual(data["by_category"]["process_error"], 35)
        self.assertEqual(data["by_category"]["client_complaint"], 12)
        self.assertEqual(data["by_category"]["sla_breach"], 0)

        self.assertEqual(data["by_origin"]["customer"], 96)
        self.assertEqual(data["by_branch"]["central"], 96)

    # =========================================================================
    # Error sanitization (no stack traces on 500)
    # =========================================================================

    def test_internal_error_does_not_expose_stack_trace(self):
        with patch("services.api.routers.incidents.open_incident_table", side_effect=RuntimeError("Secret DB error")):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/api/incidents")
                self.assertEqual(resp.status_code, 500)
                self.assertNotIn("Traceback", resp.text)
                self.assertNotIn("Secret DB error", resp.text)
                self.assertIn("internal server error", resp.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
