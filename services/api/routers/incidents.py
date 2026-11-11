"""Incidents API router for CRUD management, lifecycle transitions, analysis and export."""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from starlette import status as http_status

from services.api.auth_dependencies import get_current_user

# Ensure monorepo root is on sys.path for packages
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.incident_analyzer import (
    IncidentAnalysisResult,
    analyze_csv_stream,
    export_results_to_csv_string,
)
from services.api.incident_models import (
    ALLOWED_BRANCHES,
    ALLOWED_CATEGORIES,
    ALLOWED_ORIGINS,
    ALLOWED_STATUSES,
    IncidentCreate,
    IncidentAnalysisResponse,
    IncidentListItem,
    IncidentRecord,
    IncidentStatusUpdate,
    IncidentSummary,
    IncidentValidationErrorResponse,
    validate_status_transition,
)
from services.api.incident_storage import (
    get_incident_database_path,
    open_incident_table,
)
from services.api.response_cache import response_cache

router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
)

# In-memory store for the latest analysis result
_latest_analysis_result: Optional[IncidentAnalysisResult] = None
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB limit
INCIDENT_SUMMARY_CACHE_TTL_SECONDS = 30


def _incident_summary_cache_key() -> tuple[str, str]:
    return ("incidents:summary", str(get_incident_database_path()))


def get_latest_result() -> Optional[IncidentAnalysisResult]:
    """Helper for testing and retrieval."""
    return _latest_analysis_result


def set_latest_result(result: Optional[IncidentAnalysisResult]) -> None:
    """Helper to update or reset the latest analysis result."""
    global _latest_analysis_result
    _latest_analysis_result = result


def _to_incident_record(document: Any) -> IncidentRecord:
    record = dict(document)
    record["id"] = document.doc_id
    return IncidentRecord.model_validate(record)


# =========================================================================
# Incident Management CRUD & Summary Endpoints
# =========================================================================


@router.get(
    "/summary",
    response_model=IncidentSummary,
    summary="Operational metrics summary across incident dimensions",
    responses={
        500: {"model": DetailErrorResponse, "description": "Storage or internal server error."},
    },
)
def get_incidents_summary() -> IncidentSummary:
    """
    Returns aggregated metrics by status, category, origin, and branch.
    Responds cleanly with zero values when the storage is empty.
    """
    def calculate_summary() -> IncidentSummary:
        try:
            with open_incident_table() as table:
                records = table.all()
        except OSError:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error accessing incident storage",
            ) from None

        status_counts: dict[str, int] = {st: 0 for st in ALLOWED_STATUSES}
        category_counts: dict[str, int] = {cat: 0 for cat in ALLOWED_CATEGORIES}
        origin_counts: dict[str, int] = {orig: 0 for orig in ALLOWED_ORIGINS}
        branch_counts: dict[str, int] = {br: 0 for br in ALLOWED_BRANCHES}

        for doc in records:
            st = doc.get("status")
            if st in status_counts:
                status_counts[st] += 1
            cat = doc.get("category")
            if cat in category_counts:
                category_counts[cat] += 1
            orig = doc.get("origin")
            if orig in origin_counts:
                origin_counts[orig] += 1
            br = doc.get("branch")
            if br in branch_counts:
                branch_counts[br] += 1

        return IncidentSummary(
            total=len(records),
            by_status=status_counts,  # type: ignore
            by_category=category_counts,  # type: ignore
            by_origin=origin_counts,  # type: ignore
            by_branch=branch_counts,  # type: ignore
        )

    return response_cache.get_or_set(
        _incident_summary_cache_key(),
        INCIDENT_SUMMARY_CACHE_TTL_SECONDS,
        calculate_summary,
    )


