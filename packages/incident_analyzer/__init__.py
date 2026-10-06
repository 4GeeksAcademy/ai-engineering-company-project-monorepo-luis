"""Nexova Incident Analyzer - Shared core library."""

from .models import (
    IncidentAnalysisResult,
    RowError,
    SatisfactionStats,
    VALID_CATEGORIES,
    VALID_STATUSES,
    RULE_LABELS,
)
from .validator import REQUIRED_COLUMNS, validate_row
from .analyzer import analyze_csv_stream, analyze_incidents_file
from .exporter import (
    export_results_to_csv_string,
    export_results_to_file,
    generate_results_csv_rows,
)

__all__ = [
    "IncidentAnalysisResult",
    "RowError",
    "SatisfactionStats",
    "VALID_CATEGORIES",
    "VALID_STATUSES",
    "RULE_LABELS",
    "REQUIRED_COLUMNS",
    "validate_row",
    "analyze_csv_stream",
    "analyze_incidents_file",
    "export_results_to_csv_string",
    "export_results_to_file",
    "generate_results_csv_rows",
]
