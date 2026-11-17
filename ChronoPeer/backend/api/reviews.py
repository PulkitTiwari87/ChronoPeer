"""Peer review endpoints. Only reviewer mode may submit a review."""
from fastapi import APIRouter, Depends

from ..deps import get_db, reviewer_only
from ..models import Inference
from ..schemas import ReviewCreate
from ..services import get_or_404, review_manager

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/inferences/{inference_id}/reviews", status_code=201)
def submit_review(inference_id: int, body: ReviewCreate, db=Depends(get_db), _actor=Depends(reviewer_only)):
    inf = get_or_404(db, Inference, inference_id, "Inference")
    review = review_manager.create_review(db, inf, body)
    db.commit()
    return review_manager.review_out(review)


@router.get("/inferences/{inference_id}/reviews")
def list_reviews(inference_id: int, db=Depends(get_db)):
    inf = get_or_404(db, Inference, inference_id, "Inference")
    return [review_manager.review_out(r) for r in inf.reviews]
