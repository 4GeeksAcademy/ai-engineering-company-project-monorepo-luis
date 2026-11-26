"""Integration tests for the reporting API endpoints in services/reporting/ (Etapa 4)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
from services.api.main import app
from services.api.telemetry_storage import (
    init_telemetry_db,
    set_telemetry_engine,
    store_telemetry_events,
)


@pytest.fixture
def test_environment(monkeypatch):
    """Set up isolated in-memory test environment for telemetry and reporting."""
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

    monkeypatch.setenv("JWT_SECRET_KEY", "synthetic_jwt_secret_key_at_least_32_bytes_long_12345")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setattr("services.api.main.init_db", lambda: None)

    yield tel_engine, rep_engine

    set_telemetry_engine(None)
    set_reporting_engine(None)


@pytest.fixture
def client(test_environment):
    """TestClient wired to isolated in-memory DBs."""
    with TestClient(app) as test_client:
        yield test_client


def test_get_latest_pipeline_run_404_when_empty(client):
    """GET /reporting/pipeline-runs/latest returns 404 when no runs exist."""
    response = client.get("/reporting/pipeline-runs/latest")
    assert response.status_code == 404
    assert response.json()["detail"] == "No pipeline runs recorded"


def test_get_latest_pipeline_run_success(client, test_environment):
    """GET /reporting/pipeline-runs/latest returns metadata of the last run."""
    _, rep_engine = test_environment
    run_id = uuid4()
    started = datetime(2026, 11, 23, 5, 0, 0, tzinfo=timezone.utc)
    finished = datetime(2026, 11, 23, 5, 1, 30, tzinfo=timezone.utc)

    with rep_engine.begin() as conn:
        conn.execute(
            pipeline_execution_logs_table.insert().values(
                run_id=run_id,
                flow_name="weekly_business_performance_pipeline",
                trigger_mode="scheduled",
                window_start=date(2026, 11, 16),
                window_end=date(2026, 11, 23),
                started_at=started,
                finished_at=finished,
                status="COMPLETED",
                checkpoint_phase="FINALIZED",
                records_extracted=150,
                records_loaded=4,
                error_details=None,
                execution_context={},
            )
        )

    response = client.get("/reporting/pipeline-runs/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == str(run_id)
    assert data["status"] == "COMPLETED"
    assert data["records_extracted"] == 150
    assert data["records_loaded"] == 4
    assert data["duration_seconds"] == 90.0

    # Test alias route /reporting/status
    alias_resp = client.get("/reporting/status")
    assert alias_resp.status_code == 200
    assert alias_resp.json()["run_id"] == str(run_id)


def test_trigger_pipeline_run_endpoint(client, test_environment):
    """POST /reporting/pipeline-runs triggers execution and returns run_id."""
    tel_engine, _ = test_environment

    # Seed an event
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
                    "eventId": "evt-post-1",
                    "office": "valencia",
                    "programme_id": "b2b-sales",
                    "total_cost": 850.0,
                    "currency": "EUR",
                },
            }
        ],
        engine=tel_engine,
    )

    response = client.post(
        "/reporting/pipeline-runs",
        json={"target_week_start": "2026-11-16", "reprocess_buffer_week": False},
    )
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "COMPLETED"
    assert data["target_week_start"] == "2026-11-16"


def test_weekly_performance_kpis_endpoint_contract(client, test_environment):
    """GET /reporting/weekly-office-program-performance matches exact Nexova contract."""
    _, rep_engine = test_environment
    test_week = date(2026, 7, 13)
    run_id = uuid4()

    with rep_engine.begin() as conn:
        conn.execute(
            weekly_office_program_performance_table.insert().values(
                office="valencia",
                programme_id="b2b-sales",
                week_start=test_week,
                total_material_cost=1240.50,
                kits_delivered_count=18,
                shortage_events_count=1,
                cost_variance_events_count=0,
                currency="EUR",
                computed_at=datetime.now(timezone.utc),
                run_id=run_id,
            )
        )
        conn.execute(
            weekly_office_program_performance_table.insert().values(
                office="miami",
                programme_id="ai-core",
                week_start=test_week,
                total_material_cost=3100.00,
                kits_delivered_count=25,
                shortage_events_count=0,
                cost_variance_events_count=2,
                currency="USD",
                computed_at=datetime.now(timezone.utc),
                run_id=run_id,
            )
        )

    # 1. Query with specific week_start
    response = client.get("/reporting/weekly-office-program-performance?week_start=2026-07-13")
    assert response.status_code == 200
    data = response.json()
    assert data["week_start"] == "2026-07-13"
    assert len(data["entries"]) == 2

    valencia = next(e for e in data["entries"] if e["office"] == "valencia")
    assert valencia["programme_id"] == "b2b-sales"
    assert valencia["total_material_cost"] == 1240.50
    assert valencia["kits_delivered_count"] == 18
    assert valencia["shortage_events_count"] == 1
    assert valencia["cost_variance_events_count"] == 0
    assert valencia["currency"] == "EUR"

    miami = next(e for e in data["entries"] if e["office"] == "miami")
    assert miami["programme_id"] == "ai-core"
    assert miami["currency"] == "USD"
    assert miami["cost_variance_events_count"] == 2

    # 2. Query without week_start defaults to latest computed week
    default_resp = client.get("/reporting/weekly-office-program-performance")
    assert default_resp.status_code == 200
    assert default_resp.json()["week_start"] == "2026-07-13"
    assert len(default_resp.json()["entries"]) == 2

    # 3. Query with invalid date format returns 400
    bad_resp = client.get("/reporting/weekly-office-program-performance?week_start=invalid-date")
    assert bad_resp.status_code == 400
    assert "Invalid week_start format" in bad_resp.json()["detail"]

    # 4. Filter by office
    office_resp = client.get("/reporting/weekly-office-program-performance?office=valencia")
    assert office_resp.status_code == 200
    assert len(office_resp.json()["entries"]) == 1
    assert office_resp.json()["entries"][0]["office"] == "valencia"
