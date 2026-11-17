from .conftest import INV, REV, make_inference


def review(client, inf_id, headers=REV, **over):
    body = {
        "reviewer_name": "Sam",
        "decision": "challenge",
        "critique": "Connection times do not prove the device was used to copy anything.",
        "alternative_explanation": "The device was connected for charging only.",
        "additional_evidence": "File-copy artifacts for the device's drive letter.",
        "confidence": 4,
        **over,
    }
    return client.post(f"/api/inferences/{inf_id}/reviews", json=body, headers=headers)


def test_submitting_a_challenge(client, case):
    inf = make_inference(client, case)
    r = review(client, inf["id"])
    assert r.status_code == 201
    body = r.json()
    assert body["decision"] == "challenge" and body["alternative_explanation"] and body["confidence"] == 4
    assert body["additional_evidence"].startswith("File-copy")
    after = client.get(f"/api/inferences/{inf['id']}").json()
    assert after["status"] == "challenged" and after["review_state"]["open_challenges"] == 1


def test_a_challenge_must_offer_an_alternative_explanation(client, case):
    inf = make_inference(client, case)
    assert review(client, inf["id"], alternative_explanation="").status_code == 422
    assert client.get(f"/api/inferences/{inf['id']}/reviews").json() == []


def test_agreement_needs_a_justification_and_marks_the_inference_agreed(client, case):
    inf = make_inference(client, case)
    assert review(client, inf["id"], decision="agree", critique="").status_code == 422
    r = review(client, inf["id"], decision="agree", critique="Timestamps and device IDs line up.", alternative_explanation="")
    assert r.status_code == 201
    assert client.get(f"/api/inferences/{inf['id']}").json()["status"] == "agreed"


def test_duplicate_submission_in_the_same_round_is_rejected(client, case):
    inf = make_inference(client, case)
    assert review(client, inf["id"]).status_code == 201
    assert review(client, inf["id"]).status_code == 409
    assert review(client, inf["id"], reviewer_name="Robin").status_code == 201  # a different reviewer is fine
    assert len(client.get(f"/api/inferences/{inf['id']}/reviews").json()) == 2


def test_only_reviewer_mode_can_review(client, case):
    inf = make_inference(client, case)
    assert review(client, inf["id"], headers=INV).status_code == 403


def test_every_inference_needs_a_disposition(client, case):
    a = make_inference(client, case)
    b = make_inference(client, case, refs_=("EV001",), title="Login at 09:02")
    assert client.get(f"/api/cases/{case}/summary").json()["pending_reviews"] == 2
    review(client, a["id"])
    assert client.get(f"/api/cases/{case}/summary").json()["pending_reviews"] == 1
    review(client, b["id"], decision="agree", critique="Clear login record.", alternative_explanation="")
    assert client.get(f"/api/cases/{case}/summary").json()["pending_reviews"] == 0
    assert client.get("/api/dashboard").json()["pending_reviews"] == 0
