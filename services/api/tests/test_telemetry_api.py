"""Synthetic, isolated checks for the telemetry receiver and partial batch storage."""

import copy
import logging
import secrets
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from services.api.main import app
from services.api.telemetry import EVENT_DEFINITIONS, load_telemetry_endpoint
from services.api.telemetry_storage import (
    TelemetryStorageError,
    init_telemetry_db,
    set_telemetry_engine,
    telemetry_events_table,
)


@pytest.fixture
def telemetry_engine():
    from sqlalchemy.pool import StaticPool

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
def client(monkeypatch, telemetry_engine):
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.delenv("TELEMETRY_ENDPOINT", raising=False)
    monkeypatch.setattr("services.api.main.init_db", lambda: None)
    with TestClient(app) as test_client:
        yield test_client


def event(event_type="auth_login_succeeded", properties=None):
    return {
        "eventId": str(uuid4()),
        "timestamp": "2026-11-13T20:00:00Z",
        "sessionId": None,
        "userId": None,
        "event_type": event_type,
        "schemaVersion": "1.0",
        "requestId": "synthetic-request",
        "properties": {"auth_method": "password"} if properties is None else properties,
    }


def test_valid_batch_persists_and_logs_metadata_only(client, telemetry_engine, caplog):
    events = [
        event(),
        event("backoffice_section_viewed", {"office": "valencia", "section_id": "inventory"}),
    ]
    with caplog.at_level(logging.INFO, logger="services.api.routers.telemetry"):
        response = client.post("/telemetry/events", json={"events": events})

    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 2, "rejected": 0}

    # Verify rows persisted in DB
    with telemetry_engine.connect() as conn:
        rows = conn.execute(select(telemetry_events_table)).fetchall()
        assert len(rows) == 2
        assert {r.event_type for r in rows} == {"auth_login_succeeded", "backoffice_section_viewed"}

    # Verify logs do not leak sensitive IDs or payloads
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "services.api.routers.telemetry"
    ]
    assert len(messages) == 1
    assert "received=2 stored=2 rejected=0" in messages[0]
    assert "event_types=['auth_login_succeeded', 'backoffice_section_viewed']" in messages[0]
    assert events[0]["eventId"] not in messages[0]
    assert events[0]["requestId"] not in messages[0]


def test_empty_batch_is_accepted_without_db_calls(client, caplog):
    with caplog.at_level(logging.INFO, logger="services.api.routers.telemetry"):
        response = client.post("/telemetry/events", json={"events": []})

    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "services.api.routers.telemetry"
    ]
    assert "received=0 stored=0 rejected=0 event_types=[]" in messages[0]


def test_mixed_batch_partial_acceptance(client, telemetry_engine):
    valid_event = event("inbound_order_created", {
        "office": "valencia",
        "product_id": "prod-1",
        "product_category": "training_kit",
        "programme_id": "prog-1",
        "quantity": 10,
        "currency": "EUR",
        "unit_cost": 25.0,
        "supplier_ref": "sup-1",
    })
    invalid_event = {
        "eventId": "not-a-uuid",
        "timestamp": "invalid",
        "event_type": "unknown_event",
    }
    non_dict_event = "not-a-dict"

    response = client.post(
        "/telemetry/events",
        json={"events": [valid_event, invalid_event, non_dict_event]},
    )

    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 2}

    # Only valid event must be persisted in database
    with telemetry_engine.connect() as conn:
        rows = conn.execute(select(telemetry_events_table)).fetchall()
        assert len(rows) == 1
        assert rows[0].event_type == "inbound_order_created"
        assert rows[0].tags["product_id"] == "prod-1"


@pytest.mark.parametrize("change", [
    {"eventId": "not-a-uuid"},
    {"timestamp": "2026-11-13T20:00:00"},
    {"timestamp": "1730000000"},
    {"timestamp": "2026-02-30T20:00:00Z"},
    {"sessionId": 123},
    {"userId": False},
    {"schemaVersion": "2.0"},
    {"requestId": ""},
    {"event_type": "unknown"},
    {"email": "synthetic-private@example.invalid"},
    {"properties": {"auth_method": "password", "email": "synthetic-private@example.invalid"}},
    {"properties": {"auth_method": "invalid"}},
    {"properties": {}},
    {"properties": None},
])
def test_invalid_event_rejects_individually_without_echo(client, telemetry_engine, caplog, change):
    valid = event()
    invalid = event()
    invalid.update(change)

    with caplog.at_level(logging.INFO, logger="services.api.routers.telemetry"):
        response = client.post("/telemetry/events", json={"events": [valid, invalid]})

    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 1}

    # Only 1 valid event stored
    with telemetry_engine.connect() as conn:
        rows = conn.execute(select(telemetry_events_table)).fetchall()
        assert len(rows) == 1

    # Verify no input echoes in logs
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "services.api.routers.telemetry"
    ]
    assert len(messages) == 1
    assert "event_types=['auth_login_succeeded']" in messages[0]
    assert "synthetic-private" not in messages[0]


