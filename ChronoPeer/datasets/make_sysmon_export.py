#!/usr/bin/env python3
"""Convert the Sysmon timeline built by build_timeline.py into ChronoPeer's import format.

Input : datasets/sample_exports/source/timeline.csv      (id, source, record_id, eid, type, event_utc, ..., summary)
        datasets/sample_exports/source/evidence_log.csv  (label, file, bytes, sha256, hash_check)
Output: datasets/sample_exports/sysmon_iewin7_export.csv (timestamp, event_type, description, source, artifact_id)

Sysmon's UtcTime is UTC by definition, so 'Z' is appended and the timezone status is KNOWN (not assumed).
Run from the ChronoPeer folder:   python -I datasets/make_sysmon_export.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sample_exports" / "source"
OUT = HERE / "sample_exports" / "sysmon_iewin7_export.csv"
COLUMNS = ["timestamp", "event_type", "description", "source", "artifact_id"]


def main() -> None:
    with open(SRC / "evidence_log.csv", newline="", encoding="utf8") as f:
        files = {r["label"]: r["file"].split("/")[-1] for r in csv.DictReader(f)}
    rows = []
    with open(SRC / "timeline.csv", newline="", encoding="utf8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "timestamp": r["event_utc"].replace(" ", "T") + "Z",
                    "event_type": r["type"].upper().replace(" ", "_"),
                    "description": f"[{r['id']}] {r['summary']}",
                    "source": f"Sysmon: {files[r['source']]}",
                    "artifact_id": f"{r['source']}-{r['record_id']}",
                }
            )
    with open(OUT, "w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator=chr(10))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT.name}: {len(rows)} events")


if __name__ == "__main__":
    main()
