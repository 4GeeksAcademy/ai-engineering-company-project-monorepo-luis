"""Telemetry contracts backed by the approved custom event registry."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)


class PropertyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str | list[str]
    required: bool = False
    description: str = ""
    enum: list[JsonValue] | None = None
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = Field(default=None, alias="minLength")
    format: str | None = None
    items: PropertyDefinition | None = None


class EventDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    classification: str
    category: str
    description: str
    properties: dict[str, PropertyDefinition]


_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "docs" / "telemetry" / "event-schemas.json"
with _REGISTRY_PATH.open(encoding="utf-8") as registry_file:
    _registry = json.load(registry_file)
EVENT_DEFINITIONS = {
    event.event_type: event
    for event in TypeAdapter(list[EventDefinition]).validate_python(_registry["events"])
}


def _is_uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value.lower()
    except ValueError:
        return False


def _valid_property(value: JsonValue, definition: PropertyDefinition) -> bool:
    allowed_types = definition.type if isinstance(definition.type, list) else [definition.type]
    matches_type = (
        (value is None and "null" in allowed_types)
        or (isinstance(value, str) and "string" in allowed_types)
        or (type(value) is int and "integer" in allowed_types)
        or (type(value) in (int, float) and "number" in allowed_types)
        or (isinstance(value, list) and "array" in allowed_types)
    )
    if not matches_type or (definition.enum is not None and value not in definition.enum):
        return False
    if value is None:
        return True
    if isinstance(value, str):
        if definition.min_length is not None and len(value) < definition.min_length:
            return False
        if definition.format == "uuid" and not _is_uuid(value):
            return False
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        if definition.minimum is not None and value < definition.minimum:
            return False
        if definition.maximum is not None and value > definition.maximum:
            return False
    if isinstance(value, list) and definition.items is not None:
        return all(_valid_property(item, definition.items) for item in value)
    return True


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    eventId: str
    timestamp: str
    sessionId: str | None
    userId: str | None
    event_type: str
    schemaVersion: Literal["1.0"]
    requestId: str = Field(min_length=1)
    properties: dict[str, JsonValue]

    @field_validator("eventId")
    @classmethod
    def valid_event_id(cls, value: str) -> str:
        if not _is_uuid(value):
            raise ValueError("Invalid event identifier")
        return value

    @field_validator("timestamp")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})",
            value,
        ):
            raise ValueError("Invalid event timestamp")
        TypeAdapter(AwareDatetime).validate_python(value)
        return value

    @model_validator(mode="after")
    def valid_event_properties(self) -> TelemetryEvent:
        definition = EVENT_DEFINITIONS.get(self.event_type)
        if definition is None:
            raise ValueError("Unknown event type")
        if self.properties.keys() - definition.properties.keys():
            raise ValueError("Unknown event property")
        for name, rule in definition.properties.items():
            if name not in self.properties:
                if rule.required:
                    raise ValueError("Missing event property")
            elif not _valid_property(self.properties[name], rule):
                raise ValueError("Invalid event property")
        office = self.properties.get("office")
        currency = self.properties.get("currency")
        if currency is not None and office in ("valencia", "miami"):
            if currency != ("EUR" if office == "valencia" else "USD"):
                raise ValueError("Currency does not match office")
        return self


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    events: list[TelemetryEvent] = Field(max_length=500)


class TelemetryReceived(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    received: int = Field(ge=0)


def load_telemetry_endpoint() -> str | None:
    value = os.environ.get("TELEMETRY_ENDPOINT", "").strip()
    if not value:
        return None
    try:
        endpoint = TypeAdapter(AnyHttpUrl).validate_python(value)
    except ValidationError:
        raise RuntimeError("TELEMETRY_ENDPOINT must be an HTTP(S) URL") from None
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise RuntimeError("TELEMETRY_ENDPOINT must not contain credentials, query or fragment")
    return str(endpoint)
