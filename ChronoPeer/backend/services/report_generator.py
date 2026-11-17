"""PDF investigation report (the 11 sections of spec FR-09), built with ReportLab.

Reading of "revised timeline": the same ordered events, annotated with the inferences that cite
them and those inferences' CURRENT status. The original timeline (section 4) is never altered.
"""
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from ..models import Evidence, Inference, Revision
from . import audit
from .hashing import verify_stored
from .timeline_builder import event_out, ordered_events, timeline_summary

_base = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=_base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13)
H1 = ParagraphStyle("h1", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=22, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=14, spaceBefore=14, spaceAfter=6)
H3 = ParagraphStyle("h3", parent=_base["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=8, spaceAfter=3)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.5, leading=9.2)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
NOTE = ParagraphStyle("note", parent=BODY, fontSize=8.5, textColor=colors.HexColor("#555555"))

LIMITATIONS = [
    "Timeline accuracy depends on the quality of the source artifacts.",
    "Different system clocks may introduce discrepancies between sources.",
    "Timestamp interpretation is difficult when timezone information is missing; such events are marked, never silently converted.",
    "CSV/JSON imports depend on correct extraction by an external forensic tool.",
    "ChronoPeer does not perform disk acquisition or low-level forensic analysis.",
    "Peer review reduces unsupported reasoning but does not guarantee correct conclusions.",
    "The application does not independently determine intent or establish guilt.",
    "Shared review mode does not provide strong identity authentication; reviewer names are self-declared.",
]


SECTION_TITLES = [
    "1. Investigation details",
    "2. Dataset information",
    "3. Evidence inventory",
    "4. Original timeline",
    "5. Original inferences",
    "6. Peer critiques",
    "7. Alternative explanations",
    "8. Revised timeline",
    "9. Revision history",
    "10. Limitations",
    "11. Final conclusion",
]


class _Doc(SimpleDocTemplate):
    """Adds a PDF outline entry (bookmark) for each numbered section heading."""

    def afterFlowable(self, flowable):
        if getattr(flowable, "_section", False):
            key = f"section-{self.page}-{id(flowable)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(), key, 0, 0)


def _t(value) -> str:
    """Escape for ReportLab and replace characters the built-in fonts cannot draw."""
    text = "" if value is None else str(value)
    safe = escape(text.encode("cp1252", "replace").decode("cp1252"))
    return safe.replace(chr(10), "<br/>")


def _p(value, style=BODY) -> Paragraph:
    paragraph = Paragraph(_t(value), style)
    paragraph._section = style is H2  # level-2 headings are the numbered report sections
    return paragraph


def _table(rows, widths_mm, zebra=True) -> Table:
    data = [[Paragraph(_t(c), CELLB if r == 0 else CELL) for c in row] for r, row in enumerate(rows)]
    table = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d1d1f")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c7c7cc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if zebra:
        style += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f7")])]
    table.setStyle(TableStyle(style))
    return table


def _stamp(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC"


def _footer(case_id):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6e6e73"))
        canvas.drawString(15 * mm, 8 * mm, f"ChronoPeer investigation report - case {case_id}")
        canvas.drawRightString(landscape(A4)[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw


def generate_pdf(db, settings, actor, case):
    evidence = db.scalars(select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.id)).all()
    events = ordered_events(db, case.id)
    inferences = db.scalars(select(Inference).where(Inference.case_id == case.id).order_by(Inference.id)).all()
    revisions = db.scalars(
        select(Revision).join(Inference, Inference.id == Revision.inference_id).where(Inference.case_id == case.id).order_by(Revision.id)
    ).all()
    label = {inf.id: f"I{n}" for n, inf in enumerate(inferences, 1)}
    summary = timeline_summary(events)
    now = datetime.now(timezone.utc)
    story = []

    # 1. Investigation details
    story += [_p("ChronoPeer forensic investigation report", H1), _p("1. Investigation details", H2)]
    story.append(
        _table(
            [
                ["Field", "Value"],
                ["Case ID", f"{case.id}" + (f" ({case.case_code})" if case.case_code else "")],
                ["Title", case.title],
                ["Description", case.description or "-"],
                ["Investigation date", case.investigation_date.isoformat()],
                ["Status", case.status],
                ["Report generated", _stamp(now)],
                ["Contents", f"{len(evidence)} evidence file(s), {summary['total']} timeline events, {len(inferences)} inferences, {len(revisions)} revisions"],
            ],
            [45, 222],
        )
    )

    # 2. Dataset information
    story.append(_p("2. Dataset information", H2))
    story.append(_p(f"Dataset: {case.dataset_name or 'not recorded'}"))
    counts = summary["by_timezone_status"]
    story.append(
        _p(
            f"Timestamp status across {summary['total']} events: known {counts['known']}, assumed {counts['assumed']}, "
            f"unknown timezone {counts['unknown']}, invalid {counts['invalid']}, missing {counts['missing']}.",
            NOTE,
        )
    )

    # 3. Evidence inventory
    story.append(_p("3. Evidence inventory", H2))
    rows = [["Filename", "Type", "Records", "Imported", "SHA-256 (recorded)", "Re-check at report time"]]
    for ev in evidence:
        rows.append([ev.filename, ev.file_type, ev.record_count, _stamp(ev.imported_at), ev.sha256, verify_stored(ev.file_path, ev.sha256)])
    story.append(_table(rows, [55, 14, 16, 36, 110, 36]))
    story.append(_p("A matching SHA-256 shows the stored file equals the recorded digest. It does not prove the evidence was authentic or that custody was unbroken.", NOTE))

    # 4. Original timeline
    story.append(_p("4. Original timeline", H2))
    rows = [["#", "Original timestamp", "UTC", "Timezone", "Type", "Artifact", "Evidence file", "Description"]]
    for n, e in enumerate(events, 1):
        out = event_out(e)
        rows.append([n, out["event_time_original"] or "-", out["event_time_utc"] or "-", out["timezone_status"], out["event_type"], out["artifact_reference"], out["evidence_filename"], out["description"]])
    story.append(_table(rows, [8, 34, 34, 16, 24, 20, 34, 97]))

    # 5. Original inferences
    story.append(_p("5. Original inferences", H2))
    for inf in inferences:
        refs = ", ".join(e.artifact_reference for e in sorted(inf.events, key=lambda x: x.id))
        story += [
            _p(f"{label[inf.id]}. {inf.title}", H3),
            _p(f"<b>Original explanation:</b> {_t(inf.original_explanation)}"),
            _p(f"<b>Original reasoning:</b> {_t(inf.original_reasoning)}"),
            _p(f"<b>Original confidence:</b> {inf.original_confidence} / 5. <b>Supporting events:</b> {_t(refs)}"),
        ]
    if not inferences:
        story.append(_p("No inferences recorded."))

    # 6. Peer critiques / 7. Alternative explanations
    story.append(_p("6. Peer critiques", H2))
    unreviewed = []
    for inf in inferences:
        story.append(_p(f"{label[inf.id]}. {inf.title}", H3))
        if not inf.reviews:
            unreviewed.append(label[inf.id])
            story.append(_p("No review disposition recorded yet."))
        for r in inf.reviews:
            conf = f", reviewer confidence {r.confidence}/5" if r.confidence else ""
            story.append(_p(f"<b>{_t(r.reviewer_name)}</b> - {r.decision} (round {r.round}, {_stamp(r.created_at)}{conf}): {_t(r.critique)}"))
    if unreviewed:
        story.append(_p("Inferences without a review disposition: " + ", ".join(unreviewed), NOTE))

    story.append(_p("7. Alternative explanations", H2))
    any_alt = False
    for inf in inferences:
        for r in inf.reviews:
            if r.alternative_explanation or r.additional_evidence:
                any_alt = True
                story.append(_p(f"<b>{label[inf.id]}</b> ({_t(r.reviewer_name)}): <b>Alternative:</b> {_t(r.alternative_explanation) or '-'} <b>Evidence requested:</b> {_t(r.additional_evidence) or '-'}"))
    if not any_alt:
        story.append(_p("No alternative explanations recorded."))

    # 8. Revised timeline
    story.append(_p("8. Revised timeline", H2))
    story.append(_p("The same events in the same order, annotated with the inferences that cite them and each inference's current status.", NOTE))
    cited = {}
    for inf in inferences:
        for e in inf.events:
            cited.setdefault(e.id, []).append(f"{label[inf.id]} ({inf.status})")
    rows = [["#", "UTC / original", "Type", "Artifact", "Description", "Cited by (current status)"]]
    for n, e in enumerate(events, 1):
        out = event_out(e)
        rows.append([n, out["event_time_utc"] or out["event_time_original"] or "-", out["event_type"], out["artifact_reference"], out["description"], "; ".join(cited.get(e.id, [])) or "-"])
    story.append(_table(rows, [8, 38, 26, 22, 108, 65]))

    # 9. Revision history
    story.append(_p("9. Revision history", H2))
    if revisions:
        rows = [["When", "Inference", "Response", "Status", "Conf.", "Reason", "Explanation change"]]
        for r in revisions:
            changed = "" if r.previous_explanation == r.revised_explanation else f"{r.previous_explanation[:160]} -> {r.revised_explanation[:160]}"
            rows.append([_stamp(r.created_at), label.get(r.inference_id, r.inference_id), r.response, f"{r.previous_status} -> {r.new_status}", f"{r.previous_confidence} -> {r.new_confidence}", r.change_reason, changed or "-"])
        story.append(_table(rows, [30, 14, 22, 28, 14, 85, 74]))
    else:
        story.append(_p("No revisions recorded."))

    # 10. Limitations
    story.append(_p("10. Limitations", H2))
    for item in LIMITATIONS:
        story.append(_p("- " + item))
    if counts["unknown"] or counts["invalid"] or counts["missing"]:
        story.append(_p(f"This case: {counts['unknown']} event(s) with unknown timezone, {counts['invalid']} invalid and {counts['missing']} missing timestamps.", NOTE))

    # 11. Final conclusion
    story.append(_p("11. Final conclusion", H2))
    if case.conclusion.strip():
        story.append(_p(case.conclusion))
    by_status = {}
    for inf in inferences:
        by_status[inf.status] = by_status.get(inf.status, 0) + 1
    if by_status:
        story.append(_p("Inference outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())) + ".", NOTE))
    open_items = [label[i.id] for i in inferences if i.status in ("proposed", "challenged", "unresolved")]
    if open_items:
        story.append(_p("Still open: " + ", ".join(open_items) + ".", NOTE))

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    path = settings.reports_dir / f"case-{case.id}-report.pdf"
    doc = _Doc(
        str(path), pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"ChronoPeer report - {case.title}", author="ChronoPeer",
    )
    doc.build(story, onFirstPage=_footer(case.id), onLaterPages=_footer(case.id))
    audit.record(db, actor, case.id, "report_generated", None, f"PDF report generated ({path.name})")
    db.flush()
    return path
