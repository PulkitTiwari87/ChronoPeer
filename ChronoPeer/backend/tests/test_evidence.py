import hashlib
import json

import pytest

from backend.services import ValidationFailed
from backend.services.file_validator import safe_filename

from .conftest import HEADER, INV, REV, SAMPLE_CSV, make_case, refs, upload


def test_valid_csv_import(client):
    cid = make_case(client)
    r = upload(client, cid, SAMPLE_CSV)
    assert r.status_code == 201
    body = r.json()
    assert body["valid_records"] == 4 and body["malformed_count"] == 0
    assert body["sha256"] == hashlib.sha256(SAMPLE_CSV.encode()).hexdigest()
    assert body["by_timezone_status"] == {"known": 4}
    stored = client.settings.storage_dir / str(cid) / f"{body['sha256']}.csv"
    assert stored.read_bytes() == SAMPLE_CSV.encode()  # the original file is preserved byte for byte


def test_valid_json_import_list_and_wrapped(client):
    rows = [{"timestamp": "2024-01-15T09:02:00Z", "event_type": "LOGIN", "description": "Login", "source": "Log", "artifact_id": "J1"}]
    cid = make_case(client)
    assert upload(client, cid, json.dumps(rows), name="a.json").json()["valid_records"] == 1
    wrapped = {"events": [dict(rows[0], artifact_id="J2")]}
    r = upload(client, cid, json.dumps(wrapped), name="b.json")
    assert r.status_code == 201 and r.json()["file_type"] == "JSON"
    assert refs(client, cid) == ["J1", "J2"]


@pytest.mark.parametrize(
    "name,content",
    [
        ("evil.exe", b"timestamp,event_type,description,source\n"),
        ("empty.csv", b""),
        ("binary.csv", bytes([0, 1, 2, 3, 44, 44])),
        ("notjson.json", b"timestamp,event_type"),
        ("broken.json", b"[{"),
        ("latin.csv", HEADER.encode() + bytes([0xFF, 0xFE, 44]) + b"x\n"),
    ],
)
def test_invalid_files_are_rejected(client, name, content):
    cid = make_case(client)
    assert upload(client, cid, content, name=name).status_code == 422
    assert client.get(f"/api/cases/{cid}/evidence").json() == []  # nothing was stored


def test_unsafe_filenames_are_rejected():
    for bad in ("../evil.csv", "a/b.csv", chr(92).join(["a", "b.csv"]), "a..b.csv", "", "x" * 300 + ".csv"):
        with pytest.raises(ValidationFailed):
            safe_filename(bad)


def test_oversized_upload_is_rejected(client):
    cid = make_case(client)
    big = HEADER + "2024-01-15T09:02:00Z,LOGIN,x,Log,E1\n" * 4000
    assert len(big) > 100_000
    assert upload(client, cid, big).status_code == 413


def test_missing_required_columns(client):
    cid = make_case(client)
    r = upload(client, cid, "timestamp,description\n2024-01-15T09:02:00Z,x\n")
    assert r.status_code == 422 and "event_type" in r.json()["detail"]


def test_malformed_rows_are_reported_and_valid_rows_imported(client):
    cid = make_case(client)
    text = SAMPLE_CSV + "2024-01-15T09:40:00Z,USB,,USB Artifact,EV009\n2024-01-15T09:41:00Z,,No type,USB Artifact,EV010\n"
    body = upload(client, cid, text).json()
    assert body["valid_records"] == 4 and body["malformed_count"] == 2
    assert {m["row"] for m in body["malformed"]} == {5, 6}
    assert "missing description" in body["malformed"][0]["reason"]


def test_missing_timestamp_is_kept_flagged_and_last(client):
    cid = make_case(client)
    text = HEADER + ",LOGIN,No time recorded,Log,EV001\n2024-01-15T09:15:00Z,USB,Has time,USB,EV002\n"
    assert upload(client, cid, text).status_code == 201
    events = client.get(f"/api/cases/{cid}/timeline").json()["events"]
    assert [e["artifact_reference"] for e in events] == ["EV002", "EV001"]
    assert events[1]["timezone_status"] == "missing" and events[1]["event_time_utc"] is None and events[1]["flag"]


def test_duplicate_events_are_skipped_within_and_across_files(client):
    cid = make_case(client)
    row = "2024-01-15T09:02:00Z,LOGIN,Successful login,Windows Log,EV001\n"
    first = upload(client, cid, HEADER + row + row, name="one.csv").json()
    assert first["valid_records"] == 1 and first["duplicate_records_skipped"] == 1
    second = upload(client, cid, HEADER + row + "2024-01-15T10:00:00Z,USB,Plugged,USB,EV002\n", name="two.csv").json()
    assert second["valid_records"] == 1 and second["duplicate_records_skipped"] == 1
    assert refs(client, cid) == ["EV001", "EV002"]


def test_importing_the_same_file_twice_is_a_conflict(client):
    cid = make_case(client)
    assert upload(client, cid, SAMPLE_CSV).status_code == 201
    assert upload(client, cid, SAMPLE_CSV, name="renamed.csv").status_code == 409


def test_preview_validates_but_stores_nothing(client):
    cid = make_case(client)
    r = upload(client, cid, SAMPLE_CSV, path="evidence/preview")
    assert r.status_code == 200
    body = r.json()
    assert body["valid_records"] == 4 and len(body["sample"]) == 4 and body["already_imported"] is False
    assert client.get(f"/api/cases/{cid}/evidence").json() == []
    assert not (client.settings.storage_dir / str(cid)).exists()


def test_reviewer_mode_cannot_import_evidence(client):
    cid = make_case(client)
    assert upload(client, cid, SAMPLE_CSV, headers=REV).status_code == 403
    assert upload(client, cid, SAMPLE_CSV, headers={"X-Role": "visitor"}).status_code == 400
    assert INV["X-Role"] == "investigator"
