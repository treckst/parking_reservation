"""Validated model boundaries and persisted conversation channels."""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, field_validator

from parking.graph.reducers import merge_evidence, merge_queries


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class GraphInput(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Empty message")
        return value


class BookingDetails(StrictModel):
    facility: Literal["CTR", "RIV", "STA", "AIR"] | None = None
    spot_id: str | None = None
    start: str | None = None
    end: str | None = None


class GraphOutput(StrictModel):
    request_id: str
    final_reply: str = Field(min_length=1, max_length=12000)
    reservation_state: BookingDetails


class Intent(StrictModel):
    kind: Literal["policy", "unsupported"]
    language: Literal["en", "pl"]
    facilities: list[Literal["CTR", "RIV", "STA", "AIR"]]
    retrieval_question: str = Field(min_length=1, max_length=4000)


class EvidenceDocument(StrictModel):
    id: str
    source: str
    page: int = Field(ge=0)
    title: str
    text: str = Field(min_length=1, max_length=16000)


class EvidenceAttempt(StrictModel):
    query_index: int = Field(ge=1)
    attempt: Literal[1, 2]
    question: str
    documents: list[EvidenceDocument]
    sql_results: list[dict] = Field(default_factory=list)


class QueryRecord(StrictModel):
    index: int = Field(ge=1)
    request_id: str
    original_message: str
    retrieval_question: str


class SupportedClaim(StrictModel):
    claim: str
    facility: Literal["CTR", "RIV", "STA", "AIR", "shared"]
    evidence_ids: list[str]


class EvidenceAssessment(StrictModel):
    status: Literal["sufficient", "partial", "insufficient"]
    claims: list[SupportedClaim]
    missing: list[str]


class RewrittenQuery(StrictModel):
    question: str = Field(min_length=1, max_length=4000)
    preserves_meaning: bool


class InputGuardDecision(StrictModel):
    allowed: bool
    language: Literal["en", "pl"]


class AnswerClaim(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str]


class Answer(StrictModel):
    claims: list[AnswerClaim]
    unavailable: list[str]


class FinalGuardDecision(StrictModel):
    allowed: bool


class MainState(TypedDict, total=False):
    message: str
    request_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    queries: Annotated[dict, merge_queries]
    evidence: Annotated[dict, merge_evidence]
    query_index: int
    attempt: int
    intent: dict
    assessment: dict
    candidate: str
    final_reply: str
    reservation_state: dict
    blocked: bool
    guard_language: str
    rewritten_question: str | None
