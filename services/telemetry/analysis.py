"""Vectorized telemetry analysis pipeline using Pandas.

Adheres strictly to the operational/technical report specifications:
1. SQL push-down filters for temporal window and event_type.
2. Conversion of timestamps to UTC datetime prior to grouping.
3. Purely vectorized Pandas transformations (no iterative loops).
4. No PII, secrets, or raw text exposed in metric outputs.
5. JSON-serializable structures with safe denominator-zero handling.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from sqlalchemy import Engine, select

from services.api.telemetry_storage import (
    get_telemetry_engine,
    telemetry_events_table,
)

# Canonical list of error event types as mapped in telemetry ingestion
ERROR_EVENT_TYPES = (
    "api_request_failed",
    "frontend_uncaught_error",
    "auth_login_failed",
    "direct_stock_edit_rejected",
    "inventory_order_validation_failed",
)


def validate_report_dates(start_date: datetime, end_date: datetime) -> tuple[datetime, datetime]:
    """Validate and normalize report boundary datetimes to UTC.

    Raises:
        TypeError: If dates are not datetime instances.
        ValueError: If dates are naive (no timezone) or start_date >= end_date.
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise TypeError("start_date and end_date must be datetime instances")

    if start_date.tzinfo is None or start_date.tzinfo.utcoffset(start_date) is None:
        raise ValueError("start_date must be timezone-aware (UTC)")

    if end_date.tzinfo is None or end_date.tzinfo.utcoffset(end_date) is None:
        raise ValueError("end_date must be timezone-aware (UTC)")

    start_utc = start_date.astimezone(timezone.utc)
    end_utc = end_date.astimezone(timezone.utc)

    if start_utc >= end_utc:
        raise ValueError("start_date must be strictly before end_date")

    return start_utc, end_utc


