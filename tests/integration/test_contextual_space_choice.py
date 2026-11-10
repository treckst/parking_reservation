"""Type acceptance continues a quoted choice instead of repeating its question."""

import json
import sqlite3

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import pytest

from parking.graph.graph import build_graph
from parking.graph.dates import ReservationExtractor
from parking.graph.schemas import ReservationExtraction
from parking.graph.selection import awaiting_space_selection
from tests.extraction_helpers import updates
from tests.integration.test_admin_flow import store
from tests.integration.test_extraction_checkpoint import ExtractedModel


TIMES = {"start": "2026-11-24T16:00:00+01:00", "end": "2026-11-24T20:00:00+01:00"}


def add_spaces(store):
    with sqlite3.connect(store.path) as db:
        db.executemany("INSERT INTO transport_slots (spot_id,slot_date,working_hours,hourly_price) VALUES (?,'2026-11-24','06:00-22:00',5)",
                       [(f"AIR-{number:03}",) for number in range(1, 4)])


async def test_type_answer_uses_assistant_offer_and_advances_after_restart(store, tmp_path):
    add_spaces(store)
    config = {"configurable": {"thread_id": "type-answer"}}
    path = str(tmp_path / "choice.sqlite3")
    model = ExtractedModel(updates(TIMES))
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        offered = await graph.ainvoke({"message": "starting at 4pm up to 20:00", "request_id": "standard_choice01"}, config)
        state = (await graph.aget_state(config)).values
        assert state["awaiting_space_selection"] and "Which space" in offered["final_reply"]
        assert "AIR-001, AIR-002, AIR-003 (standard)" in offered["final_reply"]
        evidence = dict(state["evidence"])

    # Availability may change between offer and acceptance. The type acceptance
    # permits another matching space, while preserving the quoted date/interval.
    held = store.reserve("other-customer", "hold", {**TIMES, "spot_id": "AIR-001",
        "name": "PRIVATE", "surname": "PRIVATE", "car_number": "SECRET"}, "")
    model = ExtractedModel(updates({"spot_type": "standard"}))
    model.space_choice = "accept_type"
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "i would like the the standard place", "request_id": "standard_choice02"}, config)
        state = (await graph.aget_state(config)).values
        assert result["reservation_state"]["spot_id"] == "AIR-002"
        assert result["reservation_state"]["start"] == TIMES["start"] and result["reservation_state"]["end"] == TIMES["end"]
        assert "selected: AIR-002" in result["final_reply"] and "20 PLN" in result["final_reply"]
        assert "first name" in result["final_reply"] and "vehicle plate" in result["final_reply"]
        assert "Which space" not in result["final_reply"] and not state["awaiting_space_selection"]
        assert not state["field_errors"] and not state.get("reservation_id")
        assert all(state["evidence"][key] == value for key, value in evidence.items())
        assert len(state["messages"]) == 4
        assert "SECRET" not in json.dumps(result)
        assert [row["reservation_id"] for row in store.pending()] == [held["reservation_id"]]


@pytest.mark.parametrize("mode,lookup,expected", [
    ("none", False, "Shall I choose any available standard space"),
    ("defer", False, "Tell me when you're ready"),
    ("accept_type", True, "Which space"),
])
async def test_unclear_deferred_and_information_only_answers_do_not_assign(store, tmp_path, mode, lookup, expected):
    add_spaces(store)
    config = {"configurable": {"thread_id": "negative-choice"}}
    model = ExtractedModel(updates(TIMES))
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "choice.sqlite3")) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        before = await graph.ainvoke({"message": "Airport on November 24, 4pm-8pm", "request_id": "negative_choice1"}, config)
        model.patch = updates({"spot_type": "standard"})
        model.space_choice, model.lookup_only = mode, lookup
        result = await graph.ainvoke({"message": "standard-related follow-up", "request_id": "negative_choice2"}, config)
        assert result["reservation_state"]["spot_id"] is None
        assert expected in result["final_reply"] and not store.pending()
        if mode != "accept_type":
            assert result["final_reply"] != before["final_reply"]
        if mode == "none":
            model.patch, model.space_choice = [], "accept_type"
            confirmed = await graph.ainvoke({"message": "yes", "request_id": "negative_choice3"}, config)
            assert confirmed["reservation_state"]["spot_id"] == "AIR-001"
            assert "first name" in confirmed["final_reply"] and not store.pending()


async def test_initial_type_preference_is_not_acceptance_of_an_unoffered_space(store, tmp_path):
    add_spaces(store)
    model = ExtractedModel(updates({**TIMES, "spot_type": "standard"}))
    model.space_choice = "accept_type"  # Even an over-eager model needs prior context.
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "initial.sqlite3")) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "A standard spot at Airport on November 24, 4pm-8pm", "request_id": "initial_choice01"},
            {"configurable": {"thread_id": "initial-preference"}})
        assert result["reservation_state"]["spot_id"] is None
        assert "Which space" in result["final_reply"] and not store.pending()


async def test_extractor_has_full_assistant_history_and_old_checkpoint_question_context():
    offer = "Airport, 24 Nov 2026 16:00–20:00 — AIR-001, AIR-002, AIR-003 (standard). Which space would you like?"
    history = [HumanMessage(content=f"old message {i}") for i in range(20)]
    history += [AIMessage(content=offer), HumanMessage(content="i would like the the standard place")]
    state = {"message": history[-1].content, "messages": history,
        "parking_options": [{"spot_id": "AIR-001", "type": "standard"}],
        "parking_search": {"facility": "AIR"}}
    assert awaiting_space_selection(state)  # No new flag on old checkpoints.

    class Model:
        def with_structured_output(self, schema, **kwargs):
            assert schema is ReservationExtraction
            return self

        async def ainvoke(self, messages):
            data = json.loads(messages[-1].content)
            assert data["last_assistant_message"] == offer and data["awaiting_space_selection"]
            assert len(data["conversation"]) == 22
            assert data["conversation"][-2] == {"role": "ai", "text": offer}
            return {"updates": [], "space_choice": "accept_type"}

    result = await ReservationExtractor(lambda: Model()).normalize(state)
    assert result["parking_search"]["spot_type"] == "standard"
    assert result["space_choice"] == "accept_type"


@pytest.mark.parametrize("mode", ["defer", "clarify"])
async def test_deferred_or_unclear_choice_cannot_submit_a_complete_draft(store, tmp_path, mode):
    add_spaces(store)
    model = ExtractedModel(updates({**TIMES, "spot_id": "AIR-001", "name": "Sample",
        "surname": "Customer", "car_number": "DEMO123"}), "submit_reservation_draft")
    model.space_choice = mode
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "deferred.sqlite3")) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Do not choose or submit yet", "request_id": "deferred_choice1"},
            {"configurable": {"thread_id": "deferred"}})
        assert "__interrupt__" not in result and not store.pending()
        assert "ready to continue" in result["final_reply"] if mode == "defer" else "keep AIR-001" in result["final_reply"]
