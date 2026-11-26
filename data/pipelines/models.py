"""SQLAlchemy tables and Pydantic schemas for the Business Performance Data Pipeline.

Adheres strictly to the architectural contract in data/pipelines/PIPELINE_DESIGN.md.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# Dedicated metadata for the reporting schema
reporting_metadata = MetaData(schema="reporting")

# 1. Weekly Office & Programme Performance Table
weekly_office_program_performance_table = Table(
    "weekly_office_program_performance",
    reporting_metadata,
    Column("id", Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")),
    Column("office", String(20), nullable=False),
    Column("programme_id", String(100), nullable=False),
    Column("week_start", Date, nullable=False),
    Column("total_material_cost", Numeric(14, 2), nullable=False, server_default="0.00"),
    Column("kits_delivered_count", Integer, nullable=False, server_default="0"),
    Column("shortage_events_count", Integer, nullable=False, server_default="0"),
    Column("cost_variance_events_count", Integer, nullable=False, server_default="0"),
    Column("currency", String(3), nullable=False),
    Column("computed_at", DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")),
    Column("run_id", Uuid, nullable=False),
    CheckConstraint("office IN ('valencia', 'miami')", name="chk_office"),
    CheckConstraint(
        "(office = 'valencia' AND currency = 'EUR') OR (office = 'miami' AND currency = 'USD')",
        name="chk_currency",
    ),
    CheckConstraint("total_material_cost >= 0", name="chk_non_negative_cost"),
    CheckConstraint(
        "kits_delivered_count >= 0 AND shortage_events_count >= 0 AND cost_variance_events_count >= 0",
        name="chk_non_negative_counts",
    ),
    UniqueConstraint("office", "programme_id", "week_start", name="uq_weekly_office_programme"),
    schema="reporting",
)

# 2. Pipeline Execution Logs Table
pipeline_execution_logs_table = Table(
    "pipeline_execution_logs",
    reporting_metadata,
    Column("run_id", Uuid, primary_key=True),
    Column("flow_name", String(100), nullable=False),
    Column("trigger_mode", String(20), nullable=False),
    Column("window_start", Date, nullable=False),
    Column("window_end", Date, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", String(20), nullable=False),
    Column("checkpoint_phase", String(50), nullable=False),
    Column("records_extracted", Integer, nullable=False, server_default="0"),
    Column("records_loaded", Integer, nullable=False, server_default="0"),
    Column("error_details", Text, nullable=True),
    Column(
        "execution_context",
        JSONB().with_variant(JSON, "sqlite"),
        nullable=False,
        server_default=text("'{}'"),
    ),
    CheckConstraint(
        "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', 'ABORTED')",
        name="chk_log_status",
    ),
    CheckConstraint(
        "trigger_mode IN ('scheduled', 'manual', 'backfill', 'late_event_recalc')",
        name="chk_log_trigger",
    ),
    schema="reporting",
)


# --- Pydantic Schemas for Nexova Reporting API Contract ---

class WeeklyPerformanceEntry(BaseModel):
    """Single row representing aggregated business KPIs for an office and programme."""
    office: str = Field(..., description="Operational office location (valencia or miami)")
    programme_id: str = Field(..., description="Training programme identifier")
    total_material_cost: float = Field(..., ge=0, description="Total cost of inbound orders for the week")
    kits_delivered_count: int = Field(..., ge=0, description="Total count of outbound kits delivered")
    shortage_events_count: int = Field(..., ge=0, description="Total count of shortage alerts")
    cost_variance_events_count: int = Field(..., ge=0, description="Total count of cost variance anomalies")
    currency: str = Field(..., description="Local operating currency (EUR or USD)")


class WeeklyPerformanceResponse(BaseModel):
    """Response contract for GET /reporting/weekly-office-program-performance."""
    week_start: str = Field(..., description="ISO week start date (YYYY-MM-DD, Monday UTC)")
    entries: list[WeeklyPerformanceEntry] = Field(default_factory=list, description="Aggregated KPI rows")


class PipelineRunMetadata(BaseModel):
    """Metadata response for GET /reporting/pipeline-runs/latest."""
    run_id: str
    flow_name: str
    status: str
    trigger_mode: str
    window_start: str
    window_end: str
    started_at: str
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    records_extracted: int = 0
    records_loaded: int = 0
    checkpoint_phase: str
    error_details: Optional[str] = None


class TriggerPipelineRequest(BaseModel):
    """Request body for POST /reporting/pipeline-runs."""
    target_week_start: Optional[date] = None
    reprocess_buffer_week: bool = False
    reason: Optional[str] = None


class TriggerPipelineResponse(BaseModel):
    """Response body for POST /reporting/pipeline-runs."""
    run_id: str
    status: str
    target_week_start: Optional[str] = None
    message: str
