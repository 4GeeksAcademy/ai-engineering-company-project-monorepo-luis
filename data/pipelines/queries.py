"""Data extraction and analytical query helpers for the business performance pipeline.

Queries telemetry_events in read-only mode and performs deduplication by eventId.
Queries reporting tables for business stakeholders (Laura & Elena).
Adheres strictly to the architectural contract in data/pipelines/PIPELINE_DESIGN.md.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Engine, desc, func, select, text

from data.pipelines.db import get_reporting_engine
from data.pipelines.models import weekly_office_program_performance_table
from services.api.telemetry_storage import (
    get_telemetry_engine,
    telemetry_events_table,
)

logger = logging.getLogger(__name__)

MANDATORY_PIPELINE_EVENT_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_threshold_triggered",
    "kit_cost_variance_detected",
)

OFFICE_CURRENCY_MAPPING = {
    "valencia": "EUR",
    "miami": "USD",
}


def extract_telemetry_records(
    window_start: date,
    window_end: date,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Extract raw telemetry events for the given weekly window in read-only mode.

    - Window: [window_start 00:00:00 UTC, window_end 00:00:00 UTC)
    - Filter: event_type IN MANDATORY_PIPELINE_EVENT_TYPES
    - Deduplication: Deduplicates by envelope 'eventId' (or 'event_id' or UUID id)
      so retransmitted/retried events do not inflate business KPIs.
    """
    target_engine = engine or get_telemetry_engine()

    start_dt = datetime.combine(window_start, time.min).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(window_end, time.min).replace(tzinfo=timezone.utc)

    query = (
        select(
            telemetry_events_table.c.id,
            telemetry_events_table.c.timestamp,
            telemetry_events_table.c.event_type,
            telemetry_events_table.c.tags,
        )
        .where(
            telemetry_events_table.c.timestamp >= start_dt,
            telemetry_events_table.c.timestamp < end_dt,
            telemetry_events_table.c.event_type.in_(MANDATORY_PIPELINE_EVENT_TYPES),
        )
        .order_by(telemetry_events_table.c.timestamp.asc())
    )

    extracted_rows: list[dict[str, Any]] = []
    seen_dedup_keys: set[str] = set()

    with target_engine.connect() as conn:
        result = conn.execute(query)
        for row in result.mappings():
            raw_tags = row["tags"]
            if isinstance(raw_tags, str):
                try:
                    tags = json.loads(raw_tags)
                except Exception:
                    tags = {}
            elif isinstance(raw_tags, dict):
                tags = raw_tags
            else:
                tags = {}

            # Deduplication key from envelope eventId or record UUID
            envelope_event_id = tags.get("eventId") or tags.get("event_id")
            record_id_str = str(row["id"]) if row["id"] else ""
            dedup_key = envelope_event_id or record_id_str

            if dedup_key in seen_dedup_keys:
                logger.debug(
                    "Skipping duplicate telemetry event in extraction: dedup_key=%s",
                    dedup_key,
                )
                continue

            seen_dedup_keys.add(dedup_key)

            extracted_rows.append(
                {
                    "id": record_id_str,
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "tags": tags,
                    "dedup_key": dedup_key,
                }
            )

    logger.info(
        "Extracted %d deduplicated telemetry events for window [%s, %s)",
        len(extracted_rows),
        window_start,
        window_end,
    )
    return extracted_rows


