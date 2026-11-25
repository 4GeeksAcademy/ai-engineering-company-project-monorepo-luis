"""Prefect tasks for the business performance pipeline.

Implements extraction, caching transformation, and resilient retry policies.
Adheres strictly to the architectural contract in data/pipelines/PIPELINE_DESIGN.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from typing import Any, Optional

from prefect import task
from sqlalchemy import Engine

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
