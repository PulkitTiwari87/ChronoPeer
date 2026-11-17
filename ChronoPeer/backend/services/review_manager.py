"""Peer review: an explicit disposition (agree or challenge), always with a justification."""
from sqlalchemy import select

from ..models import PeerReview
from . import Conflict, ValidationFailed, audit


def review_out(r) -> dict:
    return {
        "id": r.id,
        "inference_id": r.inference_id,
        "reviewer_name": r.reviewer_name,
        "decision": r.decision,
        "critique": r.critique,
        "alternative_explanation": r.alternative_explanation,
        "additional_evidence": r.additional_evidence,
        "confidence": r.confidence,
        "round": r.round,
        "created_at": r.created_at.isoformat(timespec="seconds") + "Z",
    }


def create_review(db, inference, data) -> PeerReview:
    if data.decision == "challenge" and not data.alternative_explanation:
        raise ValidationFailed("A challenge must include an alternative explanation")
    rnd = len(inference.revisions)
    duplicate = db.scalar(
        select(PeerReview.id).where(
            PeerReview.inference_id == inference.id,
            PeerReview.reviewer_name == data.reviewer_name,
            PeerReview.round == rnd,
        )
    )
    if duplicate:
        raise Conflict(f"{data.reviewer_name} has already reviewed this inference in round {rnd}")
    review = PeerReview(
        inference_id=inference.id,
        reviewer_name=data.reviewer_name,
        decision=data.decision,
        critique=data.critique,
        alternative_explanation=data.alternative_explanation,
        additional_evidence=data.additional_evidence,
        confidence=data.confidence,
        round=rnd,
    )
    db.add(review)
    db.flush()
    if data.decision == "challenge":
        inference.status = "challenged"
    elif inference.status == "proposed":
        inference.status = "agreed"
    reviewer = audit.Actor("reviewer", data.reviewer_name)
    audit.record(
        db, reviewer, inference.case_id, "review_submitted", review.id,
        f"{data.decision} on inference {inference.id}: {inference.title}",
    )
    return review
