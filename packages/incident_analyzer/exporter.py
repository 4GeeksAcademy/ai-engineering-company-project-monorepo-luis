"""Exporter functions to serialize analysis metrics into CSV format."""

import csv
import io
from pathlib import Path
from typing import List, Tuple, Union

from .models import IncidentAnalysisResult, VALID_CATEGORIES, VALID_STATUSES


def generate_results_csv_rows(result: IncidentAnalysisResult) -> List[Tuple[str, str]]:
    """
    Generates a list of (metric, value) tuples for summary export.
    Guarantees no customer PII or raw rows are present.
    """
    rows: List[Tuple[str, str]] = [
        ("total_records", str(result.total_records)),
        ("valid_records", str(result.valid_records)),
        ("invalid_records", str(result.invalid_records)),
    ]

    # Categories
    for cat in VALID_CATEGORIES:
        rows.append((f"category_{cat.lower()}", str(result.category_counts.get(cat, 0))))

    # Statuses
    for st in VALID_STATUSES:
        rows.append((f"status_{st.lower()}", str(result.status_counts.get(st, 0))))

    # Satisfaction
    sat = result.satisfaction
    rows.append(("satisfaction_scored_tickets", str(sat.scored_tickets)))
    rows.append(("satisfaction_total_closed", str(sat.total_closed_tickets)))
    avg_str = f"{sat.average_score:.2f}" if sat.average_score is not None else "N/A"
    rows.append(("satisfaction_average_score", avg_str))

    for score in range(1, 6):
        rows.append((f"satisfaction_score_{score}", str(sat.score_distribution.get(score, 0))))

    # Invalid breakdown
    for rule, count in result.invalid_breakdown.items():
        clean_rule = rule.lower().replace(" ", "_").replace("/", "_")
        rows.append((f"invalid_reason_{clean_rule}", str(count)))

    return rows


def export_results_to_csv_string(result: IncidentAnalysisResult) -> str:
    """Exports metrics to an in-memory CSV string with header 'metric,value'."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["metric", "value"])
    for metric, value in generate_results_csv_rows(result):
        writer.writerow([metric, value])
    return output.getvalue()


def export_results_to_file(
    result: IncidentAnalysisResult,
    target_path: Union[str, Path],
    overwrite: bool = True,
) -> Path:
    """
    Writes the aggregated metrics to a CSV file.
    
    Raises:
        FileExistsError: If target file exists and overwrite is False.
    """
    path = Path(target_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Target file already exists: {target_path}")

    csv_content = export_results_to_csv_string(result)
    path.write_text(csv_content, encoding="utf-8")
    return path
