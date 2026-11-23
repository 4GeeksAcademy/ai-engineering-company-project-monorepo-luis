"""Unit and integration tests for telemetry reporting pipeline and GET /telemetry/report endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.main import app
from services.api.response_cache import response_cache
from services.api.telemetry_storage import (
    init_telemetry_db,
    set_telemetry_engine,
    store_telemetry_events,
)
from services.telemetry.analysis import (
    build_telemetry_report,
    get_auth_failure_rate,
    get_error_rate_by_type,
    get_events_per_day,
    get_latency_by_route_group,
    validate_report_dates,
)


@pytest.fixture
def test_engine():
    """Isolated in-memory SQLite engine for reporting tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_telemetry_db(engine)
    set_telemetry_engine(engine)
    yield engine
    set_telemetry_engine(None)


@pytest.fixture
def test_client(test_engine, monkeypatch):
    """TestClient wired to isolated in-memory DB and cache clearing."""
    response_cache.clear()
    monkeypatch.setenv("JWT_SECRET_KEY", "synthetic_jwt_secret_key_at_least_32_bytes_long_12345")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.delenv("TELEMETRY_ENDPOINT", raising=False)
    monkeypatch.setattr("services.api.main.init_db", lambda: None)
    with TestClient(app) as client:
        yield client
    response_cache.clear()


def make_row(
    timestamp: datetime,
    event_type: str = "api_latency_recorded",
    level: str = "info",
    value: float | None = None,
    tags: dict | None = None,
) -> dict:
    if timestamp.tzinfo is not None:
        ts_utc = timestamp.astimezone(timezone.utc)
    else:
        ts_utc = timestamp
    return {
        "timestamp": ts_utc,
        "service": "backoffice",
        "event_type": event_type,
        "level": level,
        "value": value,
        "message": None,
        "tags": tags or {},
    }


# =====================================================================
# Unit Tests: Date Validation
# =====================================================================

def test_validate_report_dates_success():
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)
    s_utc, e_utc = validate_report_dates(start, end)
    assert s_utc == start
    assert e_utc == end


def test_validate_report_dates_non_utc_conversion():
    # +02:00 timezone -> normalized to UTC
    tz_plus_2 = timezone(timedelta(hours=2))
    start = datetime(2026, 11, 1, 2, 0, tzinfo=tz_plus_2)  # equals 00:00 UTC
    end = datetime(2026, 11, 8, 2, 0, tzinfo=tz_plus_2)    # equals 00:00 UTC
    s_utc, e_utc = validate_report_dates(start, end)
    assert s_utc == datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    assert e_utc == datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)


def test_validate_report_dates_rejects_naive():
    naive = datetime(2026, 11, 1, 0, 0)
    aware = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_report_dates(naive, aware)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_report_dates(aware, naive)


def test_validate_report_dates_rejects_inverted_or_equal():
    d1 = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)
    d2 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="strictly before"):
        validate_report_dates(d1, d2)
    with pytest.raises(ValueError, match="strictly before"):
        validate_report_dates(d1, d1)


# =====================================================================
# Unit Tests: Metric 1 (events_per_day)
# =====================================================================

def test_events_per_day_boundaries_and_midnight(test_engine):
    start = datetime(2026, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 12, 0, 0, 0, tzinfo=timezone.utc)

    rows = [
        # Exactly on start_date (inclusive -> should be included)
        make_row(start, event_type="inventory_item_viewed"),
        # Just before midnight Day 1
        make_row(datetime(2026, 11, 10, 23, 59, 59, tzinfo=timezone.utc), event_type="inventory_item_viewed"),
        # Exactly midnight Day 2
        make_row(datetime(2026, 11, 11, 0, 0, 0, tzinfo=timezone.utc), event_type="auth_login_succeeded"),
        # Non-UTC timezone that lands in Day 2 in UTC (01:00 UTC+2 is 23:00 UTC Day 1!)
        make_row(
            datetime(2026, 11, 11, 1, 0, 0, tzinfo=timezone(timedelta(hours=2))),
            event_type="inventory_item_viewed",
        ),
        # Exactly on end_date (exclusive -> should NOT be included)
        make_row(end, event_type="inventory_item_viewed"),
        # After end_date -> excluded
        make_row(datetime(2026, 11, 15, 0, 0, 0, tzinfo=timezone.utc), event_type="inventory_item_viewed"),
    ]
    store_telemetry_events(rows, engine=test_engine)

    result = get_events_per_day(start, end, engine=test_engine)

    # In 2026-11-10: 3 inventory_item_viewed (start + 23:59:59 + non-UTC 23:00)
    # In 2026-11-11: 1 auth_login_succeeded
    day10 = [r for r in result if r["date"] == "2026-11-10"]
    day11 = [r for r in result if r["date"] == "2026-11-11"]
    day12 = [r for r in result if r["date"] == "2026-11-12"]

    assert len(day10) == 1
    assert day10[0]["event_type"] == "inventory_item_viewed"
    assert day10[0]["count"] == 3

    assert len(day11) == 1
    assert day11[0]["event_type"] == "auth_login_succeeded"
    assert day11[0]["count"] == 1

    assert len(day12) == 0  # Exclusive boundary respected


