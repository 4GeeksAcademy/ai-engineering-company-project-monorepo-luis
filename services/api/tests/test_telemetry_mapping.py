"""Unit tests for telemetry event mapping to database row format."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.api.telemetry import (
    DEFAULT_SERVICE,
    EVENT_SEVERITY_LEVELS,
    TelemetryEvent,
    get_event_level,
    get_event_value,
    map_event_to_row,
)


def make_event(event_type: str, properties: dict, timestamp: str = "2026-11-18T19:00:00Z") -> TelemetryEvent:
    return TelemetryEvent(
        eventId=str(uuid4()),
        timestamp=timestamp,
        sessionId=None,
        userId=None,
        event_type=event_type,
        schemaVersion="1.0",
        requestId="req-test-123",
        properties=properties,
    )


def test_map_event_to_row_structure_and_defaults():
    event = make_event(
        "backoffice_section_viewed",
        {"office": "valencia", "section_id": "inventory"},
        timestamp="2026-11-18T20:15:30+01:00",
    )
    row = map_event_to_row(event)

    assert set(row.keys()) == {"timestamp", "service", "event_type", "level", "value", "message", "tags"}
    assert row["service"] == DEFAULT_SERVICE
    assert row["event_type"] == "backoffice_section_viewed"
    assert row["level"] == "info"
    assert row["value"] is None
    assert row["message"] is None
    assert row["tags"] == {"office": "valencia", "section_id": "inventory"}

    # Assert UTC conversion
    assert isinstance(row["timestamp"], datetime)
    assert row["timestamp"].tzinfo == timezone.utc
    assert row["timestamp"].hour == 19
    assert row["timestamp"].minute == 15
    assert row["timestamp"].second == 30


@pytest.mark.parametrize(
    "event_type,expected_level",
    [
        ("api_request_failed", "error"),
        ("frontend_uncaught_error", "error"),
        ("auth_login_failed", "error"),
        ("direct_stock_edit_rejected", "error"),
        ("inventory_order_validation_failed", "error"),
        ("stock_threshold_triggered", "warn"),
        ("kit_cost_variance_detected", "warn"),
        ("auth_session_expired", "warn"),
        ("inventory_order_abandoned", "warn"),
        ("backoffice_flow_abandoned", "warn"),
        ("inbound_order_created", "info"),
        ("outbound_order_created", "info"),
        ("auth_login_succeeded", "info"),
        ("inventory_item_viewed", "info"),
        ("page_load_recorded", "info"),
    ],
)
def test_severity_level_mapping(event_type, expected_level):
    assert get_event_level(event_type) == expected_level


def test_value_extraction_for_performance_metrics():
    latency_event = make_event(
        "api_latency_recorded",
        {
            "route_group": "inventory_read",
            "http_method": "GET",
            "status_code": 200,
            "duration_ms": 142.5,
            "sample_rate": 1.0,
        },
    )
    assert get_event_value(latency_event) == 142.5
    row = map_event_to_row(latency_event)
    assert row["value"] == 142.5

    page_event = make_event(
        "page_load_recorded",
        {
            "page_id": "inventory",
            "duration_ms": 350,
            "navigation_type": "navigate",
        },
    )
    assert get_event_value(page_event) == 350
    assert map_event_to_row(page_event)["value"] == 350


def test_value_is_none_for_business_events_to_avoid_unlabeled_metric_mixing():
    inbound_event = make_event(
        "inbound_order_created",
        {
            "office": "valencia",
            "product_id": "prod-1",
            "product_category": "training_kit",
            "programme_id": "prog-1",
            "quantity": 10,
            "currency": "EUR",
            "unit_cost": 25.5,
            "supplier_ref": "sup-1",
        },
    )
    row = map_event_to_row(inbound_event)
    assert row["value"] is None
    # Details remain preserved in tags
    assert row["tags"]["quantity"] == 10
    assert row["tags"]["unit_cost"] == 25.5
