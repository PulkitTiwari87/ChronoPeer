"""SQLAlchemy models: the seven tables of the specification plus audit_logs.

Deliberate additions to the specified columns (documented in docs/database_schema.md):
cases.case_code / investigation_date / conclusion, timeline_events.source_label / import_order,
inferences.explanation / original_*, peer_reviews.round, revisions.response / previous_* / new_*.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

INFERENCE_STATUSES = ("proposed", "challenged", "agreed", "revised", "retained", "unresolved", "withdrawn")
RESPONSES = ("accepted", "partially_accepted", "rejected", "modified", "unresolved")
DECISIONS = ("agree", "challenge")
TZ_STATUSES = ("known", "assumed", "unknown", "invalid", "missing")


def utcnow() -> datetime:
    """Naive UTC 'now' (SQLite has no timezone-aware column type)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


inference_events = Table(
    "inference_events",
    Base.metadata,
    Column("inference_id", ForeignKey("inferences.id"), primary_key=True),
    Column("event_id", ForeignKey("timeline_events.id"), primary_key=True),
)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    dataset_name: Mapped[str] = mapped_column(String(200), default="")
    investigation_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(32), default="open")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("case_id", "sha256", name="uq_evidence_case_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    file_type: Mapped[str] = mapped_column(String(8))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    record_count: Mapped[int] = mapped_column(Integer, default=0)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    event_time_original: Mapped[str] = mapped_column(String(64), default="")
    event_time_utc: Mapped[datetime | None] = mapped_column(DateTime)
    timezone_status: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(64))
    source_label: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text)
    artifact_reference: Mapped[str] = mapped_column(String(128))
    import_order: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped["Evidence"] = relationship()


class Inference(Base):
    __tablename__ = "inferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    explanation: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    original_explanation: Mapped[str] = mapped_column(Text)
    original_reasoning: Mapped[str] = mapped_column(Text)
    original_confidence: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    events: Mapped[list["TimelineEvent"]] = relationship(secondary=inference_events)
    reviews: Mapped[list["PeerReview"]] = relationship(order_by="PeerReview.id")
    revisions: Mapped[list["Revision"]] = relationship(order_by="Revision.id")


class PeerReview(Base):
    __tablename__ = "peer_reviews"
    __table_args__ = (UniqueConstraint("inference_id", "reviewer_name", "round", name="uq_review_round"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    inference_id: Mapped[int] = mapped_column(ForeignKey("inferences.id"), index=True)
    reviewer_name: Mapped[str] = mapped_column(String(80))
    decision: Mapped[str] = mapped_column(String(16))
    critique: Mapped[str] = mapped_column(Text)
    alternative_explanation: Mapped[str] = mapped_column(Text, default="")
    additional_evidence: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int | None] = mapped_column(Integer)
    round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Revision(Base):
    __tablename__ = "revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    inference_id: Mapped[int] = mapped_column(ForeignKey("inferences.id"), index=True)
    peer_review_id: Mapped[int | None] = mapped_column(ForeignKey("peer_reviews.id"))
    response: Mapped[str] = mapped_column(String(24))
    previous_explanation: Mapped[str] = mapped_column(Text)
    revised_explanation: Mapped[str] = mapped_column(Text)
    previous_reasoning: Mapped[str] = mapped_column(Text)
    revised_reasoning: Mapped[str] = mapped_column(Text)
    previous_confidence: Mapped[int] = mapped_column(Integer)
    new_confidence: Mapped[int] = mapped_column(Integer)
    previous_status: Mapped[str] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16))
    change_reason: Mapped[str] = mapped_column(Text)
    actor_name: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Append-only: the ORM refuses updates and deletes (see listeners below)."""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int | None] = mapped_column(Integer, index=True)
    actor_role: Mapped[str] = mapped_column(String(16))
    actor_name: Mapped[str] = mapped_column(String(80))
    action_type: Mapped[str] = mapped_column(String(48))
    record_id: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


@event.listens_for(AuditLog, "before_update")
def _audit_refuse_update(mapper, connection, target):
    raise ValueError("audit_logs is append-only")


@event.listens_for(AuditLog, "before_delete")
def _audit_refuse_delete(mapper, connection, target):
    raise ValueError("audit_logs is append-only")