def transform_events_to_weekly_kpis(
    raw_events: list[dict[str, Any]],
    window_start: date,
) -> list[dict[str, Any]]:
    """Transform and aggregate raw telemetry events into weekly business KPIs.

    Granularity: (office, programme_id, week_start)
    Rules:
    - Office must be 'valencia' or 'miami'.
    - Currency strictly isolated (EUR for Valencia, USD for Miami).
    - total_material_cost: sum of total_cost if present, else unit_cost * quantity.
      Validates non-negative cost and avoids double-counting.
    - kits_delivered_count: count of unique outbound_order_created events.
    - shortage_events_count: count of unique stock_threshold_triggered events.
    - cost_variance_events_count: count of unique kit_cost_variance_detected events.
    """
    aggregates: dict[tuple[str, str, date], dict[str, Any]] = {}

    for event in raw_events:
        event_type = event.get("event_type")
        tags = event.get("tags", {})

        raw_office = str(tags.get("office", "")).strip().lower()
        if raw_office not in OFFICE_CURRENCY_MAPPING:
            logger.debug("Skipping event with unapproved office: %s", raw_office)
            continue

        office = raw_office
        expected_currency = OFFICE_CURRENCY_MAPPING[office]

        programme_id = str(tags.get("programme_id", "")).strip()
        if not programme_id:
            logger.debug("Skipping event without programme_id: event_id=%s", event.get("id"))
            continue

        grain_key = (office, programme_id, window_start)

        if grain_key not in aggregates:
            aggregates[grain_key] = {
                "office": office,
                "programme_id": programme_id,
                "week_start": window_start,
                "total_material_cost": 0.0,
                "kits_delivered_count": 0,
                "shortage_events_count": 0,
                "cost_variance_events_count": 0,
                "currency": expected_currency,
            }

        entry = aggregates[grain_key]

        if event_type == "inbound_order_created":
            total_cost_prop = tags.get("total_cost")
            if total_cost_prop is not None:
                try:
                    line_cost = float(total_cost_prop)
                except (ValueError, TypeError):
                    line_cost = 0.0
            else:
                try:
                    unit_cost = float(tags.get("unit_cost", 0.0))
                    qty = int(tags.get("quantity", 1))
                    line_cost = unit_cost * qty
                except (ValueError, TypeError):
                    line_cost = 0.0

            if line_cost > 0:
                entry["total_material_cost"] += line_cost

        elif event_type == "outbound_order_created":
            entry["kits_delivered_count"] += 1

        elif event_type == "stock_threshold_triggered":
            entry["shortage_events_count"] += 1

        elif event_type == "kit_cost_variance_detected":
            entry["cost_variance_events_count"] += 1

    result_list: list[dict[str, Any]] = []
    for item in aggregates.values():
        item["total_material_cost"] = round(item["total_material_cost"], 2)
        result_list.append(item)

    result_list.sort(key=lambda x: (x["office"], x["programme_id"]))
    logger.info(
        "Transformed %d raw events into %d aggregated weekly KPI rows",
        len(raw_events),
        len(result_list),
    )
    return result_list


def get_weekly_kpis_for_reporting(
    week_start: Optional[date] = None,
    office: Optional[str] = None,
    programme_id: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> tuple[Optional[date], list[dict[str, Any]]]:
    """Query reporting.weekly_office_program_performance for the requested or latest week.

    Returns (effective_week_start, list_of_entry_dicts).
    """
    target_engine = engine or get_reporting_engine()

    with target_engine.connect() as conn:
        effective_week = week_start

        # If no week_start was requested, query for the latest computed week
        if effective_week is None:
            max_week_query = select(func.max(weekly_office_program_performance_table.c.week_start))
            effective_week = conn.execute(max_week_query).scalar_one_or_none()

        if effective_week is None:
            return None, []

        query = select(weekly_office_program_performance_table).where(
            weekly_office_program_performance_table.c.week_start == effective_week
        )

        if office:
            query = query.where(weekly_office_program_performance_table.c.office == office.lower())
        if programme_id:
            query = query.where(weekly_office_program_performance_table.c.programme_id == programme_id)

        query = query.order_by(
            weekly_office_program_performance_table.c.office.asc(),
            weekly_office_program_performance_table.c.programme_id.asc(),
        )

        rows = conn.execute(query).mappings().all()

        entries: list[dict[str, Any]] = []
        for r in rows:
            entries.append(
                {
                    "office": r["office"],
                    "programme_id": r["programme_id"],
                    "total_material_cost": float(r["total_material_cost"]),
                    "kits_delivered_count": int(r["kits_delivered_count"]),
                    "shortage_events_count": int(r["shortage_events_count"]),
                    "cost_variance_events_count": int(r["cost_variance_events_count"]),
                    "currency": r["currency"],
                }
            )

        return effective_week, entries
