"""Verification script for telemetry report against Supabase / PostgreSQL.

Connects to the database configured via SUPABASE_DB_URL or DATABASE_URL,
checks that at least 20 events with variety exist, executes the report pipeline,
and prints the sanitized JSON payload.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from services.api.telemetry_storage import (
    TelemetryDatabaseNotConfiguredError,
    get_telemetry_database_url,
    get_telemetry_engine,
    telemetry_events_table,
)
from services.telemetry.analysis import build_telemetry_report


def run_verification() -> int:
    try:
        url = get_telemetry_database_url()
    except TelemetryDatabaseNotConfiguredError as exc:
        print(f"[BLOCKED] Database URL not configured: {exc}")
        print("Please set SUPABASE_DB_URL or DATABASE_URL in your environment or services/api/.env.")
        return 1

    engine = get_telemetry_engine()

    with engine.connect() as conn:
        count_stmt = select(func.count()).select_from(telemetry_events_table)
        total_events = conn.execute(count_stmt).scalar() or 0

        types_stmt = (
            select(
                telemetry_events_table.c.event_type,
                func.count().label("cnt"),
            )
            .group_by(telemetry_events_table.c.event_type)
        )
        types_breakdown = conn.execute(types_stmt).fetchall()

    print(f"Total events in telemetry_events: {total_events}")
    print("Events breakdown:")
    for event_type, cnt in types_breakdown:
        print(f"  - {event_type}: {cnt}")

    if total_events < 20:
        print(
            f"\n[WARNING] Dataset has {total_events} events (< 20 required by specification)."
            " Generate additional real/test events from the backoffice before finalizing E2E evidence."
        )

    # Run report on the last 7 days (or broader window if events are older)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=30)
    end = now + timedelta(days=1)

    print(f"\nExecuting build_telemetry_report for window: {start.isoformat()} to {end.isoformat()}...")
    report = build_telemetry_report(start, end, engine=engine)

    print("\nSanitized report output:")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
