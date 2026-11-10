"""Reservation discovery across natural-language follow-ups and saver restarts."""

import json
import sqlite3

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from parking.graph.graph import build_graph
from parking.graph.schemas import Intent, ReservationExtraction
from tests.extraction_helpers import temporal_patch, updates
from tests.integration.test_admin_flow import BookingModel
from tests.integration.test_reservation_collection import ScriptedModel
from tests.integration.test_spot_lookup import slot_store


class DiscoveryModel(BookingModel):
    def __init__(self, *, dates=None, draft=None, facility="CTR", explain=False, lookup=False):
        super().__init__(draft={} if draft is None else draft)
        self.dates = dates or {"provided_fields": []}
        self.facility, self.explain, self.lookup = facility, explain, lookup

    def with_structured_output(self, schema, **kwargs):
        delegate = super().with_structured_output(schema, **kwargs)
        model = self

        class Structured:
            async def ainvoke(self, messages):
                if schema is Intent:
                    return {"kind": "reservation", "language": "en", "facilities": [model.facility],
                        "retrieval_question": json.loads(messages[-1].content)["message"],
                        "explain_spot_id": model.explain, "lookup_only": model.lookup}
                if schema is ReservationExtraction:
                    return {"updates": temporal_patch(model.dates)["updates"] + updates({key: value for key, value in model.draft.items()
                        if key not in ("start", "end")})}
                return await delegate.ainvoke(messages)
        return Structured()


async def test_evening_duration_options_explanation_restart_and_selection(slot_store, tmp_path):
    config = {"configurable": {"thread_id": "discovery"}}
    checkpoint = str(tmp_path / "discovery.sqlite3")
    seen = []
    original = slot_store.find_slots

    def tracked(*args, **kwargs):
        seen.append((args, kwargs))
        return original(*args, **kwargs)
    slot_store.find_slots = tracked
    model = DiscoveryModel(dates={"slot_date": "2026-11-20", "duration_hours": 6,
        "provided_fields": ["slot_date", "duration_hours"], "clarification": "What start time?"})
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=slot_store)
        result = await graph.ainvoke({"message": "Can I park for 6 hours in the evening on 20 November 2026 at City Centre?",
            "request_id": "discovery_request01"}, config)
        text = result["final_reply"]
        assert "CTR-001" in text and "48 PLN for 6 hours" in text and "8 PLN/hour" in text
        assert "start time" in text and "06:00-22:00" in text
        assert "first name" not in text and "vehicle plate" not in text and "your spot ID" not in text
        assert "available:" not in text.lower() and len(text) < 350
        state = (await graph.aget_state(config)).values
        assert state["parking_search"] == {"facility": "CTR", "slot_date": "2026-11-20", "duration_hours": 6, "spot_type": None}
        assert state["evidence"]["1:1"]["sql_results"][0]["filters"]["slot_date"] == "2026-11-20"
        first_evidence = state["evidence"]["1:1"]

        model.dates, model.explain = {"provided_fields": []}, True
        result = await graph.ainvoke({"message": "what is spot id?", "request_id": "discovery_request02"}, config)
        assert "parking space label" in result["final_reply"] and "48 PLN" in result["final_reply"]
        assert "start time" in result["final_reply"]
        assert (await graph.aget_state(config)).values["evidence"]["1:1"] == first_evidence

    # A conflicting reservation added after a date-only quote is excluded once
    # exact times are supplied. Names/plates from that row never enter evidence.
    with sqlite3.connect(slot_store.path) as db:
        db.execute("""INSERT INTO reservations
            (reservation_id,spot_id,slot_date,name,surname,car_number,start_time,end_time,status,created_at)
            VALUES ('legacy','CTR-001','2026-11-20','PRIVATE','SURNAME','SECRET',?,?,'confirmed',?)""",
            ("2026-11-20T17:00:00+01:00", "2026-11-20T18:00:00+01:00", "2026-11-09T12:00:00+01:00"))
    model = DiscoveryModel(dates={"start": "2026-11-20T16:00:00+01:00", "provided_fields": ["start"]})
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=slot_store)
        result = await graph.ainvoke({"message": "4pm", "request_id": "discovery_request03"}, config)
        assert "CTR-001" not in result["final_reply"] and "CTR-002" in result["final_reply"]
        assert "available:" in result["final_reply"] and "Which space" in result["final_reply"]
        assert result["reservation_state"]["end"] == "2026-11-20T22:00:00+01:00"
        model.dates, model.draft = {"provided_fields": []}, {"spot_id": "CTR-002"}
        result = await graph.ainvoke({"message": "the first one", "request_id": "discovery_request04"}, config)
        assert result["reservation_state"]["spot_id"] == "CTR-002"
        assert "first name" in result["final_reply"] and "vehicle plate" in result["final_reply"]
        state = (await graph.aget_state(config)).values
        assert len(state["messages"]) == 8 and len(state["evidence"]) == 4
        assert "SECRET" not in json.dumps(state["evidence"])
        assert not slot_store.pending()
    assert all(kwargs["facility"] == "CTR" and kwargs["slot_date"] == "2026-11-20" for args, kwargs in seen)