def _clean_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure all record values are clean Python primitives serializable to JSON."""
    cleaned = []
    for item in records:
        cleaned_item = {}
        for k, v in item.items():
            if v is None or pd.isna(v):
                cleaned_item[k] = None
            elif isinstance(v, (np.integer, int)):
                cleaned_item[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                if math.isnan(v) or math.isinf(v):
                    cleaned_item[k] = None
                else:
                    cleaned_item[k] = float(v)
            else:
                cleaned_item[k] = v
        cleaned.append(cleaned_item)
    return cleaned


def get_events_per_day(
    start_date: datetime,
    end_date: datetime,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Metric 1: Volume of events grouped by UTC date and event_type.

    Order: SQL load -> Pandas UTC conversion -> Groupby -> Aggregate count -> Serve.
    """
    start_utc, end_utc = validate_report_dates(start_date, end_date)
    target_engine = engine or get_telemetry_engine()

    stmt = (
        select(
            telemetry_events_table.c.timestamp,
            telemetry_events_table.c.event_type,
        )
        .where(telemetry_events_table.c.timestamp >= start_utc)
        .where(telemetry_events_table.c.timestamp < end_utc)
    )

    with target_engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby(["date", "event_type"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(by=["date", "event_type"])
    )

    return _clean_records(grouped.to_dict(orient="records"))


def get_error_rate_by_type(
    start_date: datetime,
    end_date: datetime,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Metric 2: Error rate grouped by event_type.

    Reports errors, total occurrences, and the calculated error rate.
    Handles zero denominator safely with rate=None.
    """
    start_utc, end_utc = validate_report_dates(start_date, end_date)
    target_engine = engine or get_telemetry_engine()

    stmt = (
        select(
            telemetry_events_table.c.timestamp,
            telemetry_events_table.c.event_type,
            telemetry_events_table.c.level,
        )
        .where(telemetry_events_table.c.timestamp >= start_utc)
        .where(telemetry_events_table.c.timestamp < end_utc)
    )

    with target_engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    # An event is an error if level=='error' or event_type in canonical error event types
    is_error = (df["level"] == "error") | (df["event_type"].isin(ERROR_EVENT_TYPES))
    df["is_error"] = is_error.astype(int)

    grouped = (
        df.groupby("event_type", as_index=False)
        .agg(
            errors=("is_error", "sum"),
            total=("is_error", "count"),
        )
        .sort_values(by="event_type")
    )

    grouped["rate"] = np.where(
        grouped["total"] > 0,
        (grouped["errors"] / grouped["total"]).round(4),
        None,
    )
    grouped["rate"] = grouped["rate"].where(pd.notnull(grouped["rate"]), None)

    return _clean_records(grouped.to_dict(orient="records"))


def _extract_tag_route_group(tags_val: Any) -> Optional[str]:
    """Safely extract route_group string from dict or JSON string."""
    if isinstance(tags_val, dict):
        rg = tags_val.get("route_group")
        return str(rg).strip() if rg else None
    if isinstance(tags_val, str) and tags_val.strip():
        try:
            parsed = json.loads(tags_val)
            if isinstance(parsed, dict):
                rg = parsed.get("route_group")
                return str(rg).strip() if rg else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def get_latency_by_route_group(
    start_date: datetime,
    end_date: datetime,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Metric 3: Latency (mean duration in ms) grouped by UTC date and route_group.

    Filters SQL strictly on event_type='api_latency_recorded'.
    """
    start_utc, end_utc = validate_report_dates(start_date, end_date)
    target_engine = engine or get_telemetry_engine()

    stmt = (
        select(
            telemetry_events_table.c.timestamp,
            telemetry_events_table.c.value,
            telemetry_events_table.c.tags,
        )
        .where(telemetry_events_table.c.timestamp >= start_utc)
        .where(telemetry_events_table.c.timestamp < end_utc)
        .where(telemetry_events_table.c.event_type == "api_latency_recorded")
    )

    with target_engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    # Extract route_group from tags
    df["route_group"] = df["tags"].apply(_extract_tag_route_group)

    # Use value column for duration_ms or fallback to tags['duration_ms']
    df["duration_ms"] = pd.to_numeric(df["value"], errors="coerce")

    # Filter out null route_group or duration_ms
    valid = df.dropna(subset=["route_group", "duration_ms"])
    valid = valid[valid["route_group"] != ""]
    valid = valid[valid["duration_ms"] >= 0]

    if valid.empty:
        return []

    grouped = (
        valid.groupby(["date", "route_group"], as_index=False)
        .agg(mean_duration_ms=("duration_ms", "mean"))
        .sort_values(by=["date", "route_group"])
    )
    grouped["mean_duration_ms"] = grouped["mean_duration_ms"].round(2)

    return _clean_records(grouped.to_dict(orient="records"))


def get_auth_failure_rate(
    start_date: datetime,
    end_date: datetime,
    engine: Optional[Engine] = None,
) -> list[dict[str, Any]]:
    """Metric 4 (Additional): Daily auth failure rate.

    Single SQL query with IN ('auth_login_failed', 'auth_login_succeeded').
    Returns date, failures, successes, total, and failure_rate (or None if total==0).
    """
    start_utc, end_utc = validate_report_dates(start_date, end_date)
    target_engine = engine or get_telemetry_engine()

    auth_types = ["auth_login_failed", "auth_login_succeeded"]

    stmt = (
        select(
            telemetry_events_table.c.timestamp,
            telemetry_events_table.c.event_type,
        )
        .where(telemetry_events_table.c.timestamp >= start_utc)
        .where(telemetry_events_table.c.timestamp < end_utc)
        .where(telemetry_events_table.c.event_type.in_(auth_types))
    )

    with target_engine.connect() as conn:
        df = pd.read_sql(stmt, conn)

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    df["is_failure"] = (df["event_type"] == "auth_login_failed").astype(int)
    df["is_success"] = (df["event_type"] == "auth_login_succeeded").astype(int)

    grouped = (
        df.groupby("date", as_index=False)
        .agg(
            failures=("is_failure", "sum"),
            successes=("is_success", "sum"),
        )
        .sort_values(by="date")
    )

    grouped["total"] = grouped["failures"] + grouped["successes"]
    grouped["failure_rate"] = np.where(
        grouped["total"] > 0,
        (grouped["failures"] / grouped["total"]).round(4),
        None,
    )
    grouped["failure_rate"] = grouped["failure_rate"].where(pd.notnull(grouped["failure_rate"]), None)

    return _clean_records(grouped.to_dict(orient="records"))


def build_telemetry_report(
    start_date: datetime,
    end_date: datetime,
    engine: Optional[Engine] = None,
) -> dict[str, Any]:
    """Aggregate all technical metrics for the resolved temporal window.

    Output format:
    {
      "period": {"from": "...", "to": "..."},
      "metrics": {
        "events_per_day": [...],
        "error_rate_by_type": [...],
        "latency_by_route_group": [...],
        "auth_failure_rate": [...]
      }
    }
    """
    start_utc, end_utc = validate_report_dates(start_date, end_date)

    return {
        "period": {
            "from": start_utc.isoformat().replace("+00:00", "Z"),
            "to": end_utc.isoformat().replace("+00:00", "Z"),
        },
        "metrics": {
            "events_per_day": get_events_per_day(start_utc, end_utc, engine=engine),
            "error_rate_by_type": get_error_rate_by_type(start_utc, end_utc, engine=engine),
            "latency_by_route_group": get_latency_by_route_group(start_utc, end_utc, engine=engine),
            "auth_failure_rate": get_auth_failure_rate(start_utc, end_utc, engine=engine),
        },
    }
