"""Unit and integration tests for the full resilient pipeline flow and CLI (Etapa 3)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from data.pipelines.db import (
    create_reporting_engine,
    init_reporting_db,
    set_reporting_engine,
)
from data.pipelines.models import (
    pipeline_execution_logs_table,
    weekly_office_program_performance_table,
)
from data.pipelines.pipeline import (
    get_iso_week_start,
    weekly_business_performance_pipeline,
)
from services.api.telemetry_storage import (
    init_telemetry_db,
    set_telemetry_engine,
    store_telemetry_events,
)


@pytest.fixture
def isolated_engines():
    """Create in-memory SQLite engines for telemetry and reporting."""
    tel_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_telemetry_db(tel_engine)
    set_telemetry_engine(tel_engine)

    rep_engine = create_reporting_engine("sqlite:///:memory:")
    init_reporting_db(rep_engine)
    set_reporting_engine(rep_engine)

    yield tel_engine, rep_engine

    set_telemetry_engine(None)
    set_reporting_engine(None)


def test_iso_week_start_calculation():
    """Verify ISO week calculation always yields Monday UTC."""
    # Wednesday 2026-11-18 -> Monday 2026-11-16
    wednesday = date(2026, 11, 18)
    assert get_iso_week_start(wednesday) == date(2026, 11, 16)

    # Monday 2026-11-16 -> Monday 2026-11-16
    monday = date(2026, 11, 16)
    assert get_iso_week_start(monday) == date(2026, 11, 16)


def test_pipeline_flow_end_to_end_and_audit_logging(isolated_engines):
    """Verify full pipeline execution extracts, transforms, loads, and writes audit log."""
    tel_engine, rep_engine = isolated_engines
    window_start = date(2026, 11, 16)

    # Seed events
    store_telemetry_events(
        [
            {
                "timestamp": datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc),
                "service": "backoffice",
                "event_type": "inbound_order_created",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {
                    "eventId": str(uuid4()),
                    "office": "valencia",
                    "programme_id": "ai-engineering-core",
                    "total_cost": 500.0,
                    "currency": "EUR",
                },
            },
            {
                "timestamp": datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc),
                "service": "backoffice",
                "event_type": "outbound_order_created",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {
                    "eventId": str(uuid4()),
                    "office": "valencia",
                    "programme_id": "ai-engineering-core",
                    "currency": "EUR",
                },
            },
        ],
        engine=tel_engine,
    )

    result = weekly_business_performance_pipeline(
        target_week_start=window_start,
        trigger_mode="scheduled",
        engine=rep_engine,
        telemetry_engine=tel_engine,
    )

    assert result["status"] == "COMPLETED"
    assert result["records_extracted"] == 2
    assert result["records_loaded"] == 1

    # Verify database state in reporting schema
    with rep_engine.connect() as conn:
        kpi_rows = conn.execute(select(weekly_office_program_performance_table)).mappings().all()
        assert len(kpi_rows) == 1
        assert kpi_rows[0]["office"] == "valencia"
        assert kpi_rows[0]["programme_id"] == "ai-engineering-core"
        assert kpi_rows[0]["total_material_cost"] == 500.0
        assert kpi_rows[0]["kits_delivered_count"] == 1
        assert kpi_rows[0]["currency"] == "EUR"

        log_rows = conn.execute(select(pipeline_execution_logs_table)).mappings().all()
        assert len(log_rows) == 1
        assert log_rows[0]["status"] == "COMPLETED"
        assert log_rows[0]["checkpoint_phase"] == "FINALIZED"
        assert log_rows[0]["records_extracted"] == 2
        assert log_rows[0]["records_loaded"] == 1


def test_pipeline_idempotency_on_multiple_runs(isolated_engines):
    """Verify running the flow multiple times on the same window does not duplicate rows."""
    tel_engine, rep_engine = isolated_engines
    window_start = date(2026, 11, 16)

    store_telemetry_events(
        [
            {
                "timestamp": datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc),
                "service": "backoffice",
                "event_type": "inbound_order_created",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {
                    "eventId": "evt-idempotent-1",
                    "office": "miami",
                    "programme_id": "sales-q4",
                    "unit_cost": 250.0,
                    "quantity": 2,
                    "currency": "USD",
                },
            }
        ],
        engine=tel_engine,
    )

    # First run
    res1 = weekly_business_performance_pipeline(
        target_week_start=window_start,
        trigger_mode="scheduled",
        engine=rep_engine,
        telemetry_engine=tel_engine,
    )
    assert res1["status"] == "COMPLETED"

    # Second run on same window
    res2 = weekly_business_performance_pipeline(
        target_week_start=window_start,
        trigger_mode="manual",
        engine=rep_engine,
        telemetry_engine=tel_engine,
    )
    assert res2["status"] == "COMPLETED"

    # Verify table has exactly 1 row (no duplicate) and run_id was updated to res2
    with rep_engine.connect() as conn:
        kpi_rows = conn.execute(select(weekly_office_program_performance_table)).mappings().all()
        assert len(kpi_rows) == 1
        assert kpi_rows[0]["total_material_cost"] == 500.0
        assert str(kpi_rows[0]["run_id"]) == res2["run_id"]


def test_optional_step_failure_does_not_abort_flow(isolated_engines):
    """Verify failure in optional non-critical task does not interrupt critical ETL path."""
    tel_engine, rep_engine = isolated_engines
    window_start = date(2026, 11, 16)

    store_telemetry_events(
        [
            {
                "timestamp": datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc),
                "service": "backoffice",
                "event_type": "stock_threshold_triggered",
                "level": "warn",
                "value": None,
                "message": None,
                "tags": {
                    "eventId": "evt-optional-1",
                    "office": "valencia",
                    "programme_id": "ai-core",
                    "currency": "EUR",
                },
            }
        ],
        engine=tel_engine,
    )

    # Trigger run with simulate_optional_failure=True
    result = weekly_business_performance_pipeline(
        target_week_start=window_start,
        simulate_optional_failure=True,
        engine=rep_engine,
        telemetry_engine=tel_engine,
    )

    # Flow must still complete successfully
    assert result["status"] == "COMPLETED"
    assert result["records_loaded"] == 1

    with rep_engine.connect() as conn:
        kpi_rows = conn.execute(select(weekly_office_program_performance_table)).mappings().all()
        assert len(kpi_rows) == 1
        assert kpi_rows[0]["shortage_events_count"] == 1


def test_critical_step_failure_marks_run_failed(isolated_engines):
    """Verify critical task failure marks the flow and execution log as FAILED."""
    tel_engine, rep_engine = isolated_engines
    window_start = date(2026, 11, 16)

    result = weekly_business_performance_pipeline(
        target_week_start=window_start,
        simulate_load_failure=True,
        engine=rep_engine,
        telemetry_engine=tel_engine,
    )

    assert result["status"] == "FAILED"
    assert result["phase"] == "LOADING"

    with rep_engine.connect() as conn:
        log_rows = conn.execute(select(pipeline_execution_logs_table)).mappings().all()
        assert len(log_rows) == 1
        assert log_rows[0]["status"] == "FAILED"
        assert "Simulated critical failure" in log_rows[0]["error_details"]
