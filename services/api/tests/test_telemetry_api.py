"""Synthetic, isolated checks for the temporary telemetry receiver."""

import copy
import logging
import secrets
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.telemetry import EVENT_DEFINITIONS, load_telemetry_endpoint


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.delenv("TELEMETRY_ENDPOINT", raising=False)
    # The receiver has no database dependency; never initialize a local database.
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


def test_valid_batch_and_metadata_only_logging(client, caplog):
    events = [
        event(),
        event("backoffice_section_viewed", {"office": "valencia", "section_id": "inventory"}),
    ]
    with caplog.at_level(logging.INFO, logger="services.api.routers.telemetry"):
        response = client.post("/telemetry/events", json={"events": events})
    assert response.status_code == 200
    assert response.json() == {"received": 2}
    messages = [record.getMessage() for record in caplog.records
                if record.name == "services.api.routers.telemetry"]
    assert messages == [
        "Telemetry received: count=2 event_types=['auth_login_succeeded', 'backoffice_section_viewed']"
    ]
    assert events[0]["eventId"] not in messages[0]
    assert events[0]["requestId"] not in messages[0]
    assert app.state.telemetry_endpoint is None


def test_empty_batch_is_accepted(client):
    response = client.post("/telemetry/events", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"received": 0}


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
def test_invalid_event_rejects_whole_batch_without_echo(client, caplog, change):
    invalid = event()
    invalid.update(change)
    with caplog.at_level(logging.INFO, logger="services.api.routers.telemetry"):
        response = client.post("/telemetry/events", json={"events": [event(), invalid]})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid telemetry batch"}
    assert not [record for record in caplog.records
                if record.name == "services.api.routers.telemetry"]


@pytest.mark.parametrize("field", [
    "eventId", "timestamp", "sessionId", "userId", "event_type",
    "schemaVersion", "requestId", "properties",
])
def test_all_envelope_fields_are_required(client, field):
    payload = event()
    del payload[field]
    assert client.post("/telemetry/events", json={"events": [payload]}).status_code == 422


def test_batch_shape_malformed_json_and_limit(client):
    for payload in ({}, {"events": None}, {"events": {}}, {"events": [], "extra": True},
                    {"events": [event()] * 501}):
        response = client.post("/telemetry/events", json=payload)
        assert response.status_code == 422
        assert response.json() == {"detail": "Invalid telemetry batch"}
    malformed = client.post("/telemetry/events", content='{"email": "synthetic-private",')
    assert malformed.status_code == 422
    assert malformed.json() == {"detail": "Invalid telemetry batch"}
    assert client.post("/telemetry/events", json={"events": [event()] * 500}).status_code == 200


def test_catalogue_allowlists_and_property_constraints(client):
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
        for name in properties:
            invalid = copy.deepcopy(payload)
            invalid["properties"][name] = {"unexpected": True}
            assert client.post("/telemetry/events", json={"events": [invalid]}).status_code == 422


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
    assert response.status_code == 422


def test_nullable_optional_array_and_currency_constraints(client):
    properties = {"office": "miami", "currency": "USD", "result_count": 0,
                  "programme_id": None, "product_category": None,
                  "filters_used": ["availability"]}
    payload = event("inventory_search_performed", properties)
    assert client.post("/telemetry/events", json={"events": [payload]}).status_code == 200
    for change in ({"currency": "EUR"}, {"filters_used": ["raw-search"]},
                   {"result_count": False}, {"result_count": -1}):
        invalid = copy.deepcopy(payload)
        invalid["properties"].update(change)
        assert client.post("/telemetry/events", json={"events": [invalid]}).status_code == 422


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
