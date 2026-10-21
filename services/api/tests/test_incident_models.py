"""Unit tests for incident models, status transitions and storage."""

import os
import tempfile
import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from services.api.incident_models import (
    ALLOWED_BRANCHES,
    ALLOWED_CATEGORIES,
    ALLOWED_ORIGINS,
    ALLOWED_STATUSES,
    IncidentCreate,
    IncidentRecord,
    IncidentStatusUpdate,
    IncidentSummary,
    validate_status_transition,
)
from services.api.incident_storage import open_incident_table


class TestIncidentModels(unittest.TestCase):
    def test_valid_incident_create_with_defaults(self):
        incident = IncidentCreate(
            title="SSO login error",
            description="User unable to log in via Azure AD",
            category="technical_failure",
            origin="customer",
            branch="central",
        )
        self.assertEqual(incident.title, "SSO login error")
        self.assertEqual(incident.status, "open")
        self.assertEqual(incident.category, "technical_failure")
        self.assertEqual(incident.origin, "customer")
        self.assertEqual(incident.branch, "central")

    def test_title_and_description_strip_and_blank_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            IncidentCreate(
                title="   ",
                description="Valid description",
                category="technical_failure",
                origin="customer",
                branch="central",
            )
        self.assertIn("title must not be blank", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            IncidentCreate(
                title="Valid title",
                description="   \n\t  ",
                category="technical_failure",
                origin="customer",
                branch="central",
            )
        self.assertIn("description must not be blank", str(ctx.exception))

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValidationError):
            IncidentCreate(
                title="Valid title",
                description="Valid description",
                category="unknown_category",  # type: ignore
                origin="customer",
                branch="central",
            )

    def test_invalid_origin_rejected(self):
        with self.assertRaises(ValidationError):
            IncidentCreate(
                title="Valid title",
                description="Valid description",
                category="technical_failure",
                origin="external_partner",  # type: ignore
                branch="central",
            )

    def test_invalid_branch_rejected(self):
        # "headquarters" is forbidden per Nexova briefing; must be "central"
        with self.assertRaises(ValidationError):
            IncidentCreate(
                title="Valid title",
                description="Valid description",
                category="technical_failure",
                origin="customer",
                branch="headquarters",  # type: ignore
            )

    def test_all_briefing_branches_are_allowed(self):
        expected_branches = {"central", "valencia_operations", "miami_office", "remote"}
        self.assertEqual(set(ALLOWED_BRANCHES), expected_branches)
        for branch in expected_branches:
            incident = IncidentCreate(
                title="Test incident",
                description="Branch test",
                category="other",
                origin="internal",
                branch=branch,  # type: ignore
            )
            self.assertEqual(incident.branch, branch)

    def test_all_briefing_categories_are_allowed(self):
        expected_categories = {
            "technical_failure",
            "process_error",
            "client_complaint",
            "candidate_issue",
            "staff_issue",
            "sla_breach",
            "data_quality",
            "other",
        }
        self.assertEqual(set(ALLOWED_CATEGORIES), expected_categories)

    def test_extra_fields_forbidden(self):
        with self.assertRaises(ValidationError):
            IncidentCreate(
                title="Valid title",
                description="Valid description",
                category="technical_failure",
                origin="customer",
                branch="central",
                ticket_id="NXV-000001",  # Extra field
            )

    def test_status_transitions_matrix(self):
        # Valid transitions
        validate_status_transition("open", "in_progress")
        validate_status_transition("open", "discarded")
        validate_status_transition("in_progress", "resolved")
        validate_status_transition("in_progress", "discarded")

        # Invalid direct transition: open -> resolved is not allowed
        with self.assertRaises(ValueError) as ctx:
            validate_status_transition("open", "resolved")
        self.assertIn("Invalid status transition", str(ctx.exception))

        # Terminal state: resolved cannot transition to anything
        for target in ALLOWED_STATUSES:
            with self.assertRaises(ValueError) as ctx:
                validate_status_transition("resolved", target)
            self.assertIn("final", str(ctx.exception))

        # Terminal state: discarded cannot transition to anything
        for target in ALLOWED_STATUSES:
            with self.assertRaises(ValueError) as ctx:
                validate_status_transition("discarded", target)
            self.assertIn("final", str(ctx.exception))

    def test_incident_record_timestamps(self):
        now = datetime.now(timezone.utc)
        record = IncidentRecord(
            id=1,
            title="Database slow query",
            description="High latency on incident query",
            category="technical_failure",
            origin="internal",
            branch="central",
            status="open",
            created_at=now,
            updated_at=now,
        )
        self.assertEqual(record.id, 1)
        self.assertEqual(record.created_at.tzinfo, timezone.utc)


class TestIncidentStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "incidents.json")
        os.environ["NEXOVA_INCIDENTS_DB_PATH"] = self.db_path

    def tearDown(self):
        os.environ.pop("NEXOVA_INCIDENTS_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_open_incident_table_insert_and_retrieve(self):
        with open_incident_table() as table:
            doc_id = table.insert({
                "title": "Incident 1",
                "description": "Test description",
                "category": "technical_failure",
                "origin": "customer",
                "branch": "central",
                "status": "open",
                "created_at": "2026-10-19T00:00:00Z",
                "updated_at": "2026-10-19T00:00:00Z",
            })
            self.assertIsInstance(doc_id, int)
            self.assertGreater(doc_id, 0)

        with open_incident_table() as table:
            doc = table.get(doc_id=doc_id)
            self.assertIsNotNone(doc)
            self.assertEqual(doc["title"], "Incident 1")
            self.assertEqual(len(table), 1)


if __name__ == "__main__":
    unittest.main()

