"""Telemetry persistence layer for Supabase / PostgreSQL.

Provides atomic bulk persistence for telemetry events without touching inventory
or auth tables, and strictly preventing silent fallback to local SQLite.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    MetaData,
    Numeric,
    String,
    Table,
    Uuid,
    create_engine,
    insert,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

logger = logging.getLogger(__name__)

# Dedicated metadata isolated from SQLModel.metadata to avoid polluting inventory / SQLite
telemetry_metadata = MetaData()

telemetry_events_table = Table(
    "telemetry_events",
    telemetry_metadata,
    Column("id", Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("service", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("level", String, nullable=False, server_default="info"),
    Column("value", Numeric, nullable=True),
    Column("message", String, nullable=True),
    Column("tags", JSONB().with_variant(JSON, "sqlite"), nullable=False, server_default=text("'{}'")),
)

_telemetry_engine: Optional[Engine] = None


class TelemetryStorageError(Exception):
    """Base error for telemetry persistence failures."""


class TelemetryDatabaseNotConfiguredError(TelemetryStorageError):
    """Raised when Supabase / PostgreSQL database URL is missing or set to SQLite."""


def normalize_db_url(url: str) -> str:
    """Normalize Postgres URL scheme for SQLAlchemy compatibility."""
    stripped = url.strip()
    if stripped.startswith("postgres://"):
        return stripped.replace("postgres://", "postgresql://", 1)
    return stripped


def get_telemetry_database_url() -> str:
    """Retrieve Supabase / PostgreSQL URL from environment.

    Strictly refuses to fall back to SQLite to comply with project criteria.
    """
    raw_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not raw_url or not raw_url.strip():
        raise TelemetryDatabaseNotConfiguredError(
            "Telemetry storage requires a configured Supabase / PostgreSQL connection. "
            "Neither SUPABASE_DB_URL nor DATABASE_URL is set."
        )

    normalized = normalize_db_url(raw_url)
    if normalized.startswith("sqlite"):
        raise TelemetryDatabaseNotConfiguredError(
            "Telemetry storage cannot use SQLite fallback. Supabase PostgreSQL is required."
        )

    return normalized


def create_telemetry_engine(db_url: Optional[str] = None) -> Engine:
    """Create a new SQLAlchemy engine for telemetry persistence."""
    url = normalize_db_url(db_url) if db_url else get_telemetry_database_url()
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {"echo": False}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def get_telemetry_engine() -> Engine:
    """Get or initialize singleton telemetry engine."""
    global _telemetry_engine
    if _telemetry_engine is None:
        _telemetry_engine = create_telemetry_engine()
    return _telemetry_engine


def set_telemetry_engine(engine: Optional[Engine]) -> None:
    """Override singleton engine (useful for isolated tests)."""
    global _telemetry_engine
    _telemetry_engine = engine


def init_telemetry_db(target_engine: Optional[Engine] = None) -> None:
    """Create telemetry_events table on target engine if not present."""
    engine = target_engine or get_telemetry_engine()
    telemetry_metadata.create_all(engine)


def store_telemetry_events(
    rows: list[dict[str, Any]],
    engine: Optional[Engine] = None,
) -> int:
    """Persist a batch of mapped telemetry event rows in a single atomic bulk operation.

    - If rows is empty, returns 0 without opening a transaction or connection.
    - All rows are inserted in a single transaction.
    - If database insertion fails, transaction is rolled back and a sanitized exception is raised.
    - Returns the count of successfully persisted rows.
    """
    if not rows:
        return 0

    target_engine = engine or get_telemetry_engine()

    try:
        with target_engine.begin() as connection:
            connection.execute(insert(telemetry_events_table), rows)
        return len(rows)
    except Exception as exc:
        logger.error(
            "Telemetry bulk insert failed during atomic transaction: error_type=%s",
            type(exc).__name__,
        )
        raise TelemetryStorageError("Telemetry database persistence failed") from None
