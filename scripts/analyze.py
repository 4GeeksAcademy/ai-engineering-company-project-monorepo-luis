#!/usr/bin/env python3
"""
CLI script to analyze Nexova helpdesk incident CSV files.

Usage:
    python scripts/analyze.py <path-to-csv> [--export] [--output <output.csv>]
"""

import argparse
import sys
from pathlib import Path

# Ensure monorepo root is in Python path for shared packages
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from packages.incident_analyzer import (
    analyze_incidents_file,
    export_results_to_file,
    IncidentAnalysisResult,
    VALID_CATEGORIES,
    VALID_STATUSES,
)


def format_summary_cli(result: IncidentAnalysisResult, filename: str) -> str:
    """Formats the analysis metrics according to the official Nexova specification."""
    lines = []
    lines.append("============================================================")
    lines.append("  NEXOVA — SUPPORT TICKET ANALYSIS")
    lines.append(f"  Source file: {filename}")
    lines.append("============================================================")
    lines.append("")

    # Records count
    lines.append(f"TOTAL RECORDS IN FILE .......... {result.total_records}")
    lines.append(f"  ├─ Valid records ................ {result.valid_records}")
    lines.append(f"  └─ Invalid / incomplete .......... {result.invalid_records}")
    lines.append("")

    # Invalid breakdown
    lines.append("INVALID RECORDS BREAKDOWN")
    if not result.invalid_breakdown:
        lines.append("  └─ None (all records valid)")
    else:
        breakdown_items = list(result.invalid_breakdown.items())
        for idx, (label, count) in enumerate(breakdown_items):
            branch = "└─" if idx == len(breakdown_items) - 1 else "├─"
            dot_count = max(1, 35 - len(label))
            dots = "." * dot_count
            lines.append(f"  {branch} {label} {dots} {count}")
    lines.append("")

    # Categories breakdown
    lines.append("BREAKDOWN BY CATEGORY (valid records)")
    total_valid = result.valid_records
    for idx, cat in enumerate(VALID_CATEGORIES):
        count = result.category_counts.get(cat, 0)
        pct = (count / total_valid * 100) if total_valid > 0 else 0.0
        branch = "└─" if idx == len(VALID_CATEGORIES) - 1 else "├─"
        dot_count = max(1, 35 - len(cat))
        dots = "." * dot_count
        lines.append(f"  {branch} {cat} {dots} {count:2d}  ({pct:4.1f}%)")
    lines.append("")

    # Status breakdown
    lines.append("BREAKDOWN BY STATUS (valid records)")
    for idx, st in enumerate(VALID_STATUSES):
        count = result.status_counts.get(st, 0)
        pct = (count / total_valid * 100) if total_valid > 0 else 0.0
        branch = "└─" if idx == len(VALID_STATUSES) - 1 else "├─"
        dot_count = max(1, 35 - len(st))
        dots = "." * dot_count
        lines.append(f"  {branch} {st} {dots} {count:2d}  ({pct:4.1f}%)")
    lines.append("")

    # Satisfaction index
    lines.append("SATISFACTION INDEX (closed tickets)")
    sat = result.satisfaction
    lines.append(f"  Scored tickets: {sat.scored_tickets} of {sat.total_closed_tickets}")
    if sat.average_score is not None:
        lines.append(f"  Average score: {sat.average_score:.2f} / 5.00")
    else:
        lines.append("  Average score: N/A")

    score_labels = {
        1: "Score 1 (Very dissatisfied)",
        2: "Score 2 (Dissatisfied)",
        3: "Score 3 (Neutral)",
        4: "Score 4 (Satisfied)",
        5: "Score 5 (Very satisfied)",
    }
    for score in range(1, 6):
        branch = "└─" if score == 5 else "├─"
        label = score_labels[score]
        count = sat.score_distribution.get(score, 0)
        dot_count = max(1, 35 - len(label))
        dots = "." * dot_count
        lines.append(f"  {branch} {label} {dots} {count:2d}")

    lines.append("")
    lines.append("============================================================")
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Nexova incidents CSV export for volume and satisfaction."
    )
    parser.add_argument(
        "file_path",
        help="Path to the incidents CSV file (e.g. data/raw/incidents-nexova.csv)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export summary results to results.csv without asking interactively",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip export without asking interactively",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="results.csv",
        help="Target filename for CSV export (default: results.csv)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    csv_path = Path(args.file_path)

    if not csv_path.exists():
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        return 1

    try:
        result = analyze_incidents_file(csv_path)
    except ValueError as e:
        print(f"Error validating CSV file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error during analysis: {e}", file=sys.stderr)
        return 1

    # Print summary output
    print(format_summary_cli(result, csv_path.name))

    # Determine whether to export to CSV
    should_export = False
    if args.export:
        should_export = True
    elif args.no_export:
        should_export = False
    else:
        # Interactive prompt if stdin is available
        if sys.stdin.isatty():
            try:
                answer = input("Export results to CSV? [y / n]: ").strip().lower()
                should_export = answer in ("y", "yes", "s", "si", "sí")
            except (EOFError, KeyboardInterrupt):
                print()
                should_export = False
        else:
            # Non-interactive without flags: do not export
            should_export = False

    if should_export:
        target_path = Path(args.output)
        try:
            export_results_to_file(result, target_path, overwrite=True)
            print(f"Results exported successfully to {target_path}")
        except Exception as e:
            print(f"Error exporting results to CSV: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
