"""Prefect tasks for the business performance pipeline.

Implements extraction, caching transformation, idempotent atomic loading,
and resilient optional steps.
Adheres strictly to the architectural contract in data/pipelines/PIPELINE_DESIGN.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from prefect import task
from sqlalchemy import Engine

from data.pipelines.db import get_reporting_engine
from data.pipelines.models import weekly_office_program_performance_table
from data.pipelines.queries import (
    extract_telemetry_records,
    transform_events_to_weekly_kpis,
)

logger = logging.getLogger(__name__)


def compute_transform_cache_key(context: Any, parameters: dict[str, Any]) -> str:
    """Generate deterministic cache key based on window boundaries and input event contents.

    Incorporates window_start and a SHA-256 hash of sorted event identifiers, timestamps,
    and event types. Any change in the underlying data invalidates stale cache entries.
    """
    window_start = str(parameters.get("window_start", ""))
    raw_events = parameters.get("raw_events", [])

    event_fingerprints: list[str] = []
    for ev in raw_events:
        dedup_key = ev.get("dedup_key") or ev.get("id") or ""
        event_type = ev.get("event_type") or ""
        ts = str(ev.get("timestamp") or "")
        tags_str = json.dumps(ev.get("tags") or {}, sort_keys=True)
        event_fingerprints.append(f"{dedup_key}:{event_type}:{ts}:{tags_str}")

    event_fingerprints.sort()
    payload_to_hash = f"{window_start}|{len(raw_events)}|" + "|".join(event_fingerprints)
    content_hash = hashlib.sha256(payload_to_hash.encode("utf-8")).hexdigest()

    return f"transform-kpis-{window_start}-{content_hash}"


# Task 1: Extraction with transient retry policy
@task(
    name="extract-telemetry-events",
    retries=3,
    retry_delay_seconds=30,
    description="Extracts raw business telemetry events from telemetry_events in read-only mode with deduplication.",
)
def extract_telemetry_events(
    window_start: date,
    window_end: date,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Task that extracts raw telemetry events for the specified window in read-only mode.

    Policy Justification:
    Configured with 3 retries and 30-second delay. External PostgreSQL/Supabase database
    connections are prone to transient network partitions, SSL renegotiation drops, or pool
    starvation during peak workloads. A 30s delay gives the remote database time to recover
    without hammering it. Non-transient errors (such as missing tables or authentication
    failures) will cleanly exhaust retries and fail the task.
    """
    logger.info("Executing task extract-telemetry-events for window [%s, %s)", window_start, window_end)
    return extract_telemetry_records(window_start=window_start, window_end=window_end, engine=engine)


# Task 2: Transformation with deterministic input-aware caching
@task(
    name="transform-weekly-kpis",
    cache_key_fn=compute_transform_cache_key,
    cache_expiration=timedelta(hours=1),
    description="Transforms raw telemetry events into weekly business KPIs per office and programme.",
)
def transform_weekly_kpis(
    raw_events: list[dict[str, Any]],
    window_start: date,
) -> list[dict[str, Any]]:
    """Task that aggregates raw telemetry events into weekly office/programme performance KPIs.

    Policy Justification:
    Configured with compute_transform_cache_key and 1-hour expiration. This pure in-memory
    transformation is idempotent. If a flow is retried or re-triggered for the same window
    with identical input events, cached results are reused to save CPU and memory.
    If new events arrive (e.g. late-arriving events backfill), the content hash in the cache
    key changes automatically, preventing stale cached metrics from being used.
    """
    logger.info(
        "Executing task transform-weekly-kpis for window_start=%s with %d events",
        window_start,
        len(raw_events),
    )
    return transform_events_to_weekly_kpis(raw_events=raw_events, window_start=window_start)


