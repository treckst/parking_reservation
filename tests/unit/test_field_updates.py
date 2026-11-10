"""Every supplied field is applied independently of validation of its siblings."""

from datetime import datetime
import json

from langchain_core.messages import AIMessage
import pytest
from pydantic import ValidationError

from parking.graph.collection import reservation_ready
from parking.graph.dates import ReservationExtractor
from parking.graph.fields import apply_field_updates
from parking.graph.schemas import DraftFieldUpdate, ReservationExtraction
from tests.extraction_helpers import updates


def apply(state, values=None, operations=None):
    patch = ReservationExtraction(updates=(updates(values or {}) + (operations or [])))
    return apply_field_updates(state, patch.updates)


def test_valid_siblings_survive_one_invalid_timestamp():
    result = apply({}, {"facility": "AIR", "spot_type": "standard", "slot_date": "2026-11-24",
        "start": "2026-11-24T15:00:00+01:00", "end": "sometime later",
        "name": "Sample", "surname": "Customer", "car_number": "DEMO123"})
    assert result["booking_draft"]["start"] == "2026-11-24T15:00:00+01:00"
    assert result["booking_draft"]["name"] == "Sample" and result["booking_draft"]["car_number"] == "DEMO123"
    assert result["parking_search"]["slot_date"] == "2026-11-24"
    assert result["parking_search"]["spot_type"] == "standard"
    assert set(result["field_errors"]) == {"end"}
    assert not reservation_ready(result)


@pytest.mark.parametrize("bad_field,value", [("duration_hours", "0"), ("duration_hours", "nan"),
    ("spot_type", "spaceship"), ("facility", "ANY%"), ("car_number", " "), ("spot_id", "AIR-%")])
def test_invalid_field_does_not_revert_other_updates(bad_field, value):
    result = apply({}, {bad_field: value, "name": "NewName", "surname": "SavedSurname"})
    assert result["booking_draft"]["name"] == "NewName"
    assert result["booking_draft"]["surname"] == "SavedSurname"
    assert bad_field in result["field_errors"]


def test_omitted_fields_survive_and_clear_only_removes_target():
    initial = apply({}, {"name": "Name", "surname": "Surname", "car_number": "DEMO", "spot_type": "standard"})
    second = apply(initial, {"car_number": "CORRECTED"})
    assert second["booking_draft"]["name"] == "Name" and second["booking_draft"]["surname"] == "Surname"
    third = apply(second, operations=[{"field": "surname", "operation": "clear", "value": None}])
    assert third["booking_draft"]["surname"] is None
    assert third["booking_draft"]["name"] == "Name" and third["booking_draft"]["car_number"] == "CORRECTED"
    assert third["parking_search"]["spot_type"] == "standard"
    assert apply(third)["booking_draft"] == third["booking_draft"]


def test_set_null_is_an_error_not_an_implicit_clear_or_global_reset():
    result = apply({"booking_draft": {"name": "Name", "surname": "Surname"}},
        operations=[{"field": "name", "operation": "set", "value": None}])
    assert result["booking_draft"]["surname"] == "Surname"
    assert "name" in result["field_errors"]


def test_end_clarification_does_not_erase_supplied_date_or_start():
    result = apply({}, {"slot_date": "2026-11-24", "start": "2026-11-24T15:00:00+01:00"},
        [{"field": "end", "operation": "clarify", "value": None}])
    assert result["booking_draft"]["start"] == "2026-11-24T15:00:00+01:00"
    assert result["parking_search"]["slot_date"] == "2026-11-24"
    assert set(result["field_errors"]) == {"end"}
    corrected = apply(result, {"end": "2026-11-24T20:00:00+01:00"})
    assert not corrected["field_errors"] and corrected["parking_search"]["duration_hours"] == 5


def test_cleared_endpoint_does_not_reappear_on_inspection():
    result = apply({}, {"start": "2026-11-24T15:00:00+01:00", "end": "2026-11-24T20:00:00+01:00"})
    result = apply(result, operations=[{"field": "end", "operation": "clear", "value": None}])
    assert apply(result)["booking_draft"]["end"] is None


def test_date_change_rebases_only_dependent_times_and_preserves_personal_fields():
    result = apply({}, {"start": "2026-11-24T15:00:00+01:00", "end": "2026-11-24T20:00:00+01:00", "name": "Saved"})
    result = apply(result, {"slot_date": "2026-11-25"})
    assert result["booking_draft"]["start"] == "2026-11-25T15:00:00+01:00"
    assert result["booking_draft"]["end"] == "2026-11-25T20:00:00+01:00"
    assert result["booking_draft"]["name"] == "Saved"


def test_duplicate_operations_need_clarification_but_keep_siblings():
    result = apply({}, {"name": "Saved"}, [{"field": "end", "operation": "set", "value": "2026-11-24T20:00:00+01:00"},
        {"field": "end", "operation": "clear", "value": None}])
    assert result["booking_draft"]["name"] == "Saved" and "end" in result["field_errors"]


def test_schemas_reject_hidden_state_and_explicitly_model_operations():
    with pytest.raises(ValidationError):
        ReservationExtraction.model_validate({"updates": [{"field": "admin_result", "operation": "set", "value": "approved"}]})
    with pytest.raises(ValidationError):
        DraftFieldUpdate(field="start", operation="set", value="arbitrary")
    schema = ReservationExtraction.model_json_schema()
    update = schema["$defs"]["ReservationFieldUpdate"]
    assert set(update["required"]) == {"field", "operation", "value"}
    assert update["additionalProperties"] is False
    assert "provided_fields" not in json.dumps(schema)


async def test_missing_year_example_updates_public_state_before_collection():
    patch = ReservationExtraction(updates=updates({"spot_type": "standard", "slot_date": "2026-11-24",
        "start": "2026-11-24T15:00:00+01:00", "end": "2026-11-24T20:00:00+01:00"}))

    class Model:
        def with_structured_output(self, schema, **kwargs):
            assert schema is ReservationExtraction and kwargs["strict"] is True
            return self

        async def ainvoke(self, messages):
            assert "next occurrence" in messages[0].content
            payload = json.loads(messages[-1].content)
            assert payload["saved_search"]["facility"] == "AIR"
            assert payload["reference_time"].startswith("2026-11-10")
            return patch

    result = await ReservationExtractor(lambda: Model(), lambda: datetime.fromisoformat("2026-11-10T17:00:00+01:00")).normalize({
        "message": "i want to make the reservation on standart spot on 24th of november starting at 3 pm up to 20:00",
        "parking_search": {"facility": "AIR"}})
    assert result["reservation_state"] == {"facility": "AIR", "spot_id": None,
        "start": "2026-11-24T15:00:00+01:00", "end": "2026-11-24T20:00:00+01:00",
        "slot_date": "2026-11-24", "duration_hours": 5, "spot_type": "standard"}
    assert not result["field_errors"] and not reservation_ready(result)
