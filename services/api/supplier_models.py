"""Pydantic models for supplier input and persisted API records."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

SupplierCountry = Literal["Spain", "USA"]
SupplierCategory = Literal[
    "job_boards",
    "ats_software",
    "assessment_tools",
    "training_platforms",
    "payroll_and_hr_software",
    "video_interview",
    "background_check",
    "office_and_facilities",
    "it_and_software_licenses",
]
SupplierStatus = Literal["active", "suspended"]


class SupplierCreate(BaseModel):
    """Client-controlled supplier fields; server fields are deliberately excluded."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    country: SupplierCountry
    categories: list[SupplierCategory] = Field(min_length=1)
    monthly_rate: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal["EUR", "USD"]
    status: SupplierStatus
    contract_renewal_date: str | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized

    @field_validator("contract_renewal_date")
    @classmethod
    def renewal_date_must_be_iso_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("contract_renewal_date must use YYYY-MM-DD") from error
        if parsed.isoformat() != value:
            raise ValueError("contract_renewal_date must use YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def currency_must_match_country(self) -> "SupplierCreate":
        expected_currency = "EUR" if self.country == "Spain" else "USD"
        if self.currency != expected_currency:
            raise ValueError(f"currency for {self.country} must be {expected_currency}")
        return self


class SupplierRecord(SupplierCreate):
    """Supplier as stored and returned by the API."""

    id: int = Field(gt=0)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def updated_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        return value.astimezone(timezone.utc)