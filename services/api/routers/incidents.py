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
    IncidentRecord,
    IncidentStatusUpdate,
    IncidentSummary,
    validate_status_transition,
)
from services.api.incident_storage import open_incident_table

router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
)

# In-memory store for the latest analysis result
_latest_analysis_result: Optional[IncidentAnalysisResult] = None
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB limit


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
)
def get_incidents_summary() -> IncidentSummary:
    """
    Returns aggregated metrics by status, category, origin, and branch.
    Responds cleanly with zero values when the storage is empty.
    """
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


@router.post(
    "",
    response_model=IncidentRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new incident",
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

    return _to_incident_record(document)


@router.get(
    "",
    response_model=list[IncidentRecord],
    summary="List incidents with optional combinable filters",
)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    origin: Optional[str] = Query(None, description="Filter by origin"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    category: Optional[str] = Query(None, description="Filter by category"),
) -> list[IncidentRecord]:
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

    results: list[IncidentRecord] = []
    for doc in docs:
        if status is not None and doc.get("status") != status:
            continue
        if origin is not None and doc.get("origin") != origin:
            continue
        if branch is not None and doc.get("branch") != branch:
            continue
        if category is not None and doc.get("category") != category:
            continue
        results.append(_to_incident_record(doc))

    return results


@router.get(
    "/{id}",
    response_model=IncidentRecord,
    summary="Retrieve an incident by ID",
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

    return _to_incident_record(updated_doc)


# =========================================================================
# Legacy Helpdesk CSV Analyzer & Export Endpoints (Auth Protected)
# =========================================================================


@router.post(
    "/analyze",
    summary="Analyze an uploaded CSV file of incident tickets",
    response_description="Aggregated metrics and breakdown without customer PII",
    dependencies=[Depends(get_current_user)],
)
async def analyze_incidents(file: UploadFile = File(...)):
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

    # Store latest result in memory for export
    set_latest_result(analysis_result)

    return analysis_result.to_dict()


@router.get(
    "/results/export",
    summary="Export the latest analysis results as a summary CSV",
    response_description="A CSV file containing aggregated metrics (one metric per row)",
    dependencies=[Depends(get_current_user)],
)
async def export_latest_results():
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
