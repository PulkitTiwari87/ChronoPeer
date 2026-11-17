from .conftest import INV, REV, event_ids, make_case, make_inference, upload, SAMPLE_CSV


def test_create_inference_with_multiple_supporting_events(client, case):
    inf = make_inference(client, case, refs_=("EV002", "EV003", "EV004"))
    assert inf["status"] == "proposed" and len(inf["event_ids"]) == 3
    assert [e["artifact_reference"] for e in inf["events"]] == ["EV002", "EV003", "EV004"]
    assert inf["original_reasoning"] == inf["reasoning"] and inf["original_confidence"] == 3
    listed = client.get(f"/api/cases/{case}/inferences").json()
    assert [i["id"] for i in listed] == [inf["id"]]


def test_unsupported_event_references_are_rejected(client, case):
    other = make_case(client, "Other case")
    upload(client, other, SAMPLE_CSV.replace("EV00", "OT00"))
    foreign = event_ids(client, other)["OT001"]
    own = event_ids(client, case)["EV001"]
    body = {"title": "t", "explanation": "e", "reasoning": "r", "confidence": 3}
    r = client.post(f"/api/cases/{case}/inferences", json={**body, "event_ids": [own, foreign, 99999]}, headers=INV)
    assert r.status_code == 422
    assert str(foreign) in r.json()["detail"] and "99999" in r.json()["detail"]
    assert client.get(f"/api/cases/{case}/inferences").json() == []


def test_an_inference_needs_at_least_one_event_and_a_valid_confidence(client, case):
    body = {"title": "t", "explanation": "e", "reasoning": "r", "confidence": 3, "event_ids": []}
    assert client.post(f"/api/cases/{case}/inferences", json=body, headers=INV).status_code == 422
    ids = event_ids(client, case)
    for bad in (0, 6):
        r = client.post(f"/api/cases/{case}/inferences", json={**body, "event_ids": [ids["EV001"]], "confidence": bad}, headers=INV)
        assert r.status_code == 422


def test_updating_status_is_recorded_as_a_revision(client, case):
    inf = make_inference(client, case)
    r = client.patch(f"/api/inferences/{inf['id']}/status", json={"status": "unresolved", "change_reason": "Need the USB logs"}, headers=INV)
    assert r.status_code == 200 and r.json()["status"] == "unresolved"
    revs = client.get(f"/api/inferences/{inf['id']}/revisions").json()
    assert len(revs) == 1 and revs[0]["previous_status"] == "proposed" and revs[0]["new_status"] == "unresolved"
    assert revs[0]["change_reason"] == "Need the USB logs"
    bad = client.patch(f"/api/inferences/{inf['id']}/status", json={"status": "guilty", "change_reason": "x"}, headers=INV)
    assert bad.status_code == 422


def test_only_investigator_mode_creates_inferences(client, case):
    ids = event_ids(client, case)
    body = {"title": "t", "explanation": "e", "reasoning": "r", "confidence": 3, "event_ids": [ids["EV001"]]}
    assert client.post(f"/api/cases/{case}/inferences", json=body, headers=REV).status_code == 403
