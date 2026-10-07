"""Tests for the Nexova incident API endpoints."""

import io
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.routers.incidents import set_latest_result


class TestIncidentsAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        set_latest_result(None)  # Reset state before each test
        repo_root = Path(__file__).resolve().parents[3]
        self.fixture_path = repo_root / "data" / "raw" / "incidents-nexova.csv"

    def test_health_check(self):
        """Verifies health check endpoint returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "nexova-api"})

    def test_export_without_prior_analysis_returns_404(self):
        """Export before running an analysis must return 404 Not Found."""
        response = self.client.get("/api/incidents/results/export")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No analysis results available", response.json()["detail"])

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

    def test_analyze_missing_header_columns(self):
        """Reject CSV with invalid headers."""
        bad_csv = b"ticket_id,date,client_company\n1,2,3\n"
        files = {"file": ("incomplete.csv", bad_csv, "text/csv")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required columns", response.json()["detail"])

    def test_analyze_official_fixture_and_export(self):
        """Full end-to-end test with official Nexova fixture."""
        self.assertTrue(self.fixture_path.exists(), f"Fixture missing: {self.fixture_path}")
        with open(self.fixture_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": ("incidents-nexova.csv", file_bytes, "text/csv")}
        response = self.client.post("/api/incidents/analyze", files=files)
        self.assertEqual(response.status_code, 200)

        data = response.json()
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
        
        csv_body = export_response.text
        self.assertIn("total_records,100", csv_body)
        self.assertIn("valid_records,96", csv_body)
        self.assertIn("satisfaction_average_score,3.84", csv_body)
        self.assertNotIn("@", csv_body)


if __name__ == "__main__":
    unittest.main()
