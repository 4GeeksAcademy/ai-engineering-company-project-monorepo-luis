"""Unit tests for the reporting database schema and models (Etapa 1)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from data.pipelines.db import (
    create_reporting_engine,
    init_reporting_db,
    set_reporting_engine,
)
from data.pipelines.models import (
    PipelineRunMetadata,
    WeeklyPerformanceEntry,
    WeeklyPerformanceResponse,
    pipeline_execution_logs_table,
    weekly_office_program_performance_table,
)


@pytest.fixture
def reporting_test_engine():
    """Create isolated in-memory SQLite reporting engine."""
    engine = create_reporting_engine("sqlite:///:memory:")
    init_reporting_db(engine)
    set_reporting_engine(engine)
    yield engine
    set_reporting_engine(None)


def test_reporting_tables_created_and_accessible(reporting_test_engine):
    """Verify both reporting tables are created and accept valid data."""
    test_run_id = uuid4()
    test_week = date(2026, 11, 16)

    with reporting_test_engine.begin() as conn:
        # Insert log
        conn.execute(
            pipeline_execution_logs_table.insert().values(
                run_id=test_run_id,
                flow_name="weekly_business_performance_pipeline",
                trigger_mode="scheduled",
                window_start=test_week,
                window_end=date(2026, 11, 23),
                started_at=datetime.now(timezone.utc),
                status="COMPLETED",
                checkpoint_phase="FINALIZED",
                records_extracted=100,
                records_loaded=2,
                execution_context={"version": "1.0.0"},
            )
        )

        # Insert performance metric
        conn.execute(
            weekly_office_program_performance_table.insert().values(
                office="valencia",
                programme_id="ai-engineering-core",
                week_start=test_week,
                total_material_cost=1500.50,
                kits_delivered_count=20,
                shortage_events_count=1,
                cost_variance_events_count=0,
                currency="EUR",
                computed_at=datetime.now(timezone.utc),
                run_id=test_run_id,
            )
        )

    with reporting_test_engine.connect() as conn:
        # Read back log
        log_row = conn.execute(
            select(pipeline_execution_logs_table).where(
                pipeline_execution_logs_table.c.run_id == test_run_id
            )
        ).mappings().one()
        assert log_row["flow_name"] == "weekly_business_performance_pipeline"
        assert log_row["status"] == "COMPLETED"

        # Read back metric
        perf_row = conn.execute(
            select(weekly_office_program_performance_table).where(
                weekly_office_program_performance_table.c.office == "valencia"
            )
        ).mappings().one()
        assert perf_row["total_material_cost"] == 1500.50
        assert perf_row["currency"] == "EUR"
        assert perf_row["kits_delivered_count"] == 20


def test_reporting_unique_constraint_on_grain(reporting_test_engine):
    """Verify grain uniqueness constraint (office, programme_id, week_start)."""
    test_run_id = uuid4()
    test_week = date(2026, 11, 16)

    with reporting_test_engine.begin() as conn:
        conn.execute(
            weekly_office_program_performance_table.insert().values(
                office="miami",
                programme_id="b2b-sales",
                week_start=test_week,
                total_material_cost=3000.00,
                kits_delivered_count=15,
                shortage_events_count=0,
                cost_variance_events_count=2,
                currency="USD",
                computed_at=datetime.now(timezone.utc),
                run_id=test_run_id,
            )
        )

    # Attempt inserting duplicate grain must fail
    with pytest.raises(IntegrityError):
        with reporting_test_engine.begin() as conn:
            conn.execute(
                weekly_office_program_performance_table.insert().values(
                    office="miami",
                    programme_id="b2b-sales",
                    week_start=test_week,
                    total_material_cost=4000.00,
                    kits_delivered_count=25,
                    shortage_events_count=0,
                    cost_variance_events_count=0,
                    currency="USD",
                    computed_at=datetime.now(timezone.utc),
                    run_id=uuid4(),
                )
            )


def test_pydantic_reporting_models():
    """Verify Pydantic models serialization and validation."""
    entry = WeeklyPerformanceEntry(
        office="valencia",
        programme_id="ai-engineering-core",
        total_material_cost=1240.50,
        kits_delivered_count=18,
        shortage_events_count=1,
        cost_variance_events_count=0,
        currency="EUR",
    )
    response = WeeklyPerformanceResponse(
        week_start="2026-07-13",
        entries=[entry],
    )
    serialized = response.model_dump()
    assert serialized["week_start"] == "2026-07-13"
    assert len(serialized["entries"]) == 1
    assert serialized["entries"][0]["total_material_cost"] == 1240.50
    assert serialized["entries"][0]["currency"] == "EUR"
