"""Tests for supplier seeding and TinyDB persistence."""

import os
import tempfile
import unittest
from unittest.mock import patch

from tinydb import Query

from services.api.seed import SUPPLIERS_SEED, seed_suppliers
from services.api.supplier_storage import open_supplier_table


class TestSupplierSeed(unittest.TestCase):
    def test_seed_is_idempotent_and_preserves_optional_fields(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = os.path.join(temporary_directory, "suppliers.json")
            with patch.dict(os.environ, {"NEXOVA_SUPPLIERS_DB_PATH": database_path}):
                self.assertEqual(seed_suppliers(), (15, 0))
                with open_supplier_table() as table:
                    original_records = table.all()
                    self.assertEqual(len(original_records), 15)
                    query = Query()
                    infojobs = table.get(
                        (query.name == "InfoJobs Premium")
                        & (query.country == "Spain")
                    )
                    self.assertIsNotNone(infojobs)
                    self.assertNotIn("notes", infojobs)

                self.assertEqual(seed_suppliers(), (0, 15))
                with open_supplier_table() as table:
                    self.assertEqual(table.all(), original_records)

    def test_seed_contains_exactly_fifteen_suppliers(self):
        self.assertEqual(len(SUPPLIERS_SEED), 15)


if __name__ == "__main__":
    unittest.main()