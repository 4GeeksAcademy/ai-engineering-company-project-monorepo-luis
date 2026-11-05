"""Tests for the Nexova incident API endpoints."""

import csv
import io
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.main import app
from services.api.incident_models import IncidentAnalysisResponse
from services.api.response_models import HealthResponse
from services.api.routers.incidents import set_latest_result
from packages.incident_analyzer import REQUIRED_COLUMNS, VALID_CATEGORIES, VALID_STATUSES


class TestIncidentsAPI(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        environment = patch.dict(os.environ, {
            "NEXOVA_AUTH_DB_PATH": os.path.join(self.temporary_directory.name, "auth.json"),
            "JWT_SECRET_KEY": secrets.token_urlsafe(48),
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        registration = self.client.post(
            "/users",
            json={"email": "incident-tests@example.com", "password": "synthetic-password"},
        )
        self.assertEqual(registration.status_code, 201)
        login = self.client.post(
            "/auth/login",
            json={"email": "incident-tests@example.com", "password": "synthetic-password"},
        )
        self.assertEqual(login.status_code, 200)
        self.client.headers.update(
            {"Authorization": "Bearer " + login.json()["access_token"]}
        )
        set_latest_result(None)  # Reset state before each test
        repo_root = Path(__file__).resolve().parents[3]
        self.fixture_path = repo_root / "data" / "raw" / "incidents-nexova.csv"

    def test_incident_routes_reject_missing_and_invalid_bearer_tokens(self):
        files = {"file": ("empty.csv", b"id\n", "text/csv")}
        with TestClient(app) as anonymous_client:
            for headers in ({}, {"Authorization": "Bearer malformed"}):
                with self.subTest(path="/api/incidents/analyze", authenticated=bool(headers)):
                    response = anonymous_client.post(
                        "/api/incidents/analyze", files=files, headers=headers
                    )
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers["www-authenticate"], "Bearer")
                with self.subTest(path="/api/incidents/results/export", authenticated=bool(headers)):
                    response = anonymous_client.get(
                        "/api/incidents/results/export", headers=headers
                    )
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_incident_routes_are_marked_protected_in_openapi(self):
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        for path, method in (
            ("/api/incidents/analyze", "post"),
            ("/api/incidents/results/export", "get"),
        ):
            with self.subTest(path=path, method=method):
                self.assertIn("security", paths[path][method])
        self.assertNotIn("security", paths["/health"]["get"])
        analysis = paths["/api/incidents/analyze"]["post"]
        self.assertIn("multipart/form-data", analysis["requestBody"]["content"])
        response_ref = analysis["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        self.assertTrue(response_ref.endswith("/IncidentAnalysisResponse"))
        contract = schema["components"]["schemas"]["IncidentAnalysisResponse"]
        expected = {
            "total_records", "valid_records", "invalid_records", "category_counts",
            "status_counts", "invalid_breakdown", "satisfaction", "errors_count",
        }
        self.assertEqual(set(contract["properties"]), expected)
        self.assertEqual(set(contract["required"]), expected)
        self.assertFalse(contract["additionalProperties"])
        for code in ("400", "401", "413", "500", "4XX"):
            self.assertIn("application/json", analysis["responses"][code]["content"])
        self.assertNotIn("422", analysis["responses"])
        export = paths["/api/incidents/results/export"]["get"]
        self.assertEqual(set(export["responses"]["200"]["content"]), {"text/csv"})
        self.assertEqual(export["responses"]["200"]["content"]["text/csv"]["schema"], {"type": "string"})
        self.assertEqual(set(export["responses"]["200"]["headers"]), {"Content-Disposition", "Cache-Control"})
        for code in ("401", "404", "500"):
            self.assertIn("application/json", export["responses"][code]["content"])

    def test_health_check(self):
        """Verifies health check endpoint returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "nexova-api"})
        self.assertIn("application/json", response.headers["content-type"])
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/health"]["get"]
        self.assertNotIn("security", operation)
        reference = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        contract = schema["components"]["schemas"][reference.rsplit("/", 1)[-1]]
        self.assertEqual(set(contract["properties"]), {"status", "service"})
        self.assertEqual(set(contract["required"]), {"status", "service"})
        self.assertFalse(contract["additionalProperties"])
        self.assertEqual(contract["properties"]["status"]["const"], "ok")
        self.assertEqual(contract["properties"]["service"]["const"], "nexova-api")
        for payload in (
            {"status": "ok"},
            {"service": "nexova-api"},
            {"status": "down", "service": "nexova-api"},
            {"status": "ok", "service": "other"},
            {"status": "ok", "service": "nexova-api", "internal": "hidden"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                HealthResponse.model_validate(payload)

    def test_export_without_prior_analysis_returns_404(self):
        """Export before running an analysis must return 404 Not Found."""
        response = self.client.get("/api/incidents/results/export")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {
            "detail": "No analysis results available to export. Please run an analysis first."
        })
        self.assertIn("application/json", response.headers["content-type"])

    def test_analyze_invalid_extension(self):
        """Reject non-csv file extensions."""
        files = {"file": ("data.txt", b"some text content", "text/plain")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only .csv files are supported", response.json()["detail"])

    def test_analyze_empty_file(self):
        """Reject empty CSV files."""
        files = {"file": ("empty.csv", b"", "text/csv")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())
        with patch("services.api.routers.incidents.MAX_FILE_SIZE", 4):
            oversized = self.client.post(
                "/api/incidents/analyze",
                files={"file": ("large.csv", b"12345", "text/csv")},
            )
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(set(oversized.json()), {"detail"})
        self.assertEqual(self.client.get("/api/incidents/results/export").status_code, 404)

    def test_analyze_missing_header_columns(self):
        """Reject CSV with invalid headers."""
        bad_csv = b"ticket_id,date,client_company\n1,2,3\n"
        files = {"file": ("incomplete.csv", bad_csv, "text/csv")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required columns", response.json()["detail"])
        missing = self.client.post("/api/incidents/analyze")
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(set(missing.json()), {"detail", "errors"})
        self.assertEqual(missing.json()["errors"], [{"field": "file", "message": "Field required"}])
        with patch("services.api.routers.incidents.analyze_csv_stream", side_effect=RuntimeError("internal detail")):
            failed = self.client.post(
                "/api/incidents/analyze", files={"file": ("failed.csv", b"header\n", "text/csv")}
            )
        self.assertEqual(failed.status_code, 500)
        self.assertEqual(failed.json(), {"detail": "An error occurred while analyzing the incident file."})
        self.assertNotIn("internal detail", failed.text)

    def test_analyze_official_fixture_and_export(self):
        """Full end-to-end test with official Nexova fixture."""
        self.assertTrue(self.fixture_path.exists(), f"Fixture missing: {self.fixture_path}")
        with open(self.fixture_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": ("incidents-nexova.csv", file_bytes, "text/csv")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        expected_fields = {
            "total_records", "valid_records", "invalid_records", "category_counts",
            "status_counts", "invalid_breakdown", "satisfaction", "errors_count",
        }
        self.assertEqual(set(data), expected_fields)
        self.assertEqual(set(data["satisfaction"]), {
            "scored_tickets", "total_closed_tickets", "average_score", "score_distribution",
        })
        self.assertEqual(set(data["category_counts"]), set(VALID_CATEGORIES))
        self.assertEqual(set(data["status_counts"]), set(VALID_STATUSES))
        self.assertEqual(set(data["satisfaction"]["score_distribution"]), {"1", "2", "3", "4", "5"})
        self.assertEqual(IncidentAnalysisResponse.model_validate(data).model_dump(mode="json"), data)
        self.assertEqual(data["total_records"], 100)
        self.assertEqual(data["valid_records"], 96)
        self.assertEqual(data["invalid_records"], 4)
        self.assertEqual(data["category_counts"]["TECHNICAL"], 28)
        self.assertEqual(data["category_counts"]["BILLING"], 18)
        self.assertEqual(data["category_counts"]["ACCESS"], 21)
        self.assertEqual(data["category_counts"]["HR_QUERY"], 17)
        self.assertEqual(data["category_counts"]["COMPLAINT"], 12)
        self.assertEqual(data["status_counts"]["OPEN"], 27)
        self.assertEqual(data["status_counts"]["CLOSED"], 56)
        self.assertEqual(data["status_counts"]["DISCARDED"], 13)
        self.assertEqual(data["satisfaction"]["average_score"], 3.84)
        self.assertEqual(data["satisfaction"]["scored_tickets"], 56)

        # Verify zero PII in json response
        response_text = response.text
        self.assertNotIn("@", response_text)

        # Now test export endpoint succeeds with attachment
        export_response = self.client.get("/api/incidents/results/export")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response.headers.get("content-type", ""))
        self.assertIn('attachment; filename="results.csv"', export_response.headers.get("content-disposition", ""))
        self.assertEqual(export_response.headers["content-type"], "text/csv; charset=utf-8")
        self.assertEqual(export_response.headers["cache-control"], "no-cache")
        
        csv_body = export_response.text
        self.assertIn("total_records,100", csv_body)
        self.assertIn("valid_records,96", csv_body)
        self.assertIn("satisfaction_average_score,3.84", csv_body)
        self.assertNotIn("@", csv_body)
        rows = list(csv.reader(io.StringIO(csv_body)))
        self.assertEqual(rows[0], ["metric", "value"])
        self.assertTrue(all(len(row) == 2 for row in rows))

        header = ",".join(REQUIRED_COLUMNS) + "\n"
        scenarios = (
            ("header_only", "", 0, 0, 0, 0),
            ("no_scores", "NXV-000001,2024-01-01,Synthetic Corp,TECHNICAL,Synthetic description,AGT-01,OPEN,synthetic@example.com,\n", 1, 1, 0, 0),
            ("all_invalid", "NXV-000002,2024-01-01,,UNKNOWN,abc,AGT-01,CLOSED,invalid,\n", 1, 0, 1, 5),
        )
        for name, content, total, valid, invalid, errors in scenarios:
            with self.subTest(scenario=name):
                result = self.client.post(
                    "/api/incidents/analyze",
                    files={"file": (name + ".csv", (header + content).encode(), "text/csv")},
                )
                self.assertEqual(result.status_code, 200)
                body = result.json()
                self.assertEqual(set(body), expected_fields)
                self.assertEqual(body["total_records"], total)
                self.assertEqual(body["valid_records"], valid)
                self.assertEqual(body["invalid_records"], invalid)
                self.assertEqual(body["errors_count"], errors)
                self.assertEqual(set(body["category_counts"]), set(VALID_CATEGORIES))
                self.assertEqual(set(body["status_counts"]), set(VALID_STATUSES))
                self.assertIsNone(body["satisfaction"]["average_score"])
                self.assertEqual(body["satisfaction"]["score_distribution"], {str(score): 0 for score in range(1, 6)})
                self.assertNotIn("synthetic@example.com", result.text)
                self.assertNotIn("Synthetic description", result.text)
                self.assertNotIn("row_errors", result.text)
                exported = self.client.get("/api/incidents/results/export")
                self.assertEqual(exported.status_code, 200)
                self.assertEqual(exported.headers["content-type"], "text/csv; charset=utf-8")
                exported_rows = list(csv.reader(io.StringIO(exported.text)))
                self.assertEqual(exported_rows[0], ["metric", "value"])
                metrics = dict(exported_rows[1:])
                self.assertEqual(metrics["total_records"], str(total))
                self.assertEqual(metrics["satisfaction_average_score"], "N/A")
                self.assertNotIn("@", exported.text)


if __name__ == "__main__":
    unittest.main()
