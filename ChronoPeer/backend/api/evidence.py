"""Evidence upload (preview, then import), listing and integrity re-check."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from ..deps import get_db, get_settings, investigator_only
from ..models import Case, Evidence
from ..services import evidence_importer, get_or_404
from ..services.hashing import verify_stored

router = APIRouter(prefix="/api", tags=["evidence"])


def _read(file: UploadFile, settings):
    # Read at most limit+1 bytes: enough to detect "too large" without loading an unbounded upload.
    return file.filename, file.file.read(settings.max_upload_bytes + 1)


@router.post("/cases/{case_id}/evidence/preview")
def preview_evidence(
    case_id: int,
    file: UploadFile = File(...),
    assume_timezone: str = Form(""),
    db=Depends(get_db),
    settings=Depends(get_settings),
    _actor=Depends(investigator_only),
):
    case = get_or_404(db, Case, case_id, "Case")
    name, data = _read(file, settings)
    return evidence_importer.preview(db, settings, case, name, data, assume_timezone)


@router.post("/cases/{case_id}/evidence", status_code=201)
def import_evidence(
    case_id: int,
    file: UploadFile = File(...),
    assume_timezone: str = Form(""),
    db=Depends(get_db),
    settings=Depends(get_settings),
    actor=Depends(investigator_only),
):
    case = get_or_404(db, Case, case_id, "Case")
    name, data = _read(file, settings)
    result = evidence_importer.import_evidence(db, settings, actor, case, name, data, assume_timezone)
    db.commit()
    return result


@router.get("/cases/{case_id}/evidence")
def list_evidence(case_id: int, db=Depends(get_db)):
    get_or_404(db, Case, case_id, "Case")
    rows = db.scalars(select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.id)).all()
    return [evidence_importer.evidence_out(e) for e in rows]


@router.get("/evidence/{evidence_id}/verify")
def verify_evidence(evidence_id: int, db=Depends(get_db)):
    ev = get_or_404(db, Evidence, evidence_id, "Evidence")
    return {"evidence_id": ev.id, "filename": ev.filename, "recorded_sha256": ev.sha256, "result": verify_stored(ev.file_path, ev.sha256)}
