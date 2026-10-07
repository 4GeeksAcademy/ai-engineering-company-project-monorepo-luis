"""Incidents API router for analysis and report export."""

import io
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

# Ensure monorepo root is on sys.path for packages.incident_analyzer
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.incident_analyzer import (
    IncidentAnalysisResult,
    analyze_csv_stream,
    export_results_to_csv_string,
)

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

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


@router.post(
    "/analyze",
    summary="Analyze an uploaded CSV file of incident tickets",
    response_description="Aggregated metrics and breakdown without customer PII",
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are supported.",
        )

    # Read content with size check
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty.",
        )

    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text_content = content_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File encoding error. Please upload a UTF-8 encoded CSV file.",
            )

    stream = io.StringIO(text_content)

    try:
        analysis_result = analyze_csv_stream(stream)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the incident file.",
        )

    # Store latest result in memory for export
    set_latest_result(analysis_result)

    return analysis_result.to_dict()


@router.get(
    "/results/export",
    summary="Export the latest analysis results as a summary CSV",
    response_description="A CSV file containing aggregated metrics (one metric per row)",
)
async def export_latest_results():
    """
    Downloads the results of the most recent analysis execution.
    Contains only aggregated metrics without raw tickets or emails.
    """
    latest = get_latest_result()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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