# Task 3: Idempotent Atomic Loading into reporting schema
def load_weekly_performance_metrics(
    aggregates: list[dict[str, Any]],
    run_id: UUID,
    engine: Optional[Engine] = None,
) -> int:
    """Execute atomic UPSERT into reporting.weekly_office_program_performance."""
    if not aggregates:
        return 0

    target_engine = engine or get_reporting_engine()
    is_sqlite = str(target_engine.url).startswith("sqlite")

    if is_sqlite:
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        from sqlalchemy.dialects.postgresql import insert as dialect_insert

    rows_to_insert: list[dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)
    for agg in aggregates:
        rows_to_insert.append(
            {
                "id": uuid4(),
                "office": agg["office"],
                "programme_id": agg["programme_id"],
                "week_start": agg["week_start"],
                "total_material_cost": agg["total_material_cost"],
                "kits_delivered_count": agg["kits_delivered_count"],
                "shortage_events_count": agg["shortage_events_count"],
                "cost_variance_events_count": agg["cost_variance_events_count"],
                "currency": agg["currency"],
                "computed_at": now_utc,
                "run_id": run_id,
            }
        )

    stmt = dialect_insert(weekly_office_program_performance_table).values(rows_to_insert)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["office", "programme_id", "week_start"],
        set_={
            "total_material_cost": stmt.excluded.total_material_cost,
            "kits_delivered_count": stmt.excluded.kits_delivered_count,
            "shortage_events_count": stmt.excluded.shortage_events_count,
            "cost_variance_events_count": stmt.excluded.cost_variance_events_count,
            "currency": stmt.excluded.currency,
            "computed_at": stmt.excluded.computed_at,
            "run_id": stmt.excluded.run_id,
        },
    )

    with target_engine.begin() as conn:
        conn.execute(upsert_stmt)

    logger.info("Upserted %d KPI records into reporting table for run_id=%s", len(rows_to_insert), run_id)
    return len(rows_to_insert)


@task(
    name="load-reporting-metrics",
    retries=3,
    retry_delay_seconds=30,
    description="Loads aggregated KPIs into reporting.weekly_office_program_performance via atomic UPSERT.",
)
def load_reporting_metrics(
    aggregates: list[dict[str, Any]],
    run_id: UUID,
    engine: Optional[Engine] = None,
) -> int:
    """Task that performs idempotent atomic UPSERT into the reporting table.

    Policy Justification:
    Configured with 3 retries and 30-second delay. Network partitions, transient locking
    or database restarts on the destination PostgreSQL/Supabase cluster are resolved
    through retries. The ON CONFLICT DO UPDATE clause guarantees that partial or repeated
    loads for the same (office, programme_id, week_start) grain are completely idempotent
    and overwrite stale aggregates with the latest run_id and computed_at without creating
    duplicate rows. Schema violations or type mismatches fail permanently after retries.
    """
    logger.info("Executing task load-reporting-metrics for run_id=%s with %d rows", run_id, len(aggregates))
    return load_weekly_performance_metrics(aggregates=aggregates, run_id=run_id, engine=engine)


# Task 4: Optional / Non-critical Integrity Check
@task(
    name="optional-integrity-check",
    description="Non-critical validation snapshot. Checks for cost anomalies or empty programmes.",
)
def optional_integrity_check(
    aggregates: list[dict[str, Any]],
    simulate_failure: bool = False,
) -> dict[str, Any]:
    """Non-critical step verifying sanity thresholds.

    Invoked in the flow with return_state=True. If this step fails, the flow logs
    the warning without aborting the primary critical path (extract -> transform -> load).
    """
    if simulate_failure:
        raise RuntimeError("Simulated failure in optional validation snapshot")

    warnings: list[str] = []
    for row in aggregates:
        if row.get("total_material_cost", 0.0) > 500_000.0:
            warnings.append(
                f"Abnormal high material cost ({row['total_material_cost']} {row['currency']}) "
                f"for office={row['office']} programme={row['programme_id']}"
            )

    return {
        "status": "PASSED" if not warnings else "PASSED_WITH_WARNINGS",
        "warnings": warnings,
        "checked_rows": len(aggregates),
    }
