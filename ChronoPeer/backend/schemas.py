"""Request bodies (Pydantic). Whitespace is stripped before length checks."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Decision = Literal["agree", "challenge"]
Response = Literal["accepted", "partially_accepted", "rejected", "modified", "unresolved"]
Status = Literal["proposed", "challenged", "agreed", "revised", "retained", "unresolved", "withdrawn"]


class _Body(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class CaseCreate(_Body):
    title: str = Field(min_length=1, max_length=200)
    case_code: str | None = Field(default=None, max_length=64)
    description: str = ""
    dataset_name: str = Field(default="", max_length=200)
    investigation_date: date | None = None
    status: str = Field(default="open", max_length=32)


class CaseUpdate(_Body):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    dataset_name: str | None = Field(default=None, max_length=200)
    investigation_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    conclusion: str | None = None


class InferenceCreate(_Body):
    title: str = Field(min_length=1, max_length=300)
    explanation: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: int = Field(ge=1, le=5)
    event_ids: list[int] = Field(min_length=1)


class StatusUpdate(_Body):
    status: Status
    change_reason: str = Field(min_length=1)


class ReviewCreate(_Body):
    reviewer_name: str = Field(min_length=1, max_length=80)
    decision: Decision
    critique: str = Field(min_length=1)
    alternative_explanation: str = ""
    additional_evidence: str = ""
    confidence: int | None = Field(default=None, ge=1, le=5)


class RevisionCreate(_Body):
    response: Response
    change_reason: str = Field(min_length=1)
    peer_review_id: int | None = None
    revised_explanation: str | None = None
    revised_reasoning: str | None = None
    new_confidence: int | None = Field(default=None, ge=1, le=5)
    new_status: Status | None = None