def test_events_per_day_empty(test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    result = get_events_per_day(start, end, engine=test_engine)
    assert result == []


# =====================================================================
# Unit Tests: Metric 2 (error_rate_by_type)
# =====================================================================

def test_error_rate_by_type(test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)

    rows = [
        # api_request_failed: 2 errors out of 2
        make_row(start + timedelta(hours=1), event_type="api_request_failed", level="error"),
        make_row(start + timedelta(hours=2), event_type="api_request_failed", level="error"),
        # auth_login_failed: 1 error out of 1
        make_row(start + timedelta(hours=3), event_type="auth_login_failed", level="error"),
        # api_latency_recorded: 0 errors out of 3
        make_row(start + timedelta(hours=4), event_type="api_latency_recorded", level="info", value=50.0),
        make_row(start + timedelta(hours=5), event_type="api_latency_recorded", level="info", value=60.0),
        make_row(start + timedelta(hours=6), event_type="api_latency_recorded", level="info", value=70.0),
    ]
    store_telemetry_events(rows, engine=test_engine)

    result = get_error_rate_by_type(start, end, engine=test_engine)

    by_type = {r["event_type"]: r for r in result}
    assert by_type["api_request_failed"]["errors"] == 2
    assert by_type["api_request_failed"]["total"] == 2
    assert by_type["api_request_failed"]["rate"] == 1.0

    assert by_type["auth_login_failed"]["errors"] == 1
    assert by_type["auth_login_failed"]["total"] == 1
    assert by_type["auth_login_failed"]["rate"] == 1.0

    assert by_type["api_latency_recorded"]["errors"] == 0
    assert by_type["api_latency_recorded"]["total"] == 3
    assert by_type["api_latency_recorded"]["rate"] == 0.0


def test_error_rate_empty(test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    assert get_error_rate_by_type(start, end, engine=test_engine) == []


# =====================================================================
# Unit Tests: Metric 3 (latency_by_route_group)
# =====================================================================

def test_latency_by_route_group(test_engine):
    start = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)

    rows = [
        # Valid latency events for route_group "inventory_read"
        make_row(
            start + timedelta(hours=2),
            event_type="api_latency_recorded",
            value=100.0,
            tags={"route_group": "inventory_read"},
        ),
        make_row(
            start + timedelta(hours=4),
            event_type="api_latency_recorded",
            value=150.0,
            tags={"route_group": "inventory_read"},
        ),
        # Valid latency event for route_group "auth"
        make_row(
            start + timedelta(hours=6),
            event_type="api_latency_recorded",
            value=25.0,
            tags={"route_group": "auth"},
        ),
        # Invalid: missing route_group -> must be skipped
        make_row(
            start + timedelta(hours=8),
            event_type="api_latency_recorded",
            value=200.0,
            tags={"route_group": None},
        ),
        # Invalid: missing duration_ms / value -> must be skipped
        make_row(
            start + timedelta(hours=10),
            event_type="api_latency_recorded",
            value=None,
            tags={"route_group": "inventory_read"},
        ),
        # Unrelated event type -> must NOT be included even with duration
        make_row(
            start + timedelta(hours=12),
            event_type="page_load_recorded",
            value=300.0,
            tags={"route_group": "inventory_read"},
        ),
    ]
    store_telemetry_events(rows, engine=test_engine)

    result = get_latency_by_route_group(start, end, engine=test_engine)

    assert len(result) == 2
    r_map = {r["route_group"]: r for r in result}
    assert r_map["inventory_read"]["mean_duration_ms"] == 125.0
    assert r_map["inventory_read"]["date"] == "2026-11-10"
    assert r_map["auth"]["mean_duration_ms"] == 25.0
    assert r_map["auth"]["date"] == "2026-11-10"


def test_latency_empty_and_null_tags(test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    assert get_latency_by_route_group(start, end, engine=test_engine) == []


# =====================================================================
# Unit Tests: Metric 4 (auth_failure_rate)
# =====================================================================

def test_auth_failure_rate_calculation(test_engine):
    start = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 12, 0, 0, tzinfo=timezone.utc)

    rows = [
        # Day 1: 1 fail, 3 successes -> total=4, failure_rate=0.25
        make_row(start + timedelta(hours=2), event_type="auth_login_failed"),
        make_row(start + timedelta(hours=3), event_type="auth_login_succeeded"),
        make_row(start + timedelta(hours=4), event_type="auth_login_succeeded"),
        make_row(start + timedelta(hours=5), event_type="auth_login_succeeded"),
        # Day 2: 2 fails, 0 successes -> total=2, failure_rate=1.0
        make_row(start + timedelta(days=1, hours=2), event_type="auth_login_failed"),
        make_row(start + timedelta(days=1, hours=3), event_type="auth_login_failed"),
    ]
    store_telemetry_events(rows, engine=test_engine)

    result = get_auth_failure_rate(start, end, engine=test_engine)

    assert len(result) == 2
    day10 = [r for r in result if r["date"] == "2026-11-10"][0]
    day11 = [r for r in result if r["date"] == "2026-11-11"][0]

    assert day10["failures"] == 1
    assert day10["successes"] == 3
    assert day10["total"] == 4
    assert day10["failure_rate"] == 0.25

    assert day11["failures"] == 2
    assert day11["successes"] == 0
    assert day11["total"] == 2
    assert day11["failure_rate"] == 1.0


def test_auth_failure_rate_empty(test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    assert get_auth_failure_rate(start, end, engine=test_engine) == []


# =====================================================================
# Unit Tests: build_telemetry_report
# =====================================================================

def test_build_telemetry_report_serializability(test_engine):
    start = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)

    report = build_telemetry_report(start, end, engine=test_engine)
    # Must be valid json without NaN, Infinity or non-serializable objects
    serialized = json.dumps(report)
    assert "period" in serialized
    assert "metrics" in serialized
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


# =====================================================================
# Integration Tests: GET /telemetry/report
# =====================================================================

def test_get_report_defaults(test_client):
    response = test_client.get("/telemetry/report")
    assert response.status_code == 200
    data = response.json()
    assert "period" in data
    assert "from" in data["period"]
    assert "to" in data["period"]
    assert "metrics" in data
    assert "events_per_day" in data["metrics"]
    assert "error_rate_by_type" in data["metrics"]
    assert "latency_by_route_group" in data["metrics"]
    assert "auth_failure_rate" in data["metrics"]


def test_get_report_custom_dates(test_client, test_engine):
    start = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    store_telemetry_events(
        [make_row(start + timedelta(hours=1), event_type="inventory_item_viewed")],
        engine=test_engine,
    )

    response = test_client.get(
        "/telemetry/report",
        params={
            "start_date": "2026-11-01T00:00:00Z",
            "end_date": "2026-11-05T00:00:00Z",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"]["from"] == "2026-11-01T00:00:00Z"
    assert data["period"]["to"] == "2026-11-05T00:00:00Z"
    assert len(data["metrics"]["events_per_day"]) == 1
    assert data["metrics"]["events_per_day"][0]["event_type"] == "inventory_item_viewed"


def test_get_report_bad_requests(test_client):
    # Only start_date provided
    r1 = test_client.get("/telemetry/report?start_date=2026-11-01T00:00:00Z")
    assert r1.status_code == 400

    # Only end_date provided
    r2 = test_client.get("/telemetry/report?end_date=2026-11-05T00:00:00Z")
    assert r2.status_code == 400

    # Naive start_date
    r3 = test_client.get("/telemetry/report?start_date=2026-11-01T00:00:00&end_date=2026-11-05T00:00:00Z")
    assert r3.status_code == 400

    # Inverted range
    r4 = test_client.get("/telemetry/report?start_date=2026-11-10T00:00:00Z&end_date=2026-11-05T00:00:00Z")
    assert r4.status_code == 400

    # Malformed datetime
    r5 = test_client.get("/telemetry/report?start_date=not-a-date&end_date=2026-11-05T00:00:00Z")
    assert r5.status_code == 400


def test_get_report_cache_behavior(test_client, test_engine):
    start = "2026-11-01T00:00:00Z"
    end = "2026-11-05T00:00:00Z"

    with patch("services.api.routers.telemetry.build_telemetry_report") as mock_build:
        mock_build.return_value = {
            "period": {"from": start, "to": end},
            "metrics": {
                "events_per_day": [],
                "error_rate_by_type": [],
                "latency_by_route_group": [],
                "auth_failure_rate": [],
            },
        }

        # 1st request -> Cache MISS, builds report
        r1 = test_client.get(f"/telemetry/report?start_date={start}&end_date={end}")
        assert r1.status_code == 200
        assert mock_build.call_count == 1

        # 2nd request with same parameters -> Cache HIT, factory not called again
        r2 = test_client.get(f"/telemetry/report?start_date={start}&end_date={end}")
        assert r2.status_code == 200
        assert mock_build.call_count == 1

        # Request with different parameters -> Cache MISS, invokes factory
        different_end = "2026-11-06T00:00:00Z"
        r3 = test_client.get(f"/telemetry/report?start_date={start}&end_date={different_end}")
        assert r3.status_code == 200
        assert mock_build.call_count == 2


def test_get_report_privacy_no_pii_leaks(test_client, test_engine):
    now = datetime.now(timezone.utc)
    # Insert event with sensitive tags that should NOT leak in report
    rows = [
        make_row(
            now - timedelta(days=1),
            event_type="api_request_failed",
            level="error",
            tags={
                "route_group": "inventory_read",
                "userId": "secret-user-123",
                "sessionId": "secret-session-456",
                "raw_query": "SELECT * FROM passwords",
            },
        )
    ]
    store_telemetry_events(rows, engine=test_engine)

    response = test_client.get("/telemetry/report")
    assert response.status_code == 200
    body_text = response.text

    assert "secret-user-123" not in body_text
    assert "secret-session-456" not in body_text
    assert "SELECT * FROM passwords" not in body_text
    assert "raw_query" not in body_text
