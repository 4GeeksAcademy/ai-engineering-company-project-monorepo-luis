"""Domain models and lifecycle validations for Nexova incident records."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

IncidentStatus = Literal["open", "in_progress", "resolved", "discarded"]
IncidentOrigin = Literal["customer", "branch", "internal"]
IncidentBranch = Literal["central", "valencia_operations", "miami_office", "remote"]
IncidentCategory = Literal[
    "technical_failure",
    "process_error",
    "client_complaint",
    "candidate_issue",
    "staff_issue",
    "sla_breach",
    "data_quality",
    "other",
]

ALLOWED_STATUSES: tuple[IncidentStatus, ...] = (
    "open",
    "in_progress",
    "resolved",
    "discarded",
)

ALLOWED_ORIGINS: tuple[IncidentOrigin, ...] = (
    "customer",
    "branch",
    "internal",
)

ALLOWED_BRANCHES: tuple[IncidentBranch, ...] = (
    "central",
    "valencia_operations",
    "miami_office",
    "remote",
)

ALLOWED_CATEGORIES: tuple[IncidentCategory, ...] = (
    "technical_failure",
    "process_error",
    "client_complaint",
    "candidate_issue",
    "staff_issue",
    "sla_breach",
    "data_quality",
    "other",
)

ALLOWED_STATUS_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    "open": {"in_progress", "discarded"},
    "in_progress": {"resolved", "discarded"},
    "resolved": set(),
    "discarded": set(),
}


def validate_status_transition(
    current_status: IncidentStatus, new_status: IncidentStatus
) -> None:
    """
    Validate lifecycle status transition according to Nexova rules.
    Raises ValueError with explanatory message on invalid transitions.
    """
    if current_status in ("resolved", "discarded"):
        raise ValueError(
            f"Cannot change status of a {current_status} incident; status is final"
        )
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions from '{current_status}': {sorted(list(allowed)) or 'none'}"
        )


class IncidentBase(BaseModel):
    """Core incident fields shared across creation and persisted record."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: IncidentCategory
    origin: IncidentOrigin
    branch: IncidentBranch

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("description must not be blank")
        return normalized


class IncidentCreate(IncidentBase):
    """Payload for creating a new incident."""

    status: IncidentStatus = "open"


class IncidentStatusUpdate(BaseModel):
    """Payload for updating an incident's status."""

    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus


class IncidentRecord(IncidentBase):
    """Incident record as persisted and returned by API."""

    id: int = Field(gt=0)
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class IncidentSummary(BaseModel):
    """Aggregated operational metrics across incident dimensions."""

    total: int = Field(default=0, ge=0)
    by_status: dict[IncidentStatus, int]
    by_category: dict[IncidentCategory, int]
    by_origin: dict[IncidentOrigin, int]
    by_branch: dict[IncidentBranch, int]

