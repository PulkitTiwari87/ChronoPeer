"""PDF investigation report."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..deps import get_db, get_settings, investigator_only
from ..models import Case
from ..services import get_or_404
from ..services.report_generator import generate_pdf

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/cases/{case_id}/report")
def download_report(case_id: int, db=Depends(get_db), settings=Depends(get_settings), actor=Depends(investigator_only)):
    case = get_or_404(db, Case, case_id, "Case")
    path = generate_pdf(db, settings, actor, case)
    db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"chronopeer-case-{case.id}-report.pdf")