@router.post(
    "",
    response_model=IncidentRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new incident",
    responses={
        400: {"model": IncidentValidationErrorResponse, "description": "Invalid incident payload."},
        500: {"model": DetailErrorResponse, "description": "Storage or internal server error."},
        "4XX": {"model": DetailErrorResponse, "description": "Other client errors; validation uses HTTP 400."},
    },
)
def create_incident(incident: IncidentCreate) -> IncidentRecord:
    """
    Create a new incident.
    Validates all mandatory fields and enum constraints according to Nexova briefing.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    data = incident.model_dump(mode="json")
    data["created_at"] = now_iso
    data["updated_at"] = now_iso

    try:
        with open_incident_table() as table:
            doc_id = table.insert(data)
            document = table.get(doc_id=doc_id)
    except OSError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error persisting incident",
        ) from None

    response_cache.invalidate(_incident_summary_cache_key())
    return _to_incident_record(document)


@router.get(
    "",
    response_model=list[IncidentListItem],
    summary="List incidents with optional combinable filters",
    responses={
        400: {"model": DetailErrorResponse | IncidentValidationErrorResponse, "description": "Invalid filter or query."},
        500: {"model": DetailErrorResponse, "description": "Storage or internal server error."},
        "4XX": {"model": DetailErrorResponse, "description": "Other client errors; validation uses HTTP 400."},
    },
)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    origin: Optional[str] = Query(None, description="Filter by origin"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    category: Optional[str] = Query(None, description="Filter by category"),
) -> list[IncidentListItem]:
    """
    List all stored incidents.
    Supports combinable filtering by status, origin, branch, and category.
    Returns an empty list when the database has no matching records.
    """
    if status is not None and status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status filter '{status}'. Allowed: {list(ALLOWED_STATUSES)}",
        )
    if origin is not None and origin not in ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid origin filter '{origin}'. Allowed: {list(ALLOWED_ORIGINS)}",
        )
    if branch is not None and branch not in ALLOWED_BRANCHES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid branch filter '{branch}'. Allowed: {list(ALLOWED_BRANCHES)}",
        )
    if category is not None and category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category filter '{category}'. Allowed: {list(ALLOWED_CATEGORIES)}",
        )

    try:
        with open_incident_table() as table:
            docs = table.all()
    except OSError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving incidents from storage",
        ) from None

    results: list[IncidentListItem] = []
    for doc in docs:
        if status is not None and doc.get("status") != status:
            continue
        if origin is not None and doc.get("origin") != origin:
            continue
        if branch is not None and doc.get("branch") != branch:
            continue
        if category is not None and doc.get("category") != category:
            continue
        record = _to_incident_record(doc)
        results.append(IncidentListItem.model_validate(record.model_dump(exclude={"updated_at"})))

    return results


@router.get(
    "/{id}",
    response_model=IncidentRecord,
    summary="Retrieve an incident by ID",
    responses={
        400: {"model": IncidentValidationErrorResponse, "description": "Invalid incident ID."},
        404: {"model": DetailErrorResponse, "description": "Incident not found."},
        500: {"model": DetailErrorResponse, "description": "Storage or internal server error."},
        "4XX": {"model": DetailErrorResponse, "description": "Other client errors; validation uses HTTP 400."},
    },
)
def get_incident(id: int) -> IncidentRecord:
    """
    Retrieve incident detail by primary doc_id.
    Returns HTTP 404 when not found.
    """
    try:
        with open_incident_table() as table:
            doc = table.get(doc_id=id)
    except OSError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving incident",
        ) from None

    if doc is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {id} not found",
        )

    return _to_incident_record(doc)


@router.patch(
    "/{id}/status",
    response_model=IncidentRecord,
    summary="Update an incident lifecycle status",
    responses={
        400: {"model": DetailErrorResponse | IncidentValidationErrorResponse, "description": "Invalid payload, ID or lifecycle transition."},
        404: {"model": DetailErrorResponse, "description": "Incident not found."},
        500: {"model": DetailErrorResponse, "description": "Storage or internal server error."},
        "4XX": {"model": DetailErrorResponse, "description": "Other client errors; validation uses HTTP 400."},
    },
)
def update_incident_status(id: int, update: IncidentStatusUpdate) -> IncidentRecord:
    """
    Update incident status strictly according to Nexova lifecycle rules.
    Terminal states and invalid transitions are rejected with HTTP 400.
    """
    try:
        with open_incident_table() as table:
            doc = table.get(doc_id=id)
            if doc is None:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Incident with ID {id} not found",
                )

            current_status = doc.get("status")
            new_status = update.status

            try:
                validate_status_transition(current_status, new_status)
            except ValueError as err:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=str(err),
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            table.update({"status": new_status, "updated_at": now_iso}, doc_ids=[id])
            updated_doc = table.get(doc_id=id)
    except OSError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating incident status in storage",
        ) from None

    response_cache.invalidate(_incident_summary_cache_key())
    return _to_incident_record(updated_doc)


# =========================================================================
# Legacy Helpdesk CSV Analyzer & Export Endpoints (Auth Protected)
# =========================================================================


@router.post(
    "/analyze",
    response_model=IncidentAnalysisResponse,
    summary="Analyze an uploaded CSV file of incident tickets",
    response_description="Aggregated metrics and breakdown without customer PII",
    dependencies=[Depends(get_current_user)],
    responses={
        400: {
            "model": DetailErrorResponse | IncidentValidationErrorResponse,
            "description": "Invalid CSV or multipart request; validation errors use HTTP 400.",
        },
        401: {
            "model": DetailErrorResponse,
            "description": "Missing or invalid Bearer credentials.",
            "headers": {"WWW-Authenticate": {"schema": {"type": "string", "const": "Bearer"}}},
        },
        413: {"model": DetailErrorResponse, "description": "CSV exceeds the 25 MiB limit."},
        500: {"model": DetailErrorResponse, "description": "Analysis or internal server error."},
        "4XX": {
            "model": DetailErrorResponse,
            "description": "Other client errors. Request validation is documented as HTTP 400, not 422.",
        },
    },
)
async def analyze_incidents(file: UploadFile = File(...)) -> IncidentAnalysisResponse:
    """
    Accepts a multipart/form-data CSV file.
    Validates file headers and formats, runs deterministic analysis,
    and returns aggregated volume and satisfaction metrics.
    Guarantees no customer email or sensitive fields are returned.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are supported.",
        )

    # Read content with size check
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty.",
        )

    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text_content = content_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="File encoding error. Please upload a UTF-8 encoded CSV file.",
            )

    stream = io.StringIO(text_content)

    try:
        analysis_result = analyze_csv_stream(stream)
    except ValueError as val_err:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the incident file.",
        )

    response = IncidentAnalysisResponse.model_validate(analysis_result.to_dict())

    # Store latest result in memory for export
    set_latest_result(analysis_result)

    return response


