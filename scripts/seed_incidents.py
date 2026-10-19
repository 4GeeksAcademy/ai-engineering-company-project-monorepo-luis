#!/usr/bin/env python3
"""
Seed script to import historical incident records from CSV into Nexova TinyDB storage.

Usage:
    python scripts/seed_incidents.py [--csv <path-to-csv>]
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure monorepo root is on sys.path
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

from packages.incident_analyzer.validator import validate_row
from services.api.incident_models import IncidentCategory, IncidentStatus
from services.api.incident_storage import open_incident_database

DEFAULT_CSV_PATH = REPO_ROOT / "data" / "raw" / "incidents-nexova.csv"

# Exact briefing mappings
STATUS_MAP: dict[str, IncidentStatus] = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}

CATEGORY_MAP: dict[str, IncidentCategory] = {
    "TECHNICAL": "technical_failure",
    "BILLING": "process_error",
    "ACCESS": "technical_failure",
    "HR_QUERY": "process_error",
    "COMPLAINT": "client_complaint",
}


def seed_incidents(csv_path: Path | str | None = None) -> dict[str, int]:
    """
    Import and transform incidents from the raw CSV into TinyDB storage idempotently.
    Returns counts of processed, inserted, skipped invalid, and duplicate rows.
    Guarantees no customer PII or raw ticket_id is persisted in the incident record.
    """
    target_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {target_path}")

    inserted = 0
    skipped_invalid = 0
    skipped_duplicate = 0
    total_processed = 0

    with open(target_path, mode="r", encoding="utf-8", errors="replace") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    with open_incident_database() as database:
        table = database.table("incidents")
        seed_history_table = database.table("_seed_history")

        # Load existing (title, created_at) pairs and seeded ticket_ids to ensure idempotency
        existing_records = {
            (doc.get("title"), doc.get("created_at"))
            for doc in table.all()
        }
        seeded_tickets = {
            doc.get("ticket_id")
            for doc in seed_history_table.all()
            if "ticket_id" in doc
        }

        records_to_insert: list[dict[str, Any]] = []
        seed_history_to_insert: list[dict[str, Any]] = []

        for row_index, row in enumerate(rows, start=2):
            total_processed += 1

            # 1. Reuse existing incident_analyzer validation rules
            is_valid, errors, _ = validate_row(row, row_index)
            if not is_valid:
                skipped_invalid += 1
                continue

            raw_status = row.get("status", "").strip()
            raw_category = row.get("category", "").strip()

            if raw_status not in STATUS_MAP or raw_category not in CATEGORY_MAP:
                skipped_invalid += 1
                continue

            raw_desc = row.get("description", "").strip()
            title = raw_desc[:120].strip()
            if not title:
                skipped_invalid += 1
                continue

            raw_date = row.get("date", "").strip()
            try:
                date_parsed = datetime.strptime(raw_date, "%Y-%m-%d").replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )
                created_at_iso = date_parsed.isoformat()
            except ValueError:
                skipped_invalid += 1
                continue

            ticket_id = row.get("ticket_id", "").strip()

            # 2. Check idempotency: ticket_id is the idempotency key per briefing;
            # fallback to (title, created_at) only if ticket_id is missing from CSV.
            if ticket_id:
                is_duplicate = ticket_id in seeded_tickets
            else:
                is_duplicate = (title, created_at_iso) in existing_records

            if is_duplicate:
                skipped_duplicate += 1
                continue

            # 3. Transform according to Nexova briefing
            # NOTE: ticket_id, customer_email, agent_id, and satisfaction_score are deliberately omitted
            new_record: dict[str, Any] = {
                "title": title,
                "description": raw_desc,
                "category": CATEGORY_MAP[raw_category],
                "status": STATUS_MAP[raw_status],
                "origin": "customer",
                "branch": "central",
                "created_at": created_at_iso,
                "updated_at": created_at_iso,
            }

            records_to_insert.append(new_record)
            existing_records.add((title, created_at_iso))

            if ticket_id:
                seeded_tickets.add(ticket_id)
                seed_history_to_insert.append({"ticket_id": ticket_id, "seeded_at": datetime.now(timezone.utc).isoformat()})

            inserted += 1

        if records_to_insert:
            table.insert_multiple(records_to_insert)

        if seed_history_to_insert:
            seed_history_table.insert_multiple(seed_history_to_insert)

    return {
        "total_processed": total_processed,
        "inserted": inserted,
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate": skipped_duplicate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed historical customer incidents into Nexova storage."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to the raw CSV file to import.",
    )
    args = parser.parse_args()

    try:
        report = seed_incidents(args.csv)
        print("============================================================")
        print("  NEXOVA — INCIDENT HISTORICAL SEED REPORT")
        print("============================================================")
        print(f"  Source file:          {args.csv}")
        print(f"  Total processed:      {report['total_processed']}")
        print(f"  Inserted:             {report['inserted']}")
        print(f"  Skipped (invalid):    {report['skipped_invalid']}")
        print(f"  Duplicates omitted:   {report['skipped_duplicate']}")
        print("============================================================")
        return 0
    except Exception as exc:
        print(f"Error during seeding: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