@pytest.mark.parametrize("field", [
    "eventId", "timestamp", "sessionId", "userId", "event_type",
    "schemaVersion", "requestId", "properties",
])
def test_all_envelope_fields_are_required_for_valid_event(client, field):
    payload = event()
    del payload[field]
    response = client.post("/telemetry/events", json={"events": [payload]})
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}


def test_batch_shape_malformed_json_and_limit(client):
    for payload in ({}, {"events": None}, {"events": {}}, {"events": [], "extra": True},
                    {"events": [event()] * 501}):
        response = client.post("/telemetry/events", json=payload)
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid telemetry batch"}

    malformed = client.post("/telemetry/events", content='{"email": "synthetic-private",')
    assert malformed.status_code == 422
    assert malformed.json() == {"detail": "Invalid telemetry batch"}

    # 500 items max limit accepted
    assert client.post("/telemetry/events", json={"events": [event()] * 500}).status_code == 200


def test_catalogue_allowlists_and_property_constraints(client, telemetry_engine):
    for definition in EVENT_DEFINITIONS.values():
        properties = {}
        for name, rule in definition.properties.items():
            kinds = rule.type if isinstance(rule.type, list) else [rule.type]
            if rule.enum is not None:
                value = next(value for value in rule.enum if value is not None)
            elif rule.format == "uuid":
                value = str(uuid4())
            elif "string" in kinds:
                value = "synthetic-reference"
            elif "integer" in kinds:
                value = int(rule.minimum if rule.minimum is not None else 1)
            elif "number" in kinds:
                value = rule.minimum if rule.minimum is not None else 1
            else:
                value = []
            properties[name] = value

        payload = event(definition.event_type, properties)
        response = client.post("/telemetry/events", json={"events": [payload]})
        assert response.status_code == 200, definition.event_type
        assert response.json() == {"received": 1, "stored": 1, "rejected": 0}

        for name in properties:
            invalid = copy.deepcopy(payload)
            invalid["properties"][name] = {"unexpected": True}
            res = client.post("/telemetry/events", json={"events": [invalid]})
            assert res.status_code == 200
            assert res.json() == {"received": 1, "stored": 0, "rejected": 1}


@pytest.mark.parametrize("properties", [
    {"status_code": 99},
    {"status_code": 600},
    {"duration_ms": -1},
    {"sample_rate": 0},
    {"duration_ms": True},
    {"http_method": "TRACE"},
])
def test_numeric_and_enum_constraints(client, properties):
    valid = {"route_group": "auth", "http_method": "GET", "status_code": None,
             "duration_ms": 10, "sample_rate": 1}
    valid.update(properties)
    response = client.post("/telemetry/events", json={"events": [event("api_latency_recorded", valid)]})
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}


def test_nullable_optional_array_and_currency_constraints(client):
    properties = {"office": "miami", "currency": "USD", "result_count": 0,
                  "programme_id": None, "product_category": None,
                  "filters_used": ["availability"]}
    payload = event("inventory_search_performed", properties)
    res = client.post("/telemetry/events", json={"events": [payload]})
    assert res.status_code == 200
    assert res.json() == {"received": 1, "stored": 1, "rejected": 0}

    for change in ({"currency": "EUR"}, {"filters_used": ["raw-search"]},
                   {"result_count": False}, {"result_count": -1}):
        invalid = copy.deepcopy(payload)
        invalid["properties"].update(change)
        res_invalid = client.post("/telemetry/events", json={"events": [invalid]})
        assert res_invalid.status_code == 200
        assert res_invalid.json() == {"received": 1, "stored": 0, "rejected": 1}


def test_database_failure_returns_503_and_rolls_back(client):
    with patch(
        "services.api.routers.telemetry.store_telemetry_events",
        side_effect=TelemetryStorageError("DB error"),
    ):
        response = client.post("/telemetry/events", json={"events": [event()]})
        assert response.status_code == 503
        assert response.json() == {"detail": "Telemetry storage unavailable"}


def test_endpoint_configuration_is_loaded_at_startup(client, monkeypatch):
    monkeypatch.setenv("TELEMETRY_ENDPOINT", "http://127.0.0.1:8000/telemetry/events")
    with TestClient(app):
        assert app.state.telemetry_endpoint == "http://127.0.0.1:8000/telemetry/events"
    assert app.state.telemetry_endpoint is None
    monkeypatch.setenv("TELEMETRY_ENDPOINT", "")
    assert load_telemetry_endpoint() is None


@pytest.mark.parametrize("value", [
    "not-a-url", "ftp://localhost/events", "https://user:password@localhost/events",
    "https://localhost/events?token=synthetic-private", "https://localhost/events#fragment",
])
def test_invalid_endpoint_configuration_fails_safely(client, monkeypatch, value):
    monkeypatch.setenv("TELEMETRY_ENDPOINT", value)
    with pytest.raises(RuntimeError, match="TELEMETRY_ENDPOINT") as error:
        with TestClient(app):
            pass
    assert value not in str(error.value)