@router.get(
    "/results/export",
    response_class=Response,
    response_model=None,
    summary="Export the latest analysis results as a summary CSV",
    response_description="A CSV file containing aggregated metrics (one metric per row)",
    dependencies=[Depends(get_current_user)],
    responses={
        200: {
            "description": (
                "UTF-8 CSV with header metric,value and one aggregate per row. "
                "Metrics: total_records, valid_records, invalid_records; category_<lowercase category>; "
                "status_<lowercase status>; satisfaction_scored_tickets, satisfaction_total_closed, "
                "satisfaction_average_score (two decimals or N/A); satisfaction_score_1 through "
                "satisfaction_score_5; invalid_reason_<normalized rule label>. "
                "No raw tickets, row errors or personal data."
            ),
            "content": {
                "text/csv": {
                    "schema": {"type": "string"},
                    "example": "metric,value\ntotal_records,0\nvalid_records,0\ninvalid_records,0\n",
                }
            },
            "headers": {
                "Content-Disposition": {
                    "schema": {"type": "string", "const": 'attachment; filename="results.csv"'}
                },
                "Cache-Control": {"schema": {"type": "string", "const": "no-cache"}},
            },
        },
        401: {
            "model": DetailErrorResponse,
            "description": "Missing or invalid Bearer credentials.",
            "headers": {"WWW-Authenticate": {"schema": {"type": "string", "const": "Bearer"}}},
        },
        404: {"model": DetailErrorResponse, "description": "No completed analysis is available."},
        500: {"model": DetailErrorResponse, "description": "Export or internal server error."},
    },
)
async def export_latest_results() -> Response:
    """
    Downloads the results of the most recent analysis execution.
    Contains only aggregated metrics without raw tickets or emails.
    """
    latest = get_latest_result()
    if latest is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No analysis results available to export. Please run an analysis first.",
        )

    csv_output = export_results_to_csv_string(latest)

    return Response(
        content=csv_output,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="results.csv"',
            "Cache-Control": "no-cache",
        },
    )
