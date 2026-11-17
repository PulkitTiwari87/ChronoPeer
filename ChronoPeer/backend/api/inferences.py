"""Inference management."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import get_db, investigator_only
from ..models import Case, Inference
from ..schemas import InferenceCreate, RevisionCreate, StatusUpdate
from ..services import get_or_404, inference_manager, revision_manager

router = APIRouter(prefix="/api", tags=["inferences"])


@router.post("/cases/{case_id}/inferences", status_code=201)
def create_inference(case_id: int, body: InferenceCreate, db=Depends(get_db), actor=Depends(investigator_only)):
    case = get_or_404(db, Case, case_id, "Case")
    inf = inference_manager.create_inference(db, actor, case, body)
    db.commit()
    return inference_manager.inference_out(inf)


@router.get("/cases/{case_id}/inferences")
def list_inferences(case_id: int, db=Depends(get_db)):
    get_or_404(db, Case, case_id, "Case")
    rows = db.scalars(select(Inference).where(Inference.case_id == case_id).order_by(Inference.id)).all()
    return [inference_manager.inference_out(i) for i in rows]


@router.get("/inferences/{inference_id}")
def get_inference(inference_id: int, db=Depends(get_db)):
    return inference_manager.inference_out(get_or_404(db, Inference, inference_id, "Inference"))


@router.patch("/inferences/{inference_id}/status")
def update_status(inference_id: int, body: StatusUpdate, db=Depends(get_db), actor=Depends(investigator_only)):
    """A status change is itself recorded as a revision, so the previous state is never lost."""
    inf = get_or_404(db, Inference, inference_id, "Inference")
    revision_manager.apply_revision(
        db, actor, inf,
        RevisionCreate(response="modified", change_reason=body.change_reason, revised_reasoning=inf.reasoning, new_status=body.status),
    )
    db.commit()
    return inference_manager.inference_out(inf)


@router.get("/inferences/{inference_id}/history")
def inference_history(inference_id: int, db=Depends(get_db)):
    return revision_manager.history(get_or_404(db, Inference, inference_id, "Inference"))
