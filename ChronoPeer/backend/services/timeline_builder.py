"""Deterministic chronological ordering of timeline events.

Same input always yields the same order. Groups: 0 = UTC known/assumed (by UTC time), 1 = timezone
unknown (by wall-clock value, so events from one clock still order among themselves), 2 = missing or
invalid timestamp (last). Ties break on natural artifact id, then import order, then id.
"""
import re
from datetime import datetime

from sqlalchemy import select

from ..models import TimelineEvent
from .timestamp_normalizer import normalize

_DIGITS = re.compile(r"([0-9]+)")


def natural_key(text):
    return [int(p) if p.isdigit() else p.lower() for p in _DIGITS.split(text or "")]


def group_of(e) -> int:
    if e.timezone_status in ("known", "assumed") and e.event_time_utc is not None:
        return 0
    if e.timezone_status == "unknown":
        return 1
    return 2


def sort_key(e):
    group = group_of(e)
    if group == 0:
        when = e.event_time_utc
    elif group == 1:
        when = normalize(e.event_time_original).wall or datetime.min
    else:
        when = datetime.min
    return (group, when, natural_key(e.artifact_reference), e.import_order, e.id)


def ordered_events(db, case_id: int, descending: bool = False) -> list:
    events = sorted(db.scalars(select(TimelineEvent).where(TimelineEvent.case_id == case_id)).all(), key=sort_key)
    if descending:
        placed = [e for e in events if group_of(e) < 2]
        return placed[::-1] + [e for e in events if group_of(e) == 2]
    return events


def event_out(e) -> dict:
    flags = {
        "unknown": "Timezone unknown: not converted to UTC",
        "assumed": "Timezone assumed at import",
        "invalid": "Timestamp could not be parsed",
        "missing": "Timestamp missing",
    }
    return {
        "id": e.id,
        "evidence_id": e.evidence_id,
        "evidence_filename": e.evidence.filename if e.evidence else None,
        "event_time_original": e.event_time_original,
        "event_time_utc": e.event_time_utc.isoformat(timespec="milliseconds") + "Z" if e.event_time_utc else None,
        "timezone_status": e.timezone_status,
        "event_type": e.event_type,
        "source": e.source_label,
        "description": e.description,
        "artifact_reference": e.artifact_reference,
        "flag": flags.get(e.timezone_status),
    }


def timeline_summary(events: list) -> dict:
    counts = {"known": 0, "assumed": 0, "unknown": 0, "invalid": 0, "missing": 0}
    for e in events:
        counts[e.timezone_status] = counts.get(e.timezone_status, 0) + 1
    return {"total": len(events), "by_timezone_status": counts}
