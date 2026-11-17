"""Investigator responses. Every revision snapshots the previous and the new reasoning, so the original
conclusion, the peer challenge, the response and the revised conclusion all stay readable."""
from ..models import INFERENCE_STATUSES, PeerReview, Revision, utcnow
from . import Conflict, ValidationFailed, audit

DEFAULT_STATUS = {
    "accepted": "revised",
    "partially_accepted": "revised",
    "modified": "revised",
    "rejected": "retained",
    "unresolved": "unresolved",
}
NEEDS_REVIEW = ("accepted", "partially_accepted", "rejected")
NEEDS_NEW_REASONING = ("accepted", "partially_accepted", "modified")


def revision_out(r) -> dict:
    return {
        "id": r.id,
        "inference_id": r.inference_id,
        "peer_review_id": r.peer_review_id,
        "response": r.response,
        "previous_explanation": r.previous_explanation,
        "revised_explanation": r.revised_explanation,
        "previous_reasoning": r.previous_reasoning,
        "revised_reasoning": r.revised_reasoning,
        "previous_confidence": r.previous_confidence,
        "new_confidence": r.new_confidence,
        "previous_status": r.previous_status,
        "new_status": r.new_status,
        "change_reason": r.change_reason,
        "actor_name": r.actor_name,
        "created_at": r.created_at.isoformat(timespec="seconds") + "Z",
    }


def apply_revision(db, actor, inference, data) -> Revision:
    if data.response in NEEDS_REVIEW and data.peer_review_id is None:
        raise ValidationFailed(f"Responding with '{data.response}' requires the peer_review_id being answered")
    review = None
    if data.peer_review_id is not None:
        review = db.get(PeerReview, data.peer_review_id)
        if review is None or review.inference_id != inference.id:
            raise ValidationFailed("peer_review_id does not belong to this inference")
        if any(r.peer_review_id == review.id for r in inference.revisions):
            raise Conflict("This review has already been answered")
    if data.response in NEEDS_NEW_REASONING and not (data.revised_reasoning or "").strip():
        raise ValidationFailed(f"Responding with '{data.response}' requires revised_reasoning")

    new_status = data.new_status or DEFAULT_STATUS[data.response]
    if new_status not in INFERENCE_STATUSES:
        raise ValidationFailed(f"Unknown status '{new_status}'")

    if data.response == "rejected":  # a rejected challenge leaves the conclusion exactly as it was
        new_reasoning, new_explanation, new_confidence = inference.reasoning, inference.explanation, inference.confidence
    else:
        new_reasoning = (data.revised_reasoning or "").strip() or inference.reasoning
        new_explanation = (data.revised_explanation or "").strip() or inference.explanation
        new_confidence = data.new_confidence or inference.confidence

    rev = Revision(
        inference_id=inference.id,
        peer_review_id=data.peer_review_id,
        response=data.response,
        previous_explanation=inference.explanation,
        revised_explanation=new_explanation,
        previous_reasoning=inference.reasoning,
        revised_reasoning=new_reasoning,
        previous_confidence=inference.confidence,
        new_confidence=new_confidence,
        previous_status=inference.status,
        new_status=new_status,
        change_reason=data.change_reason,
        actor_name=actor.name,
    )
    inference.explanation = new_explanation
    inference.reasoning = new_reasoning
    inference.confidence = new_confidence
    inference.status = new_status
    inference.updated_at = utcnow()
    db.add(rev)
    db.flush()
    audit.record(
        db, actor, inference.case_id, "revision_recorded", rev.id,
        f"{data.response}: inference {inference.id} {rev.previous_status} -> {new_status}",
    )
    return rev


def history(inference) -> dict:
    """The full story of one inference, oldest first."""
    from .review_manager import review_out

    timeline = [("review", r.created_at, r.id, review_out(r)) for r in inference.reviews]
    timeline += [("revision", r.created_at, r.id, revision_out(r)) for r in inference.revisions]
    timeline.sort(key=lambda t: (t[1], 0 if t[0] == "review" else 1, t[2]))
    return {
        "original": {
            "explanation": inference.original_explanation,
            "reasoning": inference.original_reasoning,
            "confidence": inference.original_confidence,
            "created_at": inference.created_at.isoformat(timespec="seconds") + "Z",
        },
        "current": {
            "explanation": inference.explanation,
            "reasoning": inference.reasoning,
            "confidence": inference.confidence,
            "status": inference.status,
        },
        "steps": [{"kind": kind, **payload} for kind, _when, _id, payload in timeline],
    }
