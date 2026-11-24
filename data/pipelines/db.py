"""Database connectivity and schema initialization for the reporting layer.

Manages connections to Supabase PostgreSQL in production and provides
transparent compatibility for isolated testing engines.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.pool import StaticPool

from data.pipelines.models import reporting_metadata

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
    # Default fallback to SQLite in local dev if no Supabase URL configured
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

        # Attach 'reporting' schema on SQLite connections so schema="reporting" queries succeed
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

    # In Postgres, ensure schema exists before creating tables
    url_str = str(target_engine.url)
    if not url_str.startswith("sqlite"):
        with target_engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS reporting;"))

    reporting_metadata.create_all(target_engine)
    logger.info("Reporting database schema initialized successfully.")
