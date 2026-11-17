"""The spec's end-to-end acceptance test (section 11) and the demo-seed check."""
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app

from .conftest import INV, REV, SAMPLE_CSV, event_ids, make_case, upload


def test_complete_investigation_is_reproducible_end_to_end(client):
    # 1. Import a forensic evidence file.
    cid = make_case(client, "Acceptance", dataset_name="Illustrative sample", description="End-to-end run")
    imported = upload(client, cid, SAMPLE_CSV)
    assert imported.status_code == 201 and imported.json()["valid_records"] == 4

    # 2. Generate the original timeline.
    timeline = client.get(f"/api/cases/{cid}/timeline").json()
    assert [e["artifact_reference"] for e in timeline["events"]] == ["EV001", "EV002", "EV003", "EV004"]

    # 3. Create an inference.
    ids = event_ids(client, cid)
    created = client.post(
        f"/api/cases/{cid}/inferences",
        json={
            "title": "USB used around the document access",
            "explanation": "A USB device was connected and removed around the document access.",
            "reasoning": "EV002 and EV004 bracket EV003.",
            "confidence": 3,
            "event_ids": [ids["EV002"], ids["EV003"], ids["EV004"]],
        },
        headers=INV,
    )
    assert created.status_code == 201
    inf = created.json()

    # 4. Open the shared peer-review interface (reviewer mode sees the same investigation).
    seen = client.get(f"/api/cases/{cid}/inferences", headers=REV).json()
    assert seen[0]["id"] == inf["id"] and seen[0]["review_state"]["pending_review"] is True

    # 5. Submit a challenge.
    rv = client.post(
        f"/api/inferences/{inf['id']}/reviews",
        json={"reviewer_name": "Sam", "decision": "challenge", "critique": "Times alone do not show use.",
              "alternative_explanation": "Charging only.", "additional_evidence": "File-copy artifacts.", "confidence": 4},
        headers=REV,
    )
    assert rv.status_code == 201

    # 6. Return to investigator mode and see the open challenge.
    summary = client.get(f"/api/cases/{cid}/summary", headers=INV).json()
    assert summary["open_challenges"] == 1 and summary["inferences"]["by_status"] == {"challenged": 1}

    # 7. Revise the inference.
    revised = client.post(
        f"/api/inferences/{inf['id']}/revisions",
        json={"response": "accepted", "peer_review_id": rv.json()["id"], "change_reason": "Use is unproven.",
              "revised_reasoning": "Connection and removal are proven; use is not.", "new_confidence": 2},
        headers=INV,
    )
    assert revised.status_code == 201 and revised.json()["inference"]["status"] == "revised"
    assert client.get(f"/api/inferences/{inf['id']}").json()["original_reasoning"] == "EV002 and EV004 bracket EV003."

    # 8. Generate the final report.
    report = client.get(f"/api/cases/{cid}/report", headers=INV)
    assert report.status_code == 200 and report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF") and len(report.content) > 3000
    assert (client.settings.reports_dir / f"case-{cid}-report.pdf").read_bytes() == report.content
    actions = [a["action_type"] for a in reversed(client.get(f"/api/cases/{cid}/audit").json())]
    assert actions[-1] == "report_generated" and "revision_recorded" in actions


def test_health_reports_whether_storage_is_temporary(client):
    assert client.get("/api/health").json() == {"status": "ok", "ephemeral": False}


def test_report_lists_the_eleven_sections(client, case):
    from backend.services.report_generator import SECTION_TITLES

    assert len(SECTION_TITLES) == 11
    pdf = client.get(f"/api/cases/{case}/report", headers=INV)
    assert pdf.status_code == 200
    missing = [t for t in SECTION_TITLES if t.encode() not in pdf.content]  # each section is a PDF outline entry
    assert missing == []
    assert client.get(f"/api/cases/{case}/report", headers=REV).status_code == 403


def test_demo_seed_replays_the_real_case_without_inventing_anything(tmp_path):
    settings = Settings(
        db_path=tmp_path / "seed.db", storage_dir=tmp_path / "st", reports_dir=tmp_path / "rp",
        seed_demo=True, frontend_dir=tmp_path / "none",
    )
    with TestClient(create_app(settings)) as c:
        case = c.get("/api/cases").json()[0]
        summary = c.get(f"/api/cases/{case['id']}/summary").json()
        assert case["case_code"] == "DF-PBL-040"
        assert summary["timeline"]["total"] == 25 and summary["timeline"]["by_timezone_status"]["known"] == 25
        assert summary["inferences"]["total"] == 9
        assert summary["inferences"]["by_status"] == {"revised": 7, "retained": 1, "withdrawn": 1}
        assert len(c.get(f"/api/cases/{case['id']}/revisions").json()) == 12  # the log, minus the non-inference "Order" row
        ev = c.get(f"/api/cases/{case['id']}/evidence").json()[0]
        assert c.get(f"/api/evidence/{ev['id']}/verify").json()["result"] == "MATCH"
        infs = {i["title"].split(":")[0]: i for i in c.get(f"/api/cases/{case['id']}/inferences").json()}
        assert infs["I9"]["status"] == "withdrawn" and infs["I9"]["confidence"] == 1
        assert infs["I4"]["status"] == "retained" and len(infs["I2"]["event_ids"]) == 6
        assert c.get(f"/api/cases/{case['id']}/report", headers=INV).status_code == 200
    # a second start with a populated database must not seed again
    with TestClient(create_app(settings)) as c:
        assert len(c.get("/api/cases").json()) == 1
