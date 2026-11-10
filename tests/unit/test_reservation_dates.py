"""Date extraction contracts, normalization and readiness without provider calls."""

from datetime import datetime
import json

from langchain_core.messages import AIMessage, HumanMessage
import pytest
from pydantic import ValidationError

from parking.graph.collection import draft_snapshot
from parking.graph.dates import DateNormalizer
from parking.graph.schemas import ReservationDates, ReservationDraft


class DateModel:
    def __init__(self, result):
        self.result = result
        self.payload = None

    def with_structured_output(self, schema, **kwargs):
        assert schema is ReservationDates
        assert kwargs == {"method": "json_schema", "strict": True}
        return self

    async def ainvoke(self, messages):
        self.payload = json.loads(messages[-1].content)
        return self.result


@pytest.mark.parametrize("query,start,end", [
    ("AIR, Yevhen Shmatkov, november 13 2026 from 2pm up to 9pm, is it possible?",
     "2026-11-13T14:00:00+01:00", "2026-11-13T21:00:00+01:00"),
    ("tomorrow from 2pm to 9pm", "2026-11-11T14:00:00+01:00", "2026-11-11T21:00:00+01:00"),
    ("July 13 2027, 2pm to 9pm", "2027-07-13T14:00:00+02:00", "2027-07-13T21:00:00+02:00"),
])
async def test_natural_query_crosses_separate_schema_with_reference_time(query, start, end):
    model = DateModel({"start": start, "end": end, "provided_fields": ["start", "end"], "clarification": None})
    clock = lambda: datetime.fromisoformat("2026-11-10T16:00:00+01:00")
    history = [AIMessage(content="When would you like to park?"), HumanMessage(content=query)]
    result = await DateNormalizer(lambda: model, clock).normalize({
        "message": query, "messages": history, "booking_draft": {"name": "Saved"}})
    assert result["booking_draft"] == {"name": "Saved", "start": start, "end": end}
    assert model.payload["message"] == query
    assert model.payload["reference_time"] == clock().isoformat()
    assert model.payload["timezone"] == "Europe/Warsaw"
    assert model.payload["conversation"][0]["role"] == "ai"


async def test_end_only_correction_and_unrelated_turn_preserve_prior_values():
    draft = {"start": "2026-11-13T14:00:00+01:00", "end": "2026-11-13T21:00:00+01:00", "car_number": "ABC"}
    model = DateModel({"end": "2026-11-13T20:00:00+01:00", "provided_fields": ["end"]})
    normalized = await DateNormalizer(lambda: model).normalize({"message": "Until 8pm instead", "booking_draft": draft})
    assert normalized["booking_draft"] == {**draft, "end": "2026-11-13T20:00:00+01:00"}
    model.result = {"start": None, "end": None, "provided_fields": []}
    result = await DateNormalizer(lambda: model).normalize({"message": "ABC is my plate", "booking_draft": normalized["booking_draft"]})
    assert result["booking_draft"] == normalized["booking_draft"]


@pytest.mark.parametrize("value", ["tomorrow at 2pm", "2026-11-13T14:00:00", "2026-02-30T14:00:00+01:00",
    "2027-07-13T14:00:00+01:00", "2027-03-28T02:30:00+01:00"])
async def test_invalid_model_dates_clear_affected_field_and_require_clarification(value):
    model = DateModel({"start": value, "provided_fields": ["start"]})
    result = await DateNormalizer(lambda: model).normalize({"message": "Change start", "booking_draft": {"name": "Saved"}})
    assert result["booking_draft"] == {"name": "Saved", "start": None}
    assert result["date_clarification"]
    assert "start" in draft_snapshot(result["booking_draft"])["missing_fields"]
    with pytest.raises(ValidationError):
        ReservationDraft(start=value)


async def test_ambiguous_date_cannot_reuse_old_complete_interval():
    model = DateModel({"provided_fields": ["start", "end"], "clarification": "Is 11/12 November 12 or December 11?"})
    result = await DateNormalizer(lambda: model).normalize({"message": "Actually 11/12",
        "booking_draft": {"start": "2026-11-13T14:00:00+01:00", "end": "2026-11-13T21:00:00+01:00"}})
    assert result["booking_draft"] == {"start": None, "end": None}
    assert not draft_snapshot(result["booking_draft"])["ready"]


@pytest.mark.parametrize("end", ["2026-11-13T13:00:00+01:00", "2026-11-14T15:00:00+01:00"])
def test_invalid_interval_is_incomplete_before_submission(end):
    snapshot = draft_snapshot({"spot_id": "AIR-001", "name": "Name", "surname": "Surname", "car_number": "ABC",
        "start": "2026-11-13T14:00:00+01:00", "end": end})
    assert not snapshot["ready"]
    assert set(snapshot["missing_fields"]) == {"start", "end"}


async def test_date_duration_survive_vague_evening_then_start_time_completes_interval():
    model = DateModel({"slot_date": "2026-11-20", "duration_hours": 6,
        "start": None, "end": None, "provided_fields": ["slot_date", "duration_hours", "start", "end"],
        "clarification": "What time in the evening would you like to start?"})
    first = await DateNormalizer(lambda: model).normalize({
        "message": "6 hours in the evening on November 20 2026 at city centre",
        "intent": {"facilities": ["CTR"]}})
    assert first["parking_search"] == {"facility": "CTR", "slot_date": "2026-11-20", "duration_hours": 6}
    assert not first["booking_draft"].get("start")
    model.result = {"start": "2026-11-20T16:00:00+01:00", "provided_fields": ["start"]}
    second = await DateNormalizer(lambda: model).normalize({**first, "message": "4pm"})
    assert model.payload["saved_search"] == first["parking_search"]
    assert second["booking_draft"]["end"] == "2026-11-20T22:00:00+01:00"
    assert second["parking_search"] == first["parking_search"]


async def test_location_change_clears_old_spot_but_preserves_date_duration():
    model = DateModel({"provided_fields": []})
    result = await DateNormalizer(lambda: model).normalize({"message": "Airport instead",
        "intent": {"facilities": ["AIR"]}, "booking_draft": {"spot_id": "CTR-001"},
        "parking_search": {"facility": "CTR", "slot_date": "2026-11-20", "duration_hours": 6}})
    assert result["parking_search"] == {"facility": "AIR", "slot_date": "2026-11-20", "duration_hours": 6}
    assert result["booking_draft"]["spot_id"] is None
