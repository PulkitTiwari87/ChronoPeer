"""Evidence preview and import. Original files are stored untouched under a hash-based name."""
from pathlib import Path

from sqlalchemy import func, select

from ..models import Evidence, TimelineEvent
from . import Conflict, ValidationFailed, audit
from .evidence_parser import parse
from .file_validator import validate_upload
from .hashing import sha256_bytes
from .timestamp_normalizer import normalize, parse_assumed_tz
from .timeline_builder import event_out


def _existing_keys(db, case_id: int) -> set:
    rows = db.execute(
        select(TimelineEvent.artifact_reference, TimelineEvent.event_time_original, TimelineEvent.description).where(
            TimelineEvent.case_id == case_id
        )
    )
    return {tuple(r) for r in rows}


def _normalise(records, tz, seen: set):
    kept, duplicates, status_counts = [], 0, {}
    for r in records:
        key = (r.artifact_id, r.timestamp, r.description)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        n = normalize(r.timestamp, tz)
        status_counts[n.status] = status_counts.get(n.status, 0) + 1
        kept.append((r, n))
    return kept, duplicates, status_counts


def _summary(up, digest, parsed, kept, duplicates, status_counts) -> dict:
    return {
        "filename": up.filename,
        "file_type": up.file_type,
        "size_bytes": up.size,
        "sha256": digest,
        "total_rows": parsed.total_rows,
        "valid_records": len(kept),
        "duplicate_records_skipped": duplicates,
        "malformed": parsed.malformed[:100],
        "malformed_count": len(parsed.malformed),
        "by_timezone_status": status_counts,
    }


def preview(db, settings, case, filename, data: bytes, assume_timezone=None) -> dict:
    """Validate, hash and parse without storing anything."""
    up = validate_upload(filename, data, settings.max_upload_bytes)
    digest = sha256_bytes(data)
    parsed = parse(up.text, up.file_type)
    kept, duplicates, counts = _normalise(parsed.records, parse_assumed_tz(assume_timezone), _existing_keys(db, case.id))
    out = _summary(up, digest, parsed, kept, duplicates, counts)
    out["already_imported"] = bool(
        db.scalar(select(Evidence.id).where(Evidence.case_id == case.id, Evidence.sha256 == digest))
    )
    out["sample"] = [
        {
            "row": r.row,
            "timestamp": r.timestamp,
            "utc": n.utc.isoformat(timespec="milliseconds") + "Z" if n.utc else None,
            "timezone_status": n.status,
            "event_type": r.event_type,
            "description": r.description,
            "artifact_id": r.artifact_id,
        }
        for r, n in kept[:10]
    ]
    return out


def import_evidence(db, settings, actor, case, filename, data: bytes, assume_timezone=None) -> dict:
    up = validate_upload(filename, data, settings.max_upload_bytes)
    digest = sha256_bytes(data)
    if db.scalar(select(Evidence.id).where(Evidence.case_id == case.id, Evidence.sha256 == digest)):
        raise Conflict("This exact file (same SHA-256) has already been imported into this case")
    parsed = parse(up.text, up.file_type)
    kept, duplicates, counts = _normalise(parsed.records, parse_assumed_tz(assume_timezone), _existing_keys(db, case.id))
    if not kept:
        raise ValidationFailed("No valid records found: nothing was imported")

    stored = Path(settings.storage_dir) / str(case.id) / f"{digest}.{up.file_type.lower()}"
    stored.parent.mkdir(parents=True, exist_ok=True)
    if not stored.exists():
        stored.write_bytes(data)  # original bytes, never modified afterwards

    ev = Evidence(
        case_id=case.id,
        filename=up.filename,
        file_path=str(stored),
        sha256=digest,
        file_type=up.file_type,
        record_count=len(kept),
    )
    db.add(ev)
    db.flush()
    base = db.scalar(select(func.count(TimelineEvent.id)).where(TimelineEvent.case_id == case.id)) or 0
    for offset, (r, n) in enumerate(kept):
        db.add(
            TimelineEvent(
                case_id=case.id,
                evidence_id=ev.id,
                event_time_original=r.timestamp,
                event_time_utc=n.utc,
                timezone_status=n.status,
                event_type=r.event_type,
                source_label=r.source,
                description=r.description,
                artifact_reference=r.artifact_id,
                import_order=base + offset,
            )
        )
    audit.record(
        db, actor, case.id, "evidence_imported", ev.id,
        f"Imported {up.filename} ({up.file_type}, {len(kept)} events, sha256 {digest[:12]}...)",
    )
    db.flush()
    out = _summary(up, digest, parsed, kept, duplicates, counts)
    out["evidence_id"] = ev.id
    return out


def evidence_out(ev) -> dict:
    return {
        "id": ev.id,
        "case_id": ev.case_id,
        "filename": ev.filename,
        "file_type": ev.file_type,
        "sha256": ev.sha256,
        "record_count": ev.record_count,
        "imported_at": ev.imported_at.isoformat(timespec="seconds") + "Z",
    }
