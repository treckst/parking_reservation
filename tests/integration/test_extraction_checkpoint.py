"""Mandatory per-field extraction persists before an agent can ask or submit."""

import json
import sqlite3
from unittest.mock import Mock
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from parking.graph.graph import build_graph
from parking.graph.schemas import Intent, ReservationExtraction
from tests.extraction_helpers import updates
from tests.integration.test_admin_flow import BookingModel, store


class ExtractedModel(BookingModel):
    def __init__(self, patch, action=None):
        super().__init__(draft={})
        self.patch, self.action = patch, action
        self.inspections = []

    def with_structured_output(self, schema, **kwargs):
        delegate = super().with_structured_output(schema, **kwargs)
        model = self

        class Structured:
            async def ainvoke(self, messages):
                if schema is Intent:
                    return {"kind": "reservation", "language": "en", "facilities": ["AIR"],
                            "retrieval_question": json.loads(messages[-1].content)["message"]}
                if schema is ReservationExtraction:
                    return {"updates": model.patch}
                return await delegate.ainvoke(messages)
        return Structured()

    def bind_tools(self, tools, **kwargs):
        model = self

        class Bound:
            async def ainvoke(self, messages):
                if messages[-1].type == "tool" and messages[-1].name == "inspect_reservation_draft":
                    model.inspections.append(json.loads(messages[-1].content))
                if model.action:
                    return AIMessage(content="", tool_calls=[{"name": model.action, "args": {},
                        "id": str(uuid4()), "type": "tool_call"}])
                # Simulate the previous failure: the agent omits the update tool
                # and suggests a stale question. Only merged state may be rendered.
                return AIMessage(content="Please provide a date, start time and duration.")
        return Bound()


async def test_screenshot_fields_survive_restart_even_without_update_tool(store, tmp_path):
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO transport_slots (spot_id,slot_date,working_hours,hourly_price) VALUES ('AIR-001','2026-11-24','06:00-22:00',5)")
    path = str(tmp_path / "extracted.sqlite3")
    config = {"configurable": {"thread_id": "screenshot-case"}}
    model = ExtractedModel(updates({"facility": "AIR"}))
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        first = await graph.ainvoke({"message": "can you share more info related to the reservation near the airport?",
            "request_id": "extraction_000001"}, config)
        model.patch = updates({"spot_type": "standard", "slot_date": "2026-11-24",
            "start": "2026-11-24T15:00:00+01:00", "end": "2026-11-24T20:00:00+01:00"})
        second = await graph.ainvoke({"message": "i want to make the reservation on standart spot on 24th of november starting at 3 pm up to 20:00",
            "request_id": "extraction_000002"}, config)
        assert second["final_reply"] != first["final_reply"]
        assert "25 PLN" in second["final_reply"] and "15:00–20:00" in second["final_reply"]
        assert "Which space" in second["final_reply"] and "provide a date" not in second["final_reply"]
        assert model.inspections[-1]["draft"]["start"] == "2026-11-24T15:00:00+01:00"
        assert model.inspections[-1]["parking_search"]["spot_type"] == "standard"
        assert not store.pending()
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        model = ExtractedModel(updates({"name": "Sample", "surname": "Customer", "car_number": "DEMO123"}) +
            [{"field": "end", "operation": "clarify", "value": None}])
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Fictional customer details, but change my end time to later",
            "request_id": "extraction_000003"}, config)
        state = (await graph.aget_state(config)).values
        assert state["booking_draft"]["name"] == "Sample" and state["booking_draft"]["car_number"] == "DEMO123"
        assert state["booking_draft"]["start"] == "2026-11-24T15:00:00+01:00"
        assert state["booking_draft"]["end"] is None
        assert set(state["field_errors"]) == {"end"}
        assert "end time" in result["final_reply"] and "start time" not in result["final_reply"]
        assert "Sample" not in json.dumps(result)


async def test_unresolved_field_blocks_pending_until_corrected(store, tmp_path):
    patch = updates({"spot_id": "AIR-001", "start": "2026-11-13T15:00:00+01:00",
        "end": "2026-11-13T20:00:00+01:00", "name": "Sample", "surname": "Customer", "car_number": "DEMO123"})
    patch.append({"field": "spot_type", "operation": "clarify", "value": None})
    model = ExtractedModel(patch, "submit_reservation_draft")
    original = store.reserve
    store.reserve = Mock(wraps=original)
    config = {"configurable": {"thread_id": "pending-gate"}}
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "gate.sqlite3")) as saver:
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Book with a space type I need to clarify", "request_id": "readiness_0000001"}, config)
        store.reserve.assert_not_called()
        assert not model.inspections[-1]["ready"] and not store.pending()
        assert "space type" in result["final_reply"]
        model.patch = updates({"spot_type": "standard"})
        paused = await graph.ainvoke({"message": "standard, please submit", "request_id": "readiness_0000002"}, config)
        assert paused["__interrupt__"]
        state = (await graph.aget_state(config)).values
        assert not state["field_errors"] and state["parking_search"]["spot_type"] == "standard"
        assert store.reserve.call_count == 1 and len(store.pending()) == 1
        assert state["booking_draft"]["car_number"] == "DEMO123"
