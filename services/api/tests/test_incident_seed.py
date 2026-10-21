"""Tests for historical incident seed script, validation, transformations and idempotency."""

import os
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.seed_incidents import seed_incidents
from services.api.incident_models import ALLOWED_CATEGORIES
from services.api.incident_storage import open_incident_table


class TestIncidentSeed(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "incidents_test.json")
        os.environ["NEXOVA_INCIDENTS_DB_PATH"] = self.db_path

    def tearDown(self):
        os.environ.pop("NEXOVA_INCIDENTS_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_seed_inserts_exact_96_valid_records_and_skips_4_invalid(self):
        report = seed_incidents()
        self.assertEqual(report["total_processed"], 100)
        self.assertEqual(report["inserted"], 96)
        self.assertEqual(report["skipped_invalid"], 4)
        self.assertEqual(report["skipped_duplicate"], 0)

        with open_incident_table() as table:
            self.assertEqual(len(table), 96)

    def test_seed_distribution_matches_briefing_exact_counts(self):
        seed_incidents()

        with open_incident_table() as table:
            records = table.all()

        statuses = Counter(r["status"] for r in records)
        categories = Counter(r["category"] for r in records)
        origins = Counter(r["origin"] for r in records)
        branches = Counter(r["branch"] for r in records)

        # Expected counts post-transformation per Nexova briefing
        self.assertEqual(statuses["open"], 27)
        self.assertEqual(statuses["resolved"], 56)
        self.assertEqual(statuses["discarded"], 13)
        self.assertEqual(statuses["in_progress"], 0)

        self.assertEqual(categories["technical_failure"], 49)
        self.assertEqual(categories["process_error"], 35)
        self.assertEqual(categories["client_complaint"], 12)

        # Categories with count 0 in seed must be 0
        for zero_category in (
            "candidate_issue",
            "staff_issue",
            "sla_breach",
            "data_quality",
            "other",
        ):
            self.assertEqual(categories[zero_category], 0)

        # Origin is always customer and branch is always central for historical CSV
        self.assertEqual(origins["customer"], 96)
        self.assertEqual(len(origins), 1)
        self.assertEqual(branches["central"], 96)
        self.assertEqual(len(branches), 1)

    def test_seed_is_strictly_idempotent(self):
        first_report = seed_incidents()
        self.assertEqual(first_report["inserted"], 96)
        self.assertEqual(first_report["skipped_duplicate"], 0)

        # Second run on the same database
        second_report = seed_incidents()
        self.assertEqual(second_report["inserted"], 0)
        self.assertEqual(second_report["skipped_duplicate"], 96)
        self.assertEqual(second_report["skipped_invalid"], 4)

        with open_incident_table() as table:
            self.assertEqual(len(table), 96)

    def test_no_pii_or_ticket_id_in_stored_records(self):
        seed_incidents()

        with open_incident_table() as table:
            records = table.all()

        forbidden_fields = {
            "ticket_id",
            "customer_email",
            "agent_id",
            "client_company",
            "satisfaction_score",
        }

        allowed_fields = {
            "title",
            "description",
            "category",
            "status",
            "origin",
            "branch",
            "created_at",
            "updated_at",
        }

        for record in records:
            keys = set(record.keys())
            for forbidden in forbidden_fields:
                self.assertNotIn(
                    forbidden,
                    keys,
                    f"Sensitive or internal field '{forbidden}' must not be stored in incident record",
                )
            self.assertTrue(keys.issubset(allowed_fields))

    def test_title_and_date_transformations(self):
        seed_incidents()

        with open_incident_table() as table:
            records = table.all()

        for record in records:
            title = record["title"]
            self.assertGreater(len(title), 0)
            self.assertLessEqual(len(title), 120)
            self.assertEqual(title, title.strip())

            created_at = datetime.fromisoformat(record["created_at"])
            self.assertEqual(created_at.hour, 0)
            self.assertEqual(created_at.minute, 0)
            self.assertEqual(created_at.second, 0)
            self.assertEqual(created_at.tzinfo, timezone.utc)
            self.assertEqual(record["updated_at"], record["created_at"])


if __name__ == "__main__":
    unittest.main()

