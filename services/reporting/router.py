"""FastAPI router for business performance reporting endpoints under /reporting.

Thin service interface: delegates pipeline execution and database queries to data/pipelines.
Adheres strictly to the architectural contract in pipeline-2.md and data/pipelines/PIPELINE_DESIGN.md.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from data.pipelines.db import get_latest_pipeline_run_log, get_reporting_engine
from data.pipelines.models import (
    PipelineRunMetadata,
    TriggerPipelineRequest,
    TriggerPipelineResponse,
    WeeklyPerformanceEntry,
    WeeklyPerformanceResponse,
)
from data.pipelines.pipeline import (
    get_iso_week_start,
    weekly_business_performance_pipeline,
)
from data.pipelines.queries import get_weekly_kpis_for_reporting
from services.api.response_models import DetailErrorResponse

logger = logging.getLogger("nexova.reporting_api")

router = APIRouter(prefix="/reporting", tags=["Reporting"])


# --- Endpoint 1: Latest Pipeline Run Metadata ---

@router.get(
    "/pipeline-runs/latest",
    response_model=PipelineRunMetadata,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": DetailErrorResponse, "description": "No pipeline runs recorded."},
    },
    summary="Get status and metadata of the most recent pipeline execution run",
)
@router.get(
    "/status",
    response_model=PipelineRunMetadata,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Alias for /pipeline-runs/latest",
)
def get_latest_pipeline_run() -> PipelineRunMetadata:
    """Retrieve metadata of the latest execution run for observability and health monitoring."""
    log_data = get_latest_pipeline_run_log()
    if not log_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pipeline runs recorded",
        )

    started_at = log_data["started_at"]
    finished_at = log_data.get("finished_at")
    duration = None
    if started_at and finished_at:
        duration = round((finished_at - started_at).total_seconds(), 2)

    return PipelineRunMetadata(
        run_id=str(log_data["run_id"]),
        flow_name=str(log_data["flow_name"]),
        status=str(log_data["status"]),
        trigger_mode=str(log_data["trigger_mode"]),
        window_start=str(log_data["window_start"]),
        window_end=str(log_data["window_end"]),
        started_at=started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at),
        finished_at=finished_at.isoformat() if hasattr(finished_at, "isoformat") else (str(finished_at) if finished_at else None),
        duration_seconds=duration,
        records_extracted=int(log_data.get("records_extracted") or 0),
        records_loaded=int(log_data.get("records_loaded") or 0),
        checkpoint_phase=str(log_data.get("checkpoint_phase") or "UNKNOWN"),
        error_details=log_data.get("error_details"),
    )


# --- Endpoint 2: Trigger Pipeline Run Manually ---

@router.post(
    "/pipeline-runs",
    response_model=TriggerPipelineResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the business performance pipeline run",
)
@router.post(
    "/pipeline/trigger",
    response_model=TriggerPipelineResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
    summary="Alias for /pipeline-runs",
)
def trigger_pipeline_run(payload: Optional[TriggerPipelineRequest] = None) -> TriggerPipelineResponse:
    """Trigger the pipeline flow without duplicating ETL logic inside the API layer."""
    target_date = payload.target_week_start if payload else None
    buffer_week = payload.reprocess_buffer_week if payload else False

    try:
        result = weekly_business_performance_pipeline(
            target_week_start=target_date,
            trigger_mode="manual",
            include_buffer_week=buffer_week,
        )
        return TriggerPipelineResponse(
            run_id=result["run_id"],
            status=result["status"],
            target_week_start=str(target_date) if target_date else None,
            message="Pipeline run triggered successfully",
        )
    except Exception as exc:
        logger.error("Failed to trigger pipeline run: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute pipeline run: {exc}",
        ) from None


# --- Endpoint 3: Weekly Performance KPIs for Business Stakeholders ---

@router.get(
    "/weekly-office-program-performance",
    response_model=WeeklyPerformanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": DetailErrorResponse, "description": "Invalid date format for week_start."},
    },
    summary="Get weekly aggregated business KPIs by office and programme",
)
@router.get(
    "/kpis/weekly",
    response_model=WeeklyPerformanceResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Alias for /weekly-office-program-performance",
)
def get_weekly_performance_kpis(
    week_start: Optional[str] = Query(None, description="ISO week start date YYYY-MM-DD (Monday UTC)"),
    office: Optional[str] = Query(None, description="Filter by office: valencia or miami"),
    programme_id: Optional[str] = Query(None, description="Filter by training programme identifier"),
) -> WeeklyPerformanceResponse:
    """Retrieve consolidated business performance KPIs for Laura (CEO) and Elena (L&D)."""
    parsed_date: Optional[date] = None
    if week_start is not None:
        try:
            parsed_date = date.fromisoformat(week_start.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid week_start format. Expected YYYY-MM-DD.",
            )

    effective_week, raw_entries = get_weekly_kpis_for_reporting(
        week_start=parsed_date,
        office=office,
        programme_id=programme_id,
    )

    if effective_week is None:
        effective_week = parsed_date or get_iso_week_start()

    entries = [WeeklyPerformanceEntry(**e) for e in raw_entries]

    return WeeklyPerformanceResponse(
        week_start=str(effective_week),
        entries=entries,
    )
