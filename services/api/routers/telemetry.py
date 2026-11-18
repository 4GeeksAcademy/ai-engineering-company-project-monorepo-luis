"""Telemetry receiver: partial batch validation, bulk persistence, and controlled metadata logging."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from services.api.response_models import DetailErrorResponse
from services.api.telemetry import (
    RawTelemetryBatch,
    TelemetryBatchResponse,
    TelemetryEvent,
    map_event_to_row,
)
from services.api.telemetry_storage import (
    TelemetryStorageError,
    store_telemetry_events,
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])
logger = logging.getLogger(__name__)


@router.post(
    "/events",
    response_model=TelemetryBatchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"model": DetailErrorResponse, "description": "Invalid telemetry batch container."},
        503: {"model": DetailErrorResponse, "description": "Telemetry storage unavailable."},
    },
)
def receive_events(payload: RawTelemetryBatch) -> TelemetryBatchResponse:
    received = len(payload.events)
    if received == 0:
        logger.info(
            "Telemetry processed: received=0 stored=0 rejected=0 event_types=[]"
        )
        return TelemetryBatchResponse(received=0, stored=0, rejected=0)

    valid_events: list[TelemetryEvent] = []
    rejected = 0

    for item in payload.events:
        if not isinstance(item, dict):
            rejected += 1
            continue
        try:
            event = TelemetryEvent.model_validate(item)
            valid_events.append(event)
        except ValidationError:
            rejected += 1

    stored = 0
    if valid_events:
        rows = [map_event_to_row(ev) for ev in valid_events]
        try:
            stored = store_telemetry_events(rows)
        except TelemetryStorageError:
            logger.error("Telemetry persistence failed during batch storage")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry storage unavailable",
            ) from None

    valid_types = sorted({ev.event_type for ev in valid_events})
    logger.info(
        "Telemetry processed: received=%d stored=%d rejected=%d event_types=%s",
        received,
        stored,
        rejected,
        valid_types,
    )

    return TelemetryBatchResponse(
        received=received,
        stored=stored,
        rejected=rejected,
    )
