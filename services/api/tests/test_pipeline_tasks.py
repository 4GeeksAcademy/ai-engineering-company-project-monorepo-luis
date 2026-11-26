"""Unit tests for pipeline extraction and transformation tasks with caching (Etapa 2)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from prefect import flow
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from data.pipelines.queries import (
    extract_telemetry_records,
    transform_events_to_weekly_kpis,
)
from data.pipelines.tasks import (
    compute_transform_cache_key,
    extract_telemetry_events,
    transform_weekly_kpis,
)
from services.api.telemetry_storage import (
    init_telemetry_db,
    set_telemetry_engine,
    store_telemetry_events,
)


@pytest.fixture
def telemetry_test_engine():
    """Create isolated in-memory SQLite engine for telemetry events store."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_telemetry_db(engine)
    set_telemetry_engine(engine)
    yield engine
    set_telemetry_engine(None)


def test_extraction_filters_window_and_deduplicates(telemetry_test_engine):
    """Verify extraction only fetches pipeline events within window and deduplicates by eventId."""
    window_start = date(2026, 11, 16)
    window_end = date(2026, 11, 23)

    event_id_shared = str(uuid4())

    raw_batch = [
        # In-window valid event 1
        {
            "timestamp": datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {
                "eventId": event_id_shared,
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "unit_cost": 50.0,
                "quantity": 10,
                "currency": "EUR",
            },
        },
        # Duplicate of event 1 (retransmitted due to client network retry)
        {
            "timestamp": datetime(2026, 11, 16, 10, 1, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {
                "eventId": event_id_shared,  # Identical eventId
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "unit_cost": 50.0,
                "quantity": 10,
                "currency": "EUR",
            },
        },
        # In-window valid event 2 (different type)
        {
            "timestamp": datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "outbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {
                "eventId": str(uuid4()),
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "quantity": 5,
                "currency": "EUR",
            },
        },
        # In-window but technical event (must be ignored by business pipeline)
        {
            "timestamp": datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "api_request_failed",
            "level": "error",
            "value": 500,
            "message": None,
            "tags": {"eventId": str(uuid4()), "route": "/inventory"},
        },
        # Out-of-window event (too early)
        {
            "timestamp": datetime(2026, 11, 15, 23, 59, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {
                "eventId": str(uuid4()),
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "unit_cost": 10.0,
                "quantity": 1,
            },
        },
        # Out-of-window event (too late)
        {
            "timestamp": datetime(2026, 11, 23, 0, 1, tzinfo=timezone.utc),
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": None,
            "message": None,
            "tags": {
                "eventId": str(uuid4()),
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "unit_cost": 20.0,
                "quantity": 2,
            },
        },
    ]

    stored = store_telemetry_events(raw_batch, engine=telemetry_test_engine)
    assert stored == 6

    extracted = extract_telemetry_records(
        window_start=window_start,
        window_end=window_end,
        engine=telemetry_test_engine,
    )

    # Must extract only in-window business events and deduplicate event_id_shared
    assert len(extracted) == 2
    types = {e["event_type"] for e in extracted}
    assert types == {"inbound_order_created", "outbound_order_created"}
    assert {e["dedup_key"] for e in extracted} != {event_id_shared}  # Contains both distinct keys


def test_transform_events_aggregates_kpis_accurately():
    """Verify transformation calculates all 4 KPIs, segregates currencies, and groups by grain."""
    window_start = date(2026, 11, 16)

    raw_events = [
        # Valencia - Programme A: Inbound with total_cost specified
        {
            "dedup_key": "v1",
            "event_type": "inbound_order_created",
            "tags": {
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "total_cost": 1250.75,
                "unit_cost": 100.0,
                "quantity": 12,
                "currency": "EUR",
            },
        },
        # Valencia - Programme A: Inbound with unit_cost * quantity fallback
        {
            "dedup_key": "v2",
            "event_type": "inbound_order_created",
            "tags": {
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "unit_cost": 40.0,
                "quantity": 5,
                "currency": "EUR",
            },
        },
        # Valencia - Programme A: 2 kits delivered
        {
            "dedup_key": "v3",
            "event_type": "outbound_order_created",
            "tags": {
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "currency": "EUR",
            },
        },
        {
            "dedup_key": "v4",
            "event_type": "outbound_order_created",
            "tags": {
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "currency": "EUR",
            },
        },
        # Valencia - Programme A: 1 shortage event
        {
            "dedup_key": "v5",
            "event_type": "stock_threshold_triggered",
            "tags": {
                "office": "valencia",
                "programme_id": "ai-engineering-core",
                "currency": "EUR",
            },
        },
        # Miami - Programme B: Cost variance detected
        {
            "dedup_key": "m1",
            "event_type": "kit_cost_variance_detected",
            "tags": {
                "office": "miami",
                "programme_id": "data-eng-q4",
                "currency": "USD",
            },
        },
        # Miami - Programme B: Inbound order
        {
            "dedup_key": "m2",
            "event_type": "inbound_order_created",
            "tags": {
                "office": "miami",
                "programme_id": "data-eng-q4",
                "unit_cost": 300.0,
                "quantity": 2,
                "currency": "USD",
            },
        },
    ]

    aggregates = transform_events_to_weekly_kpis(raw_events, window_start=window_start)
    assert len(aggregates) == 2

    valencia_row = next(r for r in aggregates if r["office"] == "valencia")
    assert valencia_row["programme_id"] == "ai-engineering-core"
    assert valencia_row["currency"] == "EUR"
    # 1250.75 + (40 * 5) = 1450.75
    assert valencia_row["total_material_cost"] == 1450.75
    assert valencia_row["kits_delivered_count"] == 2
    assert valencia_row["shortage_events_count"] == 1
    assert valencia_row["cost_variance_events_count"] == 0

    miami_row = next(r for r in aggregates if r["office"] == "miami")
    assert miami_row["programme_id"] == "data-eng-q4"
    assert miami_row["currency"] == "USD"
    assert miami_row["total_material_cost"] == 600.0
    assert miami_row["kits_delivered_count"] == 0
    assert miami_row["shortage_events_count"] == 0
    assert miami_row["cost_variance_events_count"] == 1


def test_cache_key_fn_is_deterministic_and_sensitive_to_changes():
    """Verify compute_transform_cache_key responds deterministically to data modifications."""
    params1 = {
        "window_start": date(2026, 11, 16),
        "raw_events": [
            {"id": "e1", "event_type": "inbound_order_created", "timestamp": "2026-11-16T10:00:00Z", "tags": {"cost": 100}},
        ],
    }
    key1a = compute_transform_cache_key(None, params1)
    key1b = compute_transform_cache_key(None, params1)
    assert key1a == key1b

    # Changing window_start changes key
    params_diff_window = {
        "window_start": date(2026, 11, 23),
        "raw_events": params1["raw_events"],
    }
    assert compute_transform_cache_key(None, params_diff_window) != key1a

    # Changing tag payload changes key
    params_diff_data = {
        "window_start": date(2026, 11, 16),
        "raw_events": [
            {"id": "e1", "event_type": "inbound_order_created", "timestamp": "2026-11-16T10:00:00Z", "tags": {"cost": 200}},
        ],
    }
    assert compute_transform_cache_key(None, params_diff_data) != key1a


def test_prefect_tasks_execute_in_flow(telemetry_test_engine):
    """Verify Prefect tasks run end-to-end within a Prefect flow."""
    window_start = date(2026, 11, 16)
    window_end = date(2026, 11, 23)

    store_telemetry_events(
        [
            {
                "timestamp": datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
                "service": "backoffice",
                "event_type": "outbound_order_created",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {
                    "eventId": "test-flow-uuid",
                    "office": "miami",
                    "programme_id": "ai-core",
                    "currency": "USD",
                },
            }
        ],
        engine=telemetry_test_engine,
    )

    @flow(name="test-subflow-tasks")
    def run_subflow():
        raw = extract_telemetry_events(window_start, window_end, engine=telemetry_test_engine)
        transformed = transform_weekly_kpis(raw, window_start)
        return transformed

    result = run_subflow()
    assert len(result) == 1
    assert result[0]["office"] == "miami"
    assert result[0]["kits_delivered_count"] == 1
