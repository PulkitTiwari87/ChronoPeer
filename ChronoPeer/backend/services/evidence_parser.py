"""Parse normalised CSV/JSON evidence into validated records. Pure functions: no database access."""
import io
import json
from dataclasses import dataclass, field

import pandas as pd

from . import ValidationFailed

REQUIRED_COLUMNS = ("timestamp", "event_type", "description")


@dataclass(frozen=True)
class Record:
    row: int  # 1-based data row
    timestamp: str
    event_type: str
    description: str
    source: str
    artifact_id: str


@dataclass
class ParseResult:
    records: list = field(default_factory=list)
    malformed: list = field(default_factory=list)  # [{"row": n, "reason": "..."}]
    total_rows: int = 0


def _frame(text: str, file_type: str) -> pd.DataFrame:
    try:
        if file_type == "CSV":
            df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        else:
            obj = json.loads(text)
            if isinstance(obj, dict):
                obj = obj.get("events", obj.get("records"))
            if not isinstance(obj, list) or not all(isinstance(r, dict) for r in obj):
                raise ValidationFailed('JSON must be a list of event objects (or {"events": [...]})')
            df = pd.DataFrame(obj)
    except ValidationFailed:
        raise
    except Exception as exc:  # malformed CSV or JSON
        raise ValidationFailed(f"Could not parse the {file_type} file: {exc}") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df.fillna("").astype(str)


def parse(text: str, file_type: str) -> ParseResult:
    df = _frame(text, file_type)
    cols = set(df.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    if "source" not in cols and "artifact_id" not in cols:
        missing.append("source or artifact_id")
    if missing:
        raise ValidationFailed("Missing required column(s): " + ", ".join(missing))

    result = ParseResult(total_rows=len(df))
    for i, row in enumerate(df.to_dict("records"), start=1):
        timestamp = row.get("timestamp", "").strip()
        event_type = row.get("event_type", "").strip()
        description = row.get("description", "").strip()
        source = row.get("source", "").strip()
        artifact_id = row.get("artifact_id", "").strip()
        problems = []
        if not description:
            problems.append("missing description")
        if not event_type:
            problems.append("missing event_type")
        if not source and not artifact_id:
            problems.append("missing source reference (source or artifact_id)")
        if problems:
            result.malformed.append({"row": i, "reason": "; ".join(problems)})
            continue
        # A missing/invalid TIMESTAMP is not malformed: the event is kept and flagged (see timestamp_normalizer).
        result.records.append(Record(i, timestamp, event_type, description, source, artifact_id or f"row-{i}"))
    return result
