"""Validated model boundaries and persisted conversation channels."""

from datetime import date, datetime
from typing import Annotated, Literal, TypedDict
from zoneinfo import ZoneInfo

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
    slot_date: str | None = None
    duration_hours: float | None = None
    spot_type: Literal["standard", "electric", "accessible", "van"] | None = None


class GraphOutput(StrictModel):
    request_id: str
    final_reply: str = Field(min_length=1, max_length=12000)
    reservation_state: BookingDetails


class Intent(StrictModel):
    kind: Literal["policy", "reservation", "conversation", "unsupported"]
    language: Literal["en"]
    facilities: list[Literal["CTR", "RIV", "STA", "AIR"]]
    retrieval_question: str = Field(min_length=1, max_length=4000)
    explain_spot_id: bool = False
    lookup_only: bool = False


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


class LanguageDecision(StrictModel):
    is_english: bool


class InputGuardDecision(StrictModel):
    allowed: bool


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
    is_english: bool
    rewritten_question: str | None
    booking_draft: dict
    reservation_id: str | None
    reservation_summary: str
    booking_error: str | None
    admin_result: dict | None
    parking_search: dict
    parking_options: list[dict]
    date_clarification: str | None
    field_errors: dict[str, str]
    awaiting_space_selection: bool
    space_choice: Literal["none", "accept_type", "defer", "clarify"]


class ReservationDraft(StrictModel):
    spot_id: str | None = None
    start: str | None = None
    end: str | None = None
    name: str | None = None
    surname: str | None = None
    car_number: str | None = None

    @field_validator("start", "end")
    @classmethod
    def normalized_timestamp(cls, value):
        if value is None:
            return value
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None:
            raise ValueError("A normalized timestamp requires an offset")
        local = parsed.astimezone(ZoneInfo("Europe/Warsaw"))
        if parsed.replace(tzinfo=None) != local.replace(tzinfo=None) or parsed.utcoffset() != local.utcoffset():
            raise ValueError("Timestamp must use the valid Warsaw local time and offset")
        return local.isoformat()


class ReservationFieldUpdate(StrictModel):
    field: Literal["facility", "spot_type", "spot_id", "slot_date", "start", "end",
                   "duration_hours", "name", "surname", "car_number"]
    operation: Literal["set", "clear", "clarify"]
    value: str | None


class ReservationExtraction(StrictModel):
    """Only touched fields appear; null never implicitly clears another field."""

    updates: list[ReservationFieldUpdate] = Field(default_factory=list, max_length=20)
    space_choice: Literal["none", "accept_type", "defer", "clarify"] = "none"


class DraftFieldUpdate(StrictModel):
    field: Literal["spot_id", "name", "surname", "car_number"]
    operation: Literal["set", "clear"]
    value: str | None


class ParkingSearch(StrictModel):
    facility: Literal["CTR", "RIV", "STA", "AIR"] | None = None
    slot_date: str | None = None
    duration_hours: float | None = Field(default=None, gt=0, le=24)
    spot_type: Literal["standard", "electric", "accessible", "van"] | None = None

    @field_validator("slot_date")
    @classmethod
    def normalized_date(cls, value):
        return date.fromisoformat(value).isoformat() if value is not None else None


class ReservationState(MainState, total=False):
    reservation_messages: Annotated[list[AnyMessage], add_messages]
    collection_steps: int
    collection_action: Literal["continue", "ask", "submit"]
    date_clarification: str | None


class ReservationSummary(StrictModel):
    summary: str = Field(min_length=1, max_length=2000)


class AdminResponse(StrictModel):
    reservation_id: str
    response: str = Field(min_length=1, max_length=2000)


class AdminDecision(StrictModel):
    response: Literal["approve", "reject"]


class AdminResult(StrictModel):
    reservation_id: str
    status: Literal["approved", "rejected"]
    reason: str | None = None


class ReservationOutput(TypedDict):
    booking_draft: dict
    reservation_state: dict
    reservation_id: str | None
    reservation_summary: str
    booking_error: str | None
    parking_search: dict
    parking_options: list[dict]
    date_clarification: str | None
    evidence: Annotated[dict, merge_evidence]
    field_errors: dict[str, str]
    space_choice: Literal["none", "accept_type", "defer", "clarify"]


class AdminOutput(TypedDict):
    admin_result: dict


class AdminInput(TypedDict):
    reservation_id: str
    reservation_summary: str
    booking_draft: dict


class AdminState(AdminInput, total=False):
    # Shared handoff keys have the same names/types as MainState. Tool history
    # stays private to the compiled subgraph and cannot enter customer messages.
    admin_response: dict
    admin_decision: dict
    admin_messages: Annotated[list[AnyMessage], add_messages]
    admin_result: dict


class PolicyOutput(TypedDict):
    final_reply: str
    reservation_state: dict
    messages: Annotated[list[AnyMessage], add_messages]
    evidence: Annotated[dict, merge_evidence]
