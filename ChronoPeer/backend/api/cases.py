"""Cases, the dashboard, per-case summary and the (read-only) audit trail."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..deps import get_db, investigator_only
from ..models import AuditLog, Case, Evidence, Inference, TimelineEvent
from ..schemas import CaseCreate, CaseUpdate
from ..services import Conflict, audit, get_or_404
from ..services.inference_manager import review_state
from ..services.timeline_builder import timeline_summary

router = APIRouter(prefix="/api", tags=["cases"])


def case_out(c) -> dict:
    return {
        "id": c.id,
        "case_code": c.case_code,
        "title": c.title,
        "description": c.description,
        "dataset_name": c.dataset_name,
        "investigation_date": c.investigation_date.isoformat(),
        "status": c.status,
        "conclusion": c.conclusion,
        "created_at": c.created_at.isoformat(timespec="seconds") + "Z",
    }


def audit_out(a) -> dict:
    return {
        "id": a.id,
        "case_id": a.case_id,
        "actor_role": a.actor_role,
        "actor_name": a.actor_name,
        "action_type": a.action_type,
        "record_id": a.record_id,
        "description": a.description,
        "created_at": a.created_at.isoformat(timespec="seconds") + "Z",
    }


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "ephemeral": request.app.state.settings.ephemeral}


@router.get("/dashboard")
def dashboard(db=Depends(get_db)):
    inferences = db.scalars(select(Inference)).all()
    recent = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(10)).all()
    return {
        "investigations": db.scalar(select(func.count(Case.id))),
        "evidence_files": db.scalar(select(func.count(Evidence.id))),
        "timeline_events": db.scalar(select(func.count(TimelineEvent.id))),
        "inferences": len(inferences),
        "pending_reviews": sum(1 for i in inferences if review_state(i)["pending_review"]),
        "recent_activity": [audit_out(a) for a in recent],
    }


@router.get("/cases")
def list_cases(db=Depends(get_db)):
    return [case_out(c) for c in db.scalars(select(Case).order_by(Case.id)).all()]


@router.post("/cases", status_code=201)
def create_case(body: CaseCreate, db=Depends(get_db), actor=Depends(investigator_only)):
    data = body.model_dump(exclude_none=True)
    case = Case(**data)
    db.add(case)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Conflict("That case_code is already in use")
    audit.record(db, actor, case.id, "case_created", case.id, f"Case created: {case.title}")
    db.commit()
    return case_out(case)


@router.get("/cases/{case_id}")
def get_case(case_id: int, db=Depends(get_db)):
    return case_out(get_or_404(db, Case, case_id, "Case"))


@router.patch("/cases/{case_id}")
def update_case(case_id: int, body: CaseUpdate, db=Depends(get_db), actor=Depends(investigator_only)):
    case = get_or_404(db, Case, case_id, "Case")
    changes = body.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(case, key, value)
    audit.record(db, actor, case.id, "case_updated", case.id, "Case updated: " + ", ".join(sorted(changes)) if changes else "Case update (no changes)")
    db.commit()
    return case_out(case)


@router.get("/cases/{case_id}/summary")
def case_summary(case_id: int, db=Depends(get_db)):
    case = get_or_404(db, Case, case_id, "Case")
    events = db.scalars(select(TimelineEvent).where(TimelineEvent.case_id == case.id)).all()
    inferences = db.scalars(select(Inference).where(Inference.case_id == case.id)).all()
    by_status = {}
    for i in inferences:
        by_status[i.status] = by_status.get(i.status, 0) + 1
    states = [review_state(i) for i in inferences]
    return {
        "case": case_out(case),
        "evidence_files": db.scalar(select(func.count(Evidence.id)).where(Evidence.case_id == case.id)),
        "timeline": timeline_summary(events),
        "inferences": {"total": len(inferences), "by_status": by_status},
        "pending_reviews": sum(1 for s in states if s["pending_review"]),
        "open_challenges": sum(s["open_challenges"] for s in states),
    }


@router.get("/cases/{case_id}/audit")
def case_audit(case_id: int, limit: int = 200, db=Depends(get_db)):
    get_or_404(db, Case, case_id, "Case")
    rows = db.scalars(
        select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.id.desc()).limit(min(max(limit, 1), 1000))
    ).all()
    return [audit_out(a) for a in rows]
