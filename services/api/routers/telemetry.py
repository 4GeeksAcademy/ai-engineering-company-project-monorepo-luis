"""Temporary telemetry receiver: validation and controlled metadata only."""

import logging

from fastapi import APIRouter

from services.api.response_models import DetailErrorResponse
from services.api.telemetry import TelemetryBatch, TelemetryReceived

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])
logger = logging.getLogger(__name__)


@router.post(
    "/events",
    response_model=TelemetryReceived,
    responses={422: {"model": DetailErrorResponse, "description": "Invalid telemetry batch."}},
)
def receive_events(payload: TelemetryBatch) -> TelemetryReceived:
    event_types = sorted({event.event_type for event in payload.events})
    logger.info("Telemetry received: count=%d event_types=%s", len(payload.events), event_types)
    return TelemetryReceived(received=len(payload.events))
