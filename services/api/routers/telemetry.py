"""Telemetry receiver and reporting router.

Provides:
- POST /telemetry/events: partial batch validation, bulk persistence, metadata logging.
- GET /telemetry/report: technical metrics report with in-memory TTL caching.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.api.response_cache import response_cache
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
from services.telemetry.analysis import build_telemetry_report

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])
logger = logging.getLogger(__name__)

REPORT_CACHE_TTL_SECONDS = 60.0


class TelemetryReportPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from", description="UTC start datetime (inclusive)")
    to: str = Field(description="UTC end datetime (exclusive)")


class TelemetryReportMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events_per_day: list[dict[str, Any]]
    error_rate_by_type: list[dict[str, Any]]
    latency_by_route_group: list[dict[str, Any]]
    auth_failure_rate: list[dict[str, Any]] = Field(default_factory=list)


class TelemetryReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    period: TelemetryReportPeriod
    metrics: TelemetryReportMetrics


def parse_report_dates(
    start_date_str: Optional[str],
    end_date_str: Optional[str],
) -> tuple[datetime, datetime]:
    """Parse, validate, and normalize report query params to UTC datetimes.

    Policy:
    - If neither is provided, defaults to the last 7 days window ending now (UTC).
    - If only one is provided, raises HTTP 400 requiring both for explicit range.
    - If invalid ISO 8601 or missing timezone offset, raises HTTP 400.
    - If start_date >= end_date, raises HTTP 400.
    """
    if start_date_str is None and end_date_str is None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        start = now - timedelta(days=7)
        return start, now

    if start_date_str is None or end_date_str is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both start_date and end_date must be provided for explicit date ranges, or omit both for the default 7-day period.",
        )

    try:
        start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid start_date format. Expected ISO 8601 with timezone.",
        )

    try:
        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid end_date format. Expected ISO 8601 with timezone.",
        )

    if start_dt.tzinfo is None or start_dt.tzinfo.utcoffset(start_dt) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must include timezone offset (e.g. UTC 'Z')",
        )

    if end_dt.tzinfo is None or end_dt.tzinfo.utcoffset(end_dt) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must include timezone offset (e.g. UTC 'Z')",
        )

    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)

    if start_utc >= end_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be strictly before end_date",
        )

    return start_utc, end_utc



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


@router.get(
    "/report",
    response_model=TelemetryReportResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": DetailErrorResponse, "description": "Invalid date range or format."},
        503: {"model": DetailErrorResponse, "description": "Telemetry storage unavailable."},
    },
)
def get_telemetry_report(
    start_date: Optional[str] = Query(None, description="Start date ISO 8601 with timezone (inclusive)"),
    end_date: Optional[str] = Query(None, description="End date ISO 8601 with timezone (exclusive)"),
) -> TelemetryReportResponse:
    """Retrieve operational and technical telemetry metrics.

    Calculates metrics over the specified window (or default last 7 days).
    Results are cached in-memory with a 60-second TTL keyed by normalized UTC dates.
    """
    start_utc, end_utc = parse_report_dates(start_date, end_date)

    cache_key = (
        "telemetry_report",
        start_utc.isoformat(),
        end_utc.isoformat(),
    )

    def _generate_report() -> dict[str, Any]:
        try:
            return build_telemetry_report(start_utc, end_utc)
        except Exception as exc:
            logger.error("Failed to generate telemetry report: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry storage unavailable",
            ) from None

    report_payload = response_cache.get_or_set(
        key=cache_key,
        ttl_seconds=REPORT_CACHE_TTL_SECONDS,
        factory=_generate_report,
    )

    return TelemetryReportResponse.model_validate(report_payload)

