"""Database connectivity, schema initialization, and audit logging for the reporting layer.

Manages connections to Supabase PostgreSQL in production and provides
transparent compatibility for isolated testing engines.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Engine, create_engine, desc, event, select, text, update
from sqlalchemy.pool import StaticPool

from data.pipelines.models import (
    pipeline_execution_logs_table,
    reporting_metadata,
)

logger = logging.getLogger(__name__)

_reporting_engine: Optional[Engine] = None


def normalize_reporting_db_url(url: str) -> str:
    """Normalize Postgres connection URL scheme for SQLAlchemy."""
    stripped = url.strip()
    if stripped.startswith("postgres://"):
        return stripped.replace("postgres://", "postgresql://", 1)
    return stripped


def get_reporting_database_url() -> str:
    """Resolve database URL from environment (SUPABASE_DB_URL or DATABASE_URL)."""
    raw_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if raw_url and raw_url.strip():
        return normalize_reporting_db_url(raw_url)
    return "sqlite:///services/api/data/reporting.db"


def create_reporting_engine(db_url: Optional[str] = None) -> Engine:
    """Create a new SQLAlchemy engine configured for reporting."""
    url = normalize_reporting_db_url(db_url) if db_url else get_reporting_database_url()
    connect_args: dict = {}
    engine_kwargs: dict = {"echo": False}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool

        engine = create_engine(url, connect_args=connect_args, **engine_kwargs)

        @event.listens_for(engine, "connect")
        def _attach_sqlite_reporting_schema(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("ATTACH DATABASE ':memory:' AS reporting;")
            cursor.close()

        return engine

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def get_reporting_engine() -> Engine:
    """Retrieve or initialize singleton reporting engine."""
    global _reporting_engine
    if _reporting_engine is None:
        _reporting_engine = create_reporting_engine()
    return _reporting_engine


def set_reporting_engine(engine: Optional[Engine]) -> None:
    """Set or override singleton reporting engine (primarily for isolated test fixtures)."""
    global _reporting_engine
    _reporting_engine = engine


def init_reporting_db(engine: Optional[Engine] = None) -> None:
    """Initialize reporting schema and tables on the target engine."""
    target_engine = engine or get_reporting_engine()

    url_str = str(target_engine.url)
    if not url_str.startswith("sqlite"):
        with target_engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS reporting;"))

    reporting_metadata.create_all(target_engine)
    logger.info("Reporting database schema initialized successfully.")


# --- Audit Logging & Concurrency Lock Management ---

def create_pipeline_execution_log(
    run_id: UUID,
    flow_name: str,
    trigger_mode: str,
    window_start: date,
    window_end: date,
    started_at: datetime,
    checkpoint_phase: str = "INIT",
    execution_context: Optional[dict[str, Any]] = None,
    engine: Optional[Engine] = None,
) -> None:
    """Persist initial execution audit log row."""
    target_engine = engine or get_reporting_engine()
    context_data = execution_context or {}

    with target_engine.begin() as conn:
        conn.execute(
            pipeline_execution_logs_table.insert().values(
                run_id=run_id,
                flow_name=flow_name,
                trigger_mode=trigger_mode,
                window_start=window_start,
                window_end=window_end,
                started_at=started_at,
                finished_at=None,
                status="RUNNING",
                checkpoint_phase=checkpoint_phase,
                records_extracted=0,
                records_loaded=0,
                error_details=None,
                execution_context=context_data,
            )
        )


def update_pipeline_execution_log(
    run_id: UUID,
    status: Optional[str] = None,
    checkpoint_phase: Optional[str] = None,
    records_extracted: Optional[int] = None,
    records_loaded: Optional[int] = None,
    finished_at: Optional[datetime] = None,
    error_details: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> None:
    """Update progress, status, metrics or error state of a pipeline execution log."""
    target_engine = engine or get_reporting_engine()
    update_values: dict[str, Any] = {}

    if status is not None:
        update_values["status"] = status
    if checkpoint_phase is not None:
        update_values["checkpoint_phase"] = checkpoint_phase
    if records_extracted is not None:
        update_values["records_extracted"] = records_extracted
    if records_loaded is not None:
        update_values["records_loaded"] = records_loaded
    if finished_at is not None:
        update_values["finished_at"] = finished_at
    if error_details is not None:
        update_values["error_details"] = error_details

    if not update_values:
        return

    with target_engine.begin() as conn:
        conn.execute(
            update(pipeline_execution_logs_table)
            .where(pipeline_execution_logs_table.c.run_id == run_id)
            .values(**update_values)
        )


def get_latest_pipeline_run_log(engine: Optional[Engine] = None) -> Optional[dict[str, Any]]:
    """Retrieve metadata of the most recent pipeline execution run."""
    target_engine = engine or get_reporting_engine()

    query = (
        select(pipeline_execution_logs_table)
        .order_by(desc(pipeline_execution_logs_table.c.started_at))
        .limit(1)
    )

    with target_engine.connect() as conn:
        row = conn.execute(query).mappings().first()
        if not row:
            return None
        return dict(row)


def check_window_lock(
    window_start: date,
    engine: Optional[Engine] = None,
    lock_timeout_minutes: int = 30,
) -> bool:
    """Check if an active run is currently executing for this window.

    Lock Policy:
    Runs in 'RUNNING' status started less than `lock_timeout_minutes` ago hold an active lock.
    Locks older than `lock_timeout_minutes` (30 min) are considered abandoned (e.g. killed process)
    and will not block new executions, ensuring auto-recovery without operator intervention.
    """
    target_engine = engine or get_reporting_engine()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lock_timeout_minutes)

    query = (
        select(pipeline_execution_logs_table.c.run_id)
        .where(
            pipeline_execution_logs_table.c.window_start == window_start,
            pipeline_execution_logs_table.c.status == "RUNNING",
            pipeline_execution_logs_table.c.started_at > cutoff,
        )
        .limit(1)
    )

    with target_engine.connect() as conn:
        active = conn.execute(query).scalar_one_or_none()
        return active is not None