async def test_location_switch_and_no_unfiltered_queries(slot_store):
    model = DiscoveryModel(dates={"slot_date": "2026-11-20", "duration_hours": 6,
                                 "provided_fields": ["slot_date", "duration_hours"]})
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=slot_store)
    config = {"configurable": {"thread_id": "location-switch"}}
    await graph.ainvoke({"message": "City Centre on November 20 for six hours", "request_id": "switch_request001"}, config)
    model.facility, model.dates = "AIR", {"provided_fields": []}
    result = await graph.ainvoke({"message": "Airport instead", "request_id": "switch_request002"}, config)
    assert "AIR-001" in result["final_reply"] and "5 PLN/hour" in result["final_reply"]
    assert "30 PLN for 6 hours" in result["final_reply"] and "CTR-" not in result["final_reply"]
    state = (await graph.aget_state(config)).values
    assert state["parking_search"]["slot_date"] == "2026-11-20"
    assert state["evidence"]["2:1"]["sql_results"][0]["filters"]["facility"] == "AIR"


async def test_lookup_cannot_submit_even_a_complete_draft(slot_store):
    model = DiscoveryModel(dates={"start": "2026-11-20T16:00:00+01:00", "end": "2026-11-20T22:00:00+01:00",
        "provided_fields": ["start", "end"]}, draft={"spot_id": "CTR-001", "name": "Name", "surname": "Surname", "car_number": "DEMO"}, lookup=True)
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=slot_store)
    result = await graph.ainvoke({"message": "How much would that space cost?", "request_id": "lookup_request001"},
                               {"configurable": {"thread_id": "lookup-only"}})
    assert "48 PLN" in result["final_reply"] and "approval" in result["final_reply"]
    assert not slot_store.pending() and "__interrupt__" not in result


async def test_tool_cannot_select_space_from_different_location(slot_store):
    model = ScriptedModel([("update_reservation_draft", {"updates": {"spot_id": "AIR-001", "name": "SavedName"}}),
                           ("ask_missing_reservation_details", {})])
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=slot_store)
    config = {"configurable": {"thread_id": "scoped-choice"}}
    result = await graph.ainvoke({"message": "Book City Centre", "request_id": "choice_request001"}, config)
    assert model.tool_results[1].status == "error"
    assert not (await graph.aget_state(config)).values["booking_draft"].get("spot_id")
    assert (await graph.aget_state(config)).values["booking_draft"]["name"] == "SavedName"
    assert "AIR-001" not in result["final_reply"] and not slot_store.pending()


async def test_new_hold_invalidates_an_earlier_space_choice(slot_store):
    hold = slot_store.reserve("another-customer", "hold", {"spot_id": "CTR-001",
        "start": "2026-11-20T08:00:00+01:00", "end": "2026-11-20T10:00:00+01:00",
        "name": "PRIVATE", "surname": "PRIVATE", "car_number": "SECRET"}, "")
    model = ScriptedModel([("update_reservation_draft", {"updates": {"spot_id": "CTR-001"}}),
                           ("ask_missing_reservation_details", {})])
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=slot_store)
    result = await graph.ainvoke({"message": "Book the previously offered CTR-001", "request_id": "race_choice_00001"},
        {"configurable": {"thread_id": "choosing-customer"}})
    assert model.tool_results[1].status == "error"
    assert "CTR-001" not in result["final_reply"] and "CTR-002" in result["final_reply"]
    assert "SECRET" not in result["final_reply"] and "PRIVATE" not in result["final_reply"]
    assert [row["reservation_id"] for row in slot_store.pending()] == [hold["reservation_id"]]


async def test_unknown_location_never_runs_a_table_scan():
    from unittest.mock import Mock
    from parking.graph.discovery import ParkingDiscovery, reservation_question

    store = Mock()
    result = await ParkingDiscovery(store).lookup({"booking_draft": {}, "parking_search": {}})
    store.find_slots.assert_not_called()
    assert "Where would you like to park" in reservation_question(result)
