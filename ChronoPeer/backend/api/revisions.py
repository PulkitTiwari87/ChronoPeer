"""Investigator responses to peer reviews, and the revision history."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import get_db, investigator_only
from ..models import Case, Inference, Revision
from ..schemas import RevisionCreate
from ..services import get_or_404, inference_manager, revision_manager

router = APIRouter(prefix="/api", tags=["revisions"])


@router.post("/inferences/{inference_id}/revisions", status_code=201)
def respond(inference_id: int, body: RevisionCreate, db=Depends(get_db), actor=Depends(investigator_only)):
    inf = get_or_404(db, Inference, inference_id, "Inference")
    rev = revision_manager.apply_revision(db, actor, inf, body)
    db.commit()
    return {"revision": revision_manager.revision_out(rev), "inference": inference_manager.inference_out(inf)}


@router.get("/inferences/{inference_id}/revisions")
def list_revisions(inference_id: int, db=Depends(get_db)):
    inf = get_or_404(db, Inference, inference_id, "Inference")
    return [revision_manager.revision_out(r) for r in inf.revisions]


@router.get("/cases/{case_id}/revisions")
def case_revisions(case_id: int, db=Depends(get_db)):
    get_or_404(db, Case, case_id, "Case")
    rows = db.scalars(
        select(Revision).join(Inference, Inference.id == Revision.inference_id).where(Inference.case_id == case_id).order_by(Revision.id)
    ).all()
    return [revision_manager.revision_out(r) for r in rows]
