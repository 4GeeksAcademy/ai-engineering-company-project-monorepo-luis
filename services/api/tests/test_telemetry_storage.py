"""Unit tests for telemetry persistence layer (telemetry_storage.py)."""

from datetime import datetime, timezone
import logging
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select

from services.api.telemetry_storage import (
    TelemetryDatabaseNotConfiguredError,
    TelemetryStorageError,
    get_telemetry_database_url,
    init_telemetry_db,
    set_telemetry_engine,
    store_telemetry_events,
    telemetry_events_table,
)


@pytest.fixture(autouse=True)
def clean_engine():
    set_telemetry_engine(None)
    yield
    set_telemetry_engine(None)


def test_sqlite_fallback_is_strictly_rejected(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///services/api/data/inventory.db")
    with pytest.raises(TelemetryDatabaseNotConfiguredError, match="cannot use SQLite fallback"):
        get_telemetry_database_url()


def test_missing_database_url_is_rejected(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(TelemetryDatabaseNotConfiguredError, match="requires a configured Supabase"):
        get_telemetry_database_url()


def test_supabase_db_url_is_normalized_and_accepted(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://user:pass@ep-test.pooler.supabase.com:6543/postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = get_telemetry_database_url()
    assert url == "postgresql://user:pass@ep-test.pooler.supabase.com:6543/postgres"


def test_store_telemetry_events_empty_list_does_not_open_db():
    mock_engine = MagicMock()
    stored_count = store_telemetry_events([], engine=mock_engine)
    assert stored_count == 0
    mock_engine.begin.assert_not_called()


def test_store_telemetry_events_bulk_success():
    engine = create_engine("sqlite:///:memory:")
    init_telemetry_db(engine)

    rows = [
        {
            "timestamp": datetime(2026, 11, 18, 19, 0, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {"office": "valencia", "quantity": 5},
        },
        {
            "timestamp": datetime(2026, 11, 18, 19, 1, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "api_latency_recorded",
            "level": "info",
            "value": 120.5,
            "message": None,
            "tags": {"route_group": "inventory_read", "duration_ms": 120.5},
        },
    ]

    count = store_telemetry_events(rows, engine=engine)
    assert count == 2

    with engine.connect() as conn:
        records = conn.execute(select(telemetry_events_table)).fetchall()
        assert len(records) == 2
        assert records[0].event_type == "inbound_order_created"
        assert records[0].service == "backoffice"
        assert records[0].tags == {"office": "valencia", "quantity": 5}
        assert records[1].event_type == "api_latency_recorded"
        assert float(records[1].value) == 120.5


def test_store_telemetry_events_atomic_rollback_on_failure(caplog):
    engine = create_engine("sqlite:///:memory:")
    init_telemetry_db(engine)

    # Insert initial row
    initial_row = {
        "timestamp": datetime(2026, 11, 18, 18, 0, 0, tzinfo=timezone.utc),
        "service": "backoffice",
        "event_type": "initial_event",
        "level": "info",
        "value": None,
        "message": None,
        "tags": {},
    }
    store_telemetry_events([initial_row], engine=engine)

    # Prepare batch with one valid and one row that causes a constraint violation
    # Timestamp is NOT NULL, passing None will fail in SQL
    failing_batch = [
        {
            "timestamp": datetime(2026, 11, 18, 19, 0, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "valid_in_batch",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {},
        },
        {
            "timestamp": None,  # Violates NOT NULL constraint
            "service": "backoffice",
            "event_type": "invalid_sql_row",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {},
        },
    ]

    with caplog.at_level(logging.ERROR):
        with pytest.raises(TelemetryStorageError, match="Telemetry database persistence failed"):
            store_telemetry_events(failing_batch, engine=engine)

    # Verify atomic rollback: valid_in_batch must NOT have been saved
    with engine.connect() as conn:
        records = conn.execute(select(telemetry_events_table)).fetchall()
        assert len(records) == 1
        assert records[0].event_type == "initial_event"

    # Verify no raw sensitive data or credentials in error logs
    for record in caplog.records:
        assert "password" not in record.getMessage()
        assert "valid_in_batch" not in record.getMessage()
