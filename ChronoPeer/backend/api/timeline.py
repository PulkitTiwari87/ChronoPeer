"""The reconstructed chronological timeline of a case."""
from typing import Literal

from fastapi import APIRouter, Depends

from ..deps import get_db
from ..models import Case
from ..services import get_or_404
from ..services.timeline_builder import event_out, ordered_events, timeline_summary

router = APIRouter(prefix="/api", tags=["timeline"])


@router.get("/cases/{case_id}/timeline")
def get_timeline(case_id: int, order: Literal["asc", "desc"] = "asc", db=Depends(get_db)):
    get_or_404(db, Case, case_id, "Case")
    events = ordered_events(db, case_id, descending=(order == "desc"))
    return {
        "case_id": case_id,
        "order": order,
        "summary": timeline_summary(events),
        "events": [event_out(e) for e in events],
    }
