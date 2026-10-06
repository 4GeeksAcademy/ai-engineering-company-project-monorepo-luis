"""Core streaming analyzer for Nexova incident CSV exports."""

import csv
import io
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TextIO, Union

from .models import (
    IncidentAnalysisResult,
    RowError,
    SatisfactionStats,
    VALID_CATEGORIES,
    VALID_STATUSES,
    RULE_LABELS,
)
from .validator import REQUIRED_COLUMNS, validate_row


def analyze_csv_stream(stream: Iterable[str]) -> IncidentAnalysisResult:
    """
    Parses and analyzes an incidents CSV stream row-by-row.
    
    Supports files up to millions of lines efficiently using streaming.
    Deterministically computes summary metrics without holding raw rows in memory.
    
    Raises:
        ValueError: If file is empty or missing required header columns.
    """
    # Detect empty stream
    reader = csv.reader(stream)
    try:
        header_row = next(reader)
    except StopIteration:
        raise ValueError("CSV file is empty.")

    # Strip and lowercase/normalize header check
    clean_header = [col.strip() for col in header_row if col.strip()]
    if not clean_header:
        raise ValueError("CSV header is empty or missing.")

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in clean_header]
    if missing_cols:
        raise ValueError(
            f"Missing required columns in CSV header: {', '.join(missing_cols)}"
        )

    # Initialize counters
    result = IncidentAnalysisResult()
    for cat in VALID_CATEGORIES:
        result.category_counts[cat] = 0
    for st in VALID_STATUSES:
        result.status_counts[st] = 0

    satisfaction = SatisfactionStats()
    score_sum = 0
    invalid_breakdown_counts: Dict[str, int] = {}
    row_errors: List[RowError] = []

    row_index = 1  # 1-indexed for header, data starts at 2
    for raw_row in reader:
        row_index += 1
        # Skip completely empty trailing lines
        if not raw_row or all(not cell.strip() for cell in raw_row):
            continue

        result.total_records += 1

        # Match row with header columns
        row_dict = {
            col_name: raw_row[i].strip() if i < len(raw_row) else ""
            for i, col_name in enumerate(clean_header)
        }

        is_valid, errors, parsed_score = validate_row(row_dict, row_number=row_index)

        if is_valid:
            result.valid_records += 1
            cat = row_dict["category"]
            result.category_counts[cat] = result.category_counts.get(cat, 0) + 1

            status = row_dict["status"]
            result.status_counts[status] = result.status_counts.get(status, 0) + 1

            if status == "CLOSED":
                satisfaction.total_closed_tickets += 1
                if parsed_score is not None:
                    satisfaction.scored_tickets += 1
                    satisfaction.score_distribution[parsed_score] = (
                        satisfaction.score_distribution.get(parsed_score, 0) + 1
                    )
                    score_sum += parsed_score
        else:
            result.invalid_records += 1
            row_errors.extend(errors)
            for err in errors:
                rule_label = RULE_LABELS.get(err.rule_key, err.rule_key)
                invalid_breakdown_counts[rule_label] = (
                    invalid_breakdown_counts.get(rule_label, 0) + 1
                )

    # Calculate average satisfaction score
    if satisfaction.scored_tickets > 0:
        satisfaction.average_score = round(
            score_sum / satisfaction.scored_tickets, 2
        )
    else:
        satisfaction.average_score = None

    result.satisfaction = satisfaction
    result.invalid_breakdown = invalid_breakdown_counts
    result.row_errors = row_errors

    return result


def analyze_incidents_file(file_path: Union[str, Path]) -> IncidentAnalysisResult:
    """Convenience helper to analyze a file from path."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {file_path}")

    with path.open("r", encoding="utf-8", errors="replace") as f:
        return analyze_csv_stream(f)
