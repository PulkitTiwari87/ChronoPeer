"""Demo case: the real Sysmon investigation (host IEWIN7, 2019-04-30), replayed through the normal services.

Everything comes from files in datasets/sample_exports/ (derived from the project's own CSVs):
the normalised event export is imported with the real importer; inferences, reviews and revisions are
created with the real managers. Nothing is invented. Mappings are documented in docs/dataset_documentation.md.
"""
import csv
import re
from datetime import date

from sqlalchemy import func, select

from ..config import ROOT
from ..models import Case, TimelineEvent
from ..schemas import InferenceCreate, ReviewCreate, RevisionCreate
from . import audit, evidence_importer, inference_manager, review_manager, revision_manager

SRC = ROOT / "datasets" / "sample_exports"
SEED_ACTOR = audit.Actor("investigator", "Seed loader")
_RANK = {"rejected": 1, "low": 2, "medium": 3, "high": 4}
_RESPONSE = {"Upheld": "accepted", "Partly upheld": "partially_accepted", "Answered": "rejected", "Accepted": "modified"}

CASE_DESCRIPTION = (
    "Three Sysmon excerpts (A, B, C) from host IEWIN7 on 2019-04-30: a remote service starting hidden PowerShell, a remote "
    "WMI whoami, and an installer package opening a command prompt. Nine inferences were drawn, each challenged by a reviewer, "
    "and every revision logged. An ordering question (event time versus record order) was answered: event-time order is kept."
)
CASE_CONCLUSION = (
    "Two inferences are well supported: remote service creation over SMB (I2) and remote WMI discovery as IEUser (I6). "
    "Four have a simpler, harmless explanation: injection (I4), service clean-up (I5), timestomping (I8) and shadow-copy "
    "tampering (I9). Open: whether files A, B and C are one actor. Review changed five of nine claims, so the first version overstated."
)


def _rows(name):
    with open(SRC / "source" / name, newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


def confidence_from_text(text: str) -> int:
    """Compound text such as 'Medium (host/log); Low (actor)' maps to its LOWEST part (conservative)."""
    found = re.findall("(rejected|low|medium|high)", text.lower())
    return min(_RANK[w] for w in found) if found else 2


def t_ids(supporting: str) -> list:
    head = supporting.split(";")[0]
    ids = []
    for a, b in re.findall("T([0-9]+)-T([0-9]+)", head):
        ids += [f"T{n:02d}" for n in range(int(a), int(b) + 1)]
    ids += re.findall("T[0-9]+", re.sub("T[0-9]+-T[0-9]+", "", head))
    return list(dict.fromkeys(ids))


def seed(db, settings) -> None:
    case = Case(
        case_code="DF-PBL-040",
        title="Incident timeline peer review: Sysmon host IEWIN7",
        description=CASE_DESCRIPTION,
        dataset_name="sbousseaden/EVTX-ATTACK-SAMPLES (GPL-3.0), commit 4ceed2f; three Sysmon .evtx files",
        investigation_date=date(2026, 11, 17),
        status="under review",
        conclusion=CASE_CONCLUSION,
    )
    db.add(case)
    db.flush()
    audit.record(db, SEED_ACTOR, case.id, "case_created", case.id, "Demo case loaded from the project's real Sysmon data")

    export = SRC / "sysmon_iewin7_export.csv"
    evidence_importer.import_evidence(db, settings, SEED_ACTOR, case, export.name, export.read_bytes())

    source_events = {r["id"]: f"{r['source']}-{r['record_id']}" for r in _rows("timeline.csv")}
    event_ids = {
        ref: eid for eid, ref in db.execute(select(TimelineEvent.id, TimelineEvent.artifact_reference).where(TimelineEvent.case_id == case.id))
    }
    v2 = {r["id"]: r for r in _rows("inference_register_v2.csv")}

    inferences = {}
    for row in _rows("inference_register.csv"):
        key = row["id"]
        reasoning = (
            f"Author confidence (v1): {row['confidence_v1']}. Supporting events: {row['supporting_events']}. "
            f"Alternative anticipated by the author: {row['alternative_anticipated_by_author']} "
            f"Evidence that would distinguish: {row['discriminating_evidence']} "
            f"Cannot be shown by these logs: {row['cannot_be_shown_by_these_logs']}"
        )
        inf = inference_manager.create_inference(
            db, SEED_ACTOR, case,
            InferenceCreate(
                title=f"{key}: {v2[key]['inference (v2, after review)']}"[:290],
                explanation=row["inference (v1, author)"],
                reasoning=reasoning,
                confidence=confidence_from_text(row["confidence_v1"]),
                event_ids=[event_ids[source_events[t]] for t in t_ids(row["supporting_events"])],
            ),
        )
        inferences[key] = (inf, row)

    reviews = {}
    for row in _rows("peer_critique.csv"):
        if row["item"] not in inferences:  # the "Order" row is a method question, not an inference
            continue
        inf, reg = inferences[row["item"]]
        review = review_manager.create_review(
            db, inf,
            ReviewCreate(
                reviewer_name=row["reviewer"],
                decision="challenge",
                critique=f"{row['reviewer_challenge']} Evidence in the logs: {row['evidence_in_logs']} "
                f"(challenge strength recorded in the original critique: {row['challenge_strength (Supported/Weak/Unsupported)']})",
                alternative_explanation="Alternative recorded in the original register: " + reg["alternative_anticipated_by_author"],
                additional_evidence=row["evidence_that_would_distinguish"],
            ),
        )
        reviews[row["item"]] = review

    log = []
    for row in _rows("revision_log.csv"):
        for item in [i.strip() for i in row["item"].split(",")]:
            if item in inferences:
                log.append((item, row))
    last_review_row = {}
    for idx, (item, row) in enumerate(log):
        if row["revision"] != "R2" and _RESPONSE[row["decision"]] != "rejected":
            last_review_row[item] = idx

    for idx, (item, row) in enumerate(log):
        inf, _reg = inferences[item]
        response = _RESPONSE[row["decision"]]
        final = last_review_row.get(item) == idx
        revised_explanation = new_confidence = new_status = None
        if final:
            new_v2 = v2[item]
            revised_explanation = new_v2["inference (v2, after review)"]
            new_confidence = confidence_from_text(new_v2["confidence_v2"])
            new_status = "withdrawn" if new_v2["confidence_v2"].lower().startswith("rejected") else None
        revision_manager.apply_revision(
            db, SEED_ACTOR, inf,
            RevisionCreate(
                response=response,
                peer_review_id=reviews[item].id if row["revision"].startswith("R1") else None,
                change_reason=f"[{row['revision']}] {row['stage']}, raised by {row['by']}: {row['challenge_or_issue']} "
                f"Decision: {row['decision']}. Change: {row['change_made']}",
                revised_reasoning=f"{inf.reasoning} [{row['revision']}] {row['change_made']}",
                revised_explanation=revised_explanation,
                new_confidence=new_confidence,
                new_status=new_status,
            ),
        )


def seed_if_empty(session_factory, settings) -> None:
    with session_factory() as db:
        if db.scalar(select(func.count(Case.id))):
            return
        seed(db, settings)
        db.commit()
