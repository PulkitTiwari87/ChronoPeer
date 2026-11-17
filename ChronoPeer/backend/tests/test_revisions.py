import pytest
from sqlalchemy import select

from backend.models import AuditLog

from .conftest import INV, REV, make_inference
from .test_reviews import review


def respond(client, inf_id, headers=INV, **over):
    body = {"response": "accepted", "change_reason": "The reviewer is right: the logs do not show a file copy.", **over}
    return client.post(f"/api/inferences/{inf_id}/revisions", json=body, headers=headers)


def challenged(client, case):
    inf = make_inference(client, case)
    return inf, review(client, inf["id"]).json()


def test_accepting_a_challenge_preserves_the_original_reasoning(client, case):
    inf, rv = challenged(client, case)
    r = respond(
        client, inf["id"], peer_review_id=rv["id"],
        revised_reasoning="The device connected and disconnected; use during that window is unproven.",
        revised_explanation="A USB device was connected between 09:15 and 09:35; its use is unproven.",
        new_confidence=2,
    )
    assert r.status_code == 201
    rev, now = r.json()["revision"], r.json()["inference"]
    assert now["status"] == "revised" and now["confidence"] == 2
    assert now["original_reasoning"] == inf["reasoning"] and now["original_confidence"] == 3
    assert rev["previous_reasoning"] == inf["reasoning"] and rev["revised_reasoning"] == now["reasoning"]
    assert rev["previous_status"] == "challenged" and rev["new_status"] == "revised"


def test_rejecting_a_challenge_needs_a_justification_and_changes_nothing(client, case):
    inf, rv = challenged(client, case)
    assert respond(client, inf["id"], response="rejected", peer_review_id=rv["id"], change_reason="").status_code == 422
    r = respond(client, inf["id"], response="rejected", peer_review_id=rv["id"], change_reason="Device serial matches the copied files.", revised_reasoning="ignored")
    assert r.status_code == 201
    now = r.json()["inference"]
    assert now["status"] == "retained" and now["reasoning"] == inf["reasoning"] and now["confidence"] == inf["confidence"]


def test_partial_acceptance_and_unresolved(client, case):
    inf, rv = challenged(client, case)
    r = respond(client, inf["id"], response="partially_accepted", peer_review_id=rv["id"], revised_reasoning="Connection proven; use unproven.")
    assert r.json()["inference"]["status"] == "revised"
    u = respond(client, inf["id"], response="unresolved", change_reason="Waiting for the file-copy artifacts.")
    assert u.json()["inference"]["status"] == "unresolved"


def test_acceptance_needs_revised_reasoning_and_a_review_to_answer(client, case):
    inf, rv = challenged(client, case)
    assert respond(client, inf["id"], peer_review_id=rv["id"]).status_code == 422  # no revised_reasoning
    assert respond(client, inf["id"], revised_reasoning="x").status_code == 422  # no peer_review_id
    assert respond(client, inf["id"], peer_review_id=999, revised_reasoning="x").status_code == 422
    assert client.get(f"/api/inferences/{inf['id']}/revisions").json() == []


def test_a_review_can_only_be_answered_once(client, case):
    inf, rv = challenged(client, case)
    assert respond(client, inf["id"], peer_review_id=rv["id"], revised_reasoning="First answer.").status_code == 201
    assert respond(client, inf["id"], peer_review_id=rv["id"], revised_reasoning="Second answer.").status_code == 409


def test_history_shows_original_challenge_response_and_revision_in_order(client, case):
    inf, rv = challenged(client, case)
    respond(client, inf["id"], peer_review_id=rv["id"], revised_reasoning="Narrowed claim.")
    h = client.get(f"/api/inferences/{inf['id']}/history").json()
    assert h["original"]["reasoning"] == inf["reasoning"] and h["current"]["reasoning"] == "Narrowed claim."
    assert [s["kind"] for s in h["steps"]] == ["review", "revision"]
    assert client.get(f"/api/cases/{case}/revisions").json()[0]["inference_id"] == inf["id"]


def test_a_reviewed_again_round_is_allowed_after_a_revision(client, case):
    inf, rv = challenged(client, case)
    respond(client, inf["id"], peer_review_id=rv["id"], revised_reasoning="Narrowed claim.")
    again = review(client, inf["id"])  # same reviewer, new round
    assert again.status_code == 201 and again.json()["round"] == 1


def test_only_investigator_mode_responds(client, case):
    inf, rv = challenged(client, case)
    assert respond(client, inf["id"], headers=REV, peer_review_id=rv["id"], revised_reasoning="x").status_code == 403


def test_audit_log_is_append_only_and_records_every_step(client, case):
    inf, rv = challenged(client, case)
    respond(client, inf["id"], peer_review_id=rv["id"], revised_reasoning="Narrowed claim.")
    actions = [a["action_type"] for a in reversed(client.get(f"/api/cases/{case}/audit").json())]
    assert actions == ["case_created", "evidence_imported", "inference_created", "review_submitted", "revision_recorded"]
    assert client.delete(f"/api/cases/{case}/audit").status_code == 405  # no delete endpoint exists
    with client.app.state.session_factory() as db:
        row = db.scalars(select(AuditLog)).first()
        row.description = "tampered"
        with pytest.raises(ValueError):
            db.flush()
        db.rollback()
        db.delete(db.scalars(select(AuditLog)).first())
        with pytest.raises(ValueError):
            db.flush()
