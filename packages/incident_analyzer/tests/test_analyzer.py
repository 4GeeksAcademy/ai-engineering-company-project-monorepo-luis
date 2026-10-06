"""Unit tests for the incident_analyzer package."""

import io
import unittest
from pathlib import Path

from packages.incident_analyzer import (
    analyze_csv_stream,
    analyze_incidents_file,
    export_results_to_csv_string,
    validate_row,
)


class TestIncidentAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate official fixture
        repo_root = Path(__file__).resolve().parents[3]
        cls.fixture_path = repo_root / "data" / "raw" / "incidents-nexova.csv"
        if not cls.fixture_path.exists():
            cls.fixture_path = repo_root / "scripts" / "incidents-nexova.csv"

    def test_official_nexova_fixture_metrics(self):
        """Verifies exact acceptance criteria from CONTEXT-nexova and script-panel.md."""
        self.assertTrue(self.fixture_path.exists(), f"Fixture missing: {self.fixture_path}")
        result = analyze_incidents_file(self.fixture_path)

        # 1. Total records
        self.assertEqual(result.total_records, 100)
        self.assertEqual(result.valid_records, 96)
        self.assertEqual(result.invalid_records, 4)

        # 2. Categories breakdown
        self.assertEqual(result.category_counts["TECHNICAL"], 28)
        self.assertEqual(result.category_counts["BILLING"], 18)
        self.assertEqual(result.category_counts["ACCESS"], 21)
        self.assertEqual(result.category_counts["HR_QUERY"], 17)
        self.assertEqual(result.category_counts["COMPLAINT"], 12)

        # 3. Status breakdown
        self.assertEqual(result.status_counts["OPEN"], 27)
        self.assertEqual(result.status_counts["CLOSED"], 56)
        self.assertEqual(result.status_counts["DISCARDED"], 13)

        # 4. Invalid breakdown expected
        self.assertEqual(result.invalid_breakdown.get("Missing client_company"), 1)
        self.assertEqual(result.invalid_breakdown.get("Invalid or missing category"), 1)
        self.assertEqual(result.invalid_breakdown.get("Invalid or missing email"), 1)
        self.assertEqual(result.invalid_breakdown.get("Closed ticket, no score"), 1)

        # 5. Satisfaction
        sat = result.satisfaction
        self.assertEqual(sat.total_closed_tickets, 56)
        self.assertEqual(sat.scored_tickets, 56)
        self.assertEqual(sat.score_distribution[1], 2)
        self.assertEqual(sat.score_distribution[2], 5)
        self.assertEqual(sat.score_distribution[3], 10)
        self.assertEqual(sat.score_distribution[4], 22)
        self.assertEqual(sat.score_distribution[5], 17)
        self.assertAlmostEqual(sat.average_score, 3.84, places=2)

    def test_privacy_no_pii_in_errors_or_exports(self):
        """Ensures customer email or sensitive details never leak into errors or exports."""
        raw_csv = (
            "ticket_id,date,client_company,category,description,agent_id,status,customer_email,satisfaction_score\n"
            "NXV-000001,2024-01-01,Test Corp,TECHNICAL,Valid description,AGT-01,CLOSED,secret.user@example.com,5\n"
            "NXV-000002,2024-01-01,Test Corp,TECHNICAL,Short,AGT-01,CLOSED,another.secret@domain.com,5\n"
        )
        stream = io.StringIO(raw_csv)
        result = analyze_csv_stream(stream)

        # Ensure no emails in row error messages
        for err in result.row_errors:
            self.assertNotIn("secret.user@example.com", err.message)
            self.assertNotIn("another.secret@domain.com", err.message)
            self.assertNotIn("@", err.message)

        # Ensure no emails in CSV export
        exported_csv = export_results_to_csv_string(result)
        self.assertNotIn("secret.user@example.com", exported_csv)
        self.assertNotIn("another.secret@domain.com", exported_csv)
        self.assertNotIn("@", exported_csv)

    def test_empty_and_corrupt_files(self):
        """Ensures proper validation errors when CSV is empty or headers are missing."""
        # Empty file
        with self.assertRaises(ValueError):
            analyze_csv_stream(io.StringIO(""))

        # Missing required header column
        bad_header = (
            "ticket_id,date,client_company,category,description,agent_id,status\n"
        )
        with self.assertRaises(ValueError):
            analyze_csv_stream(io.StringIO(bad_header))

    def test_multiple_errors_on_single_row(self):
        """A row with multiple errors counts once as invalid, but tracks each rule."""
        row = {
            "ticket_id": "NXV-000001",
            "date": "2024-01-01",
            "client_company": "",  # error 1
            "category": "INVALID_CAT",  # error 2
            "description": "abc",  # error 3 (< 5 chars)
            "agent_id": "AGT-01",
            "status": "CLOSED",
            "customer_email": "bademail",  # error 4 (no @)
            "satisfaction_score": "",  # error 5 (CLOSED but empty)
        }
        is_valid, errors, score = validate_row(row, row_number=2)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 5)
        self.assertIsNone(score)

    def test_satisfaction_score_variations(self):
        """Tests satisfaction score boundaries: 0, 6, decimal, text, and valid integers."""
        base_row = {
            "ticket_id": "NXV-000001",
            "date": "2024-01-01",
            "client_company": "Acme Corp",
            "category": "TECHNICAL",
            "description": "Valid issue description",
            "agent_id": "AGT-01",
            "status": "CLOSED",
            "customer_email": "test@domain.com",
            "satisfaction_score": "",
        }

        # CLOSED without score -> invalid
        valid, errs, _ = validate_row(base_row, 2)
        self.assertFalse(valid)
        self.assertEqual(errs[0].rule_key, "closed_no_score")

        # Score 0 -> invalid
        base_row["satisfaction_score"] = "0"
        valid, errs, _ = validate_row(base_row, 2)
        self.assertFalse(valid)
        self.assertEqual(errs[0].rule_key, "invalid_score")

        # Score 6 -> invalid
        base_row["satisfaction_score"] = "6"
        valid, errs, _ = validate_row(base_row, 2)
        self.assertFalse(valid)
        self.assertEqual(errs[0].rule_key, "invalid_score")

        # Decimal score 4.5 -> invalid
        base_row["satisfaction_score"] = "4.5"
        valid, errs, _ = validate_row(base_row, 2)
        self.assertFalse(valid)
        self.assertEqual(errs[0].rule_key, "invalid_score")

        # Text score "good" -> invalid
        base_row["satisfaction_score"] = "good"
        valid, errs, _ = validate_row(base_row, 2)
        self.assertFalse(valid)
        self.assertEqual(errs[0].rule_key, "invalid_score")

        # Valid score 5 -> valid
        base_row["satisfaction_score"] = "5"
        valid, errs, score = validate_row(base_row, 2)
        self.assertTrue(valid)
        self.assertEqual(score, 5)

        # OPEN with empty score -> valid
        base_row["status"] = "OPEN"
        base_row["satisfaction_score"] = ""
        valid, errs, score = validate_row(base_row, 2)
        self.assertTrue(valid)
        self.assertIsNone(score)

    def test_zero_scored_tickets_no_division_by_zero(self):
        """Handles cases with no scored closed tickets without division by zero."""
        raw_csv = (
            "ticket_id,date,client_company,category,description,agent_id,status,customer_email,satisfaction_score\n"
            "NXV-000001,2024-01-01,Test Corp,TECHNICAL,Valid description,AGT-01,OPEN,test@example.com,\n"
        )
        result = analyze_csv_stream(io.StringIO(raw_csv))
        self.assertEqual(result.total_records, 1)
        self.assertEqual(result.valid_records, 1)
        self.assertEqual(result.satisfaction.scored_tickets, 0)
        self.assertIsNone(result.satisfaction.average_score)

        exported_csv = export_results_to_csv_string(result)
        self.assertIn("satisfaction_average_score,N/A", exported_csv)

    def test_special_characters_quotes_and_crlf(self):
        """Tests commas inside quotes, spanish accents, and CRLF line endings."""
        csv_content = (
            "ticket_id,date,client_company,category,description,agent_id,status,customer_email,satisfaction_score\r\n"
            'NXV-000001,2024-01-01,"Empresa Española, S.L.",TECHNICAL,"Fallo en autenticación, error 500",AGT-01,CLOSED,user@test.es,4\r\n'
        )
        result = analyze_csv_stream(io.StringIO(csv_content))
        self.assertEqual(result.total_records, 1)
        self.assertEqual(result.valid_records, 1)
        self.assertEqual(result.category_counts["TECHNICAL"], 1)
        self.assertEqual(result.satisfaction.average_score, 4.0)


if __name__ == "__main__":
    unittest.main()

