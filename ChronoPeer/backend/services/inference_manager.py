"""Creating and reading inferences. Every inference must cite at least one real event of its case."""
from sqlalchemy import select

from ..models import Inference, TimelineEvent, utcnow
from . import ValidationFailed, audit
from .timeline_builder import sort_key


def review_state(inf) -> dict:
    """Round = number of revisions so far. An open challenge is a challenge nobody has responded to yet."""
    rnd = len(inf.revisions)
    answered = {r.peer_review_id for r in inf.revisions if r.peer_review_id}
    this_round = [r for r in inf.reviews if r.round == rnd]
    return {
        "round": rnd,
        "reviews_total": len(inf.reviews),
        "reviews_this_round": len(this_round),
        "pending_review": not this_round and inf.status != "withdrawn",
        "open_challenges": sum(1 for r in inf.reviews if r.decision == "challenge" and r.id not in answered),
    }


def inference_out(inf) -> dict:
    events = sorted(inf.events, key=sort_key)
    return {
        "id": inf.id,
        "case_id": inf.case_id,
        "title": inf.title,
        "explanation": inf.explanation,
        "reasoning": inf.reasoning,
        "confidence": inf.confidence,
        "status": inf.status,
        "original_explanation": inf.original_explanation,
        "original_reasoning": inf.original_reasoning,
        "original_confidence": inf.original_confidence,
        "created_at": inf.created_at.isoformat(timespec="seconds") + "Z",
        "updated_at": inf.updated_at.isoformat(timespec="seconds") + "Z",
        "event_ids": [e.id for e in events],
        "events": [
            {
                "id": e.id,
                "artifact_reference": e.artifact_reference,
                "event_type": e.event_type,
                "event_time_original": e.event_time_original,
                "description": e.description,
            }
            for e in events
        ],
        "review_state": review_state(inf),
    }


def create_inference(db, actor, case, data) -> Inference:
    wanted = set(data.event_ids)
    found = set(
        db.scalars(
            select(TimelineEvent.id).where(TimelineEvent.case_id == case.id, TimelineEvent.id.in_(wanted))
        ).all()
    )
    missing = sorted(wanted - found)
    if missing:
        raise ValidationFailed(f"Unsupported evidence references: event id(s) {missing} do not exist in this case")
    events = list(db.scalars(select(TimelineEvent).where(TimelineEvent.id.in_(found))).all())
    now = utcnow()
    inf = Inference(
        case_id=case.id,
        title=data.title,
        explanation=data.explanation,
        reasoning=data.reasoning,
        confidence=data.confidence,
        status="proposed",
        original_explanation=data.explanation,
        original_reasoning=data.reasoning,
        original_confidence=data.confidence,
        created_at=now,
        updated_at=now,
        events=events,
    )
    db.add(inf)
    db.flush()
    audit.record(db, actor, case.id, "inference_created", inf.id, f"Inference created: {inf.title} ({len(events)} supporting events)")
    return inf
