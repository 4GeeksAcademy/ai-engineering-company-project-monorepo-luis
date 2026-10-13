"""Unit tests for supplier input and response models."""

import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from services.api.supplier_models import SupplierCreate, SupplierRecord


VALID_SUPPLIER = {
    "name": "Example Supplier",
    "country": "Spain",
    "categories": ["job_boards"],
    "monthly_rate": 100.0,
    "currency": "EUR",
    "status": "active",
}


class TestSupplierModels(unittest.TestCase):
    def test_valid_supplier_accepts_optional_fields_as_absent(self):
        supplier = SupplierCreate.model_validate(VALID_SUPPLIER)

        self.assertEqual(supplier.name, "Example Supplier")
        self.assertNotIn("notes", supplier.model_dump(exclude_none=True))

    def test_country_currency_must_match(self):
        invalid_supplier = {**VALID_SUPPLIER, "currency": "USD"}

        with self.assertRaises(ValidationError):
            SupplierCreate.model_validate(invalid_supplier)

    def test_rate_must_be_positive_and_finite(self):
        for monthly_rate in (0, -1, float("inf"), float("nan")):
            with self.subTest(monthly_rate=monthly_rate):
                invalid_supplier = {**VALID_SUPPLIER, "monthly_rate": monthly_rate}
                with self.assertRaises(ValidationError):
                    SupplierCreate.model_validate(invalid_supplier)

    def test_categories_status_country_and_email_are_validated(self):
        invalid_values = (
            {"categories": ["other"]},
            {"categories": []},
            {"status": "deleted"},
            {"country": "Spain", "currency": "USD"},
            {"country": "USA", "currency": "EUR"},
            {"country": "France"},
            {"contact_email": "not-an-email"},
        )
        for changes in invalid_values:
            with self.subTest(changes=changes):
                invalid_supplier = {**VALID_SUPPLIER, **changes}
                with self.assertRaises(ValidationError):
                    SupplierCreate.model_validate(invalid_supplier)

    def test_renewal_date_must_be_exact_iso_date(self):
        for renewal_date in ("2025-2-03", "2025-02-30", "03/02/2025"):
            with self.subTest(renewal_date=renewal_date):
                invalid_supplier = {
                    **VALID_SUPPLIER,
                    "contract_renewal_date": renewal_date,
                }
                with self.assertRaises(ValidationError):
                    SupplierCreate.model_validate(invalid_supplier)

    def test_client_cannot_set_server_managed_fields(self):
        for field_name, value in (("id", 15), ("updated_at", "2026-10-13T00:00:00Z")):
            with self.subTest(field_name=field_name):
                invalid_supplier = {**VALID_SUPPLIER, field_name: value}
                with self.assertRaises(ValidationError):
                    SupplierCreate.model_validate(invalid_supplier)

    def test_supplier_record_normalizes_timestamp_to_utc(self):
        record = SupplierRecord.model_validate(
            {
                **VALID_SUPPLIER,
                "id": 1,
                "updated_at": "2026-10-13T12:00:00+02:00",
            }
        )

        self.assertEqual(record.updated_at, datetime(2026, 10, 13, 10, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()