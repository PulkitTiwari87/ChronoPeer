"""Shared fixtures: a fresh app and temporary database per test, plus small helpers."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app

INV = {"X-Role": "investigator", "X-Actor": "Alex"}
REV = {"X-Role": "reviewer", "X-Actor": "Sam"}

# Illustrative records, not events from the real dataset.
SAMPLE_CSV = (
    "timestamp,event_type,description,source,artifact_id\n"
    "2024-01-15T09:02:00Z,LOGIN,Successful login,Windows Log,EV001\n"
    "2024-01-15T09:15:00Z,USB,USB device connected,USB Artifact,EV002\n"
    "2024-01-15T09:19:00Z,FILE_ACCESS,Document accessed,File System,EV003\n"
    "2024-01-15T09:35:00Z,USB,USB device disconnected,USB Artifact,EV004\n"
)
HEADER = "timestamp,event_type,description,source,artifact_id\n"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        db_path=tmp_path / "test.db",
        storage_dir=tmp_path / "storage",
        reports_dir=tmp_path / "reports",
        max_upload_bytes=100_000,
        seed_demo=False,
        frontend_dir=tmp_path / "no-frontend",
    )
    with TestClient(create_app(settings)) as c:
        c.settings = settings
        yield c


def make_case(client, title="Test case", **extra):
    r = client.post("/api/cases", json={"title": title, **extra}, headers=INV)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def upload(client, case_id, content, name="evidence.csv", tz="", path="evidence", headers=INV):
    data = content.encode() if isinstance(content, str) else content
    return client.post(
        f"/api/cases/{case_id}/{path}",
        files={"file": (name, data, "application/octet-stream")},
        data={"assume_timezone": tz},
        headers=headers,
    )


def event_ids(client, case_id):
    events = client.get(f"/api/cases/{case_id}/timeline").json()["events"]
    return {e["artifact_reference"]: e["id"] for e in events}


def refs(client, case_id, **params):
    return [e["artifact_reference"] for e in client.get(f"/api/cases/{case_id}/timeline", params=params).json()["events"]]


@pytest.fixture
def case(client):
    cid = make_case(client)
    assert upload(client, cid, SAMPLE_CSV).status_code == 201
    return cid


def make_inference(client, case_id, refs_=("EV002", "EV004"), **over):
    ids = event_ids(client, case_id)
    body = {
        "title": "USB device used around the document access",
        "explanation": "A USB device was connected and removed around the time a document was accessed.",
        "reasoning": "EV002 and EV004 bracket the file access EV003.",
        "confidence": 3,
        "event_ids": [ids[r] for r in refs_],
        **over,
    }
    r = client.post(f"/api/cases/{case_id}/inferences", json=body, headers=INV)
    assert r.status_code == 201, r.text
    return r.json()
