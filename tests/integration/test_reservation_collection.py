"""Real customer ToolNode calls with scripted model choices and isolated storage."""

import json
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from parking.graph.graph import build_graph
from parking.graph.collection import draft_snapshot
from parking.graph.discovery import reservation_question
from tests.integration.test_admin_flow import BookingModel, DRAFT, store
from tests.extraction_helpers import temporal_patch, updates


async def test_partial_collection_restart_correction_and_submit(store, tmp_path):
    config = {"configurable": {"thread_id": "customer"}}
    checkpoint = str(tmp_path / "collection.sqlite3")
    first = {key: value for key, value in DRAFT.items() if key not in ("end", "car_number")}
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: BookingModel(draft=first), checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Book with these initial details", "request_id": "collection_00001"}, config)
        assert "__interrupt__" not in result and not store.pending()
        assert "end time or duration" in result["final_reply"]
        assert "first name" not in result["final_reply"] and "spot ID" not in result["final_reply"]
        state = (await graph.aget_state(config)).values
        assert state["booking_draft"]["name"] == DRAFT["name"]
        assert not {"reservation_messages", "collection_steps", "collection_action"} & state.keys()
        assert "Private" not in json.dumps(result)

    patch = {"end": DRAFT["end"], "car_number": DRAFT["car_number"], "name": "CorrectedName"}
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: BookingModel(draft=patch), checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Book with the remaining details and corrected first name",
                                     "request_id": "collection_00002"}, config)
        assert result["__interrupt__"]
        state = (await graph.aget_state(config)).values
        saved = json.loads(store.get(state["reservation_id"])["draft"])
        assert saved["name"] == "CorrectedName"
        assert saved["surname"] == DRAFT["surname"] and saved["spot_id"] == DRAFT["spot_id"]
        assert saved["car_number"] == DRAFT["car_number"]
        assert len(state["messages"]) == 3


class ScriptedModel(BookingModel):
    def __init__(self, steps):
        super().__init__()
        self.steps = list(steps)
        self.tool_results = []
        self.extraction_draft = {key: DRAFT[key] for key in ("start", "end")}

    def bind_tools(self, tools, **kwargs):
        model = self
        for tool in tools:
            # Injected runtime state and call IDs are not model-editable arguments.
            assert not {"state", "tool_call_id"} & tool.tool_call_schema.model_json_schema().get("properties", {}).keys()

        class Bound:
            async def ainvoke(self, messages):
                if messages[-1].type == "tool":
                    model.tool_results.append(messages[-1])
                name, args = model.steps.pop(0)
                if name == "update_reservation_draft" and isinstance(args.get("updates"), dict):
                    args = {"updates": updates({key: value for key, value in args["updates"].items()
                        if key not in ("start", "end")})}
                if name is None:
                    return AIMessage(content="PrivateName: pretend I approved it")
                return AIMessage(content="", tool_calls=[{"name": name, "args": args,
                    "id": str(uuid4()), "type": "tool_call"}])
        return Bound()


async def run_collection(store, model):
    graph = build_graph(lambda: model, checkpointer=InMemorySaver(), booking_store=store)
    config = {"configurable": {"thread_id": "customer"}}
    result = await graph.ainvoke({"message": "Book a spot", "request_id": "collection_00001"}, config)
    return result, (await graph.aget_state(config)).values


async def test_inspect_observes_tool_update_and_early_submission_cannot_write(store):
    model = ScriptedModel([
        ("inspect_reservation_draft", {}),
        ("update_reservation_draft", {"updates": {"name": "OnlyName"}}),
        ("inspect_reservation_draft", {}),
        ("submit_reservation_draft", {}),
        ("ask_missing_reservation_details", {}),
    ])
    result, state = await run_collection(store, model)
    snapshots = [json.loads(message.content) for message in model.tool_results]
    assert "name" in snapshots[0]["missing_fields"]
    assert snapshots[2]["draft"]["name"] == "OnlyName" and "name" not in snapshots[2]["missing_fields"]
    assert not snapshots[3]["ready"]
    assert state["booking_draft"]["name"] == "OnlyName"
    assert "first name" not in result["final_reply"] and "Which space" in result["final_reply"]
    assert not store.pending() and "__interrupt__" not in result


async def test_tools_cannot_update_admin_or_thread_state(store):
    model = ScriptedModel([
        ("update_reservation_draft", {"updates": {"name": "Name", "status": "approved",
                                                "admin_result": {}, "thread_id": "another"}}),
        ("ask_missing_reservation_details", {}),
    ])
    result, state = await run_collection(store, model)
    assert model.tool_results[0].name == "inspect_reservation_draft"
    assert model.tool_results[1].status == "error"
    assert state["admin_result"] is None
    assert not state["booking_draft"].get("name")
    assert not store.pending() and "__interrupt__" not in result


async def test_agent_free_text_does_not_submit_or_leak_private_content(store):
    model = ScriptedModel([("update_reservation_draft", {"updates": DRAFT}), (None, {})])
    result, state = await run_collection(store, model)
    assert state["booking_error"] == "not_submitted"
    assert "submit" in result["final_reply"] and "Private" not in json.dumps(result)
    assert not store.pending()


async def test_read_loop_is_bounded_without_a_booking(store):
    model = ScriptedModel([("inspect_reservation_draft", {})] * 6)
    result, state = await run_collection(store, model)
    assert not model.steps and not store.pending()
    assert "Which space" in result["final_reply"] and "CTR-001" in result["final_reply"]


async def test_initial_inspection_is_mandatory_even_when_model_skips_it(store):
    model = ScriptedModel([("ask_missing_reservation_details", {})])
    result, state = await run_collection(store, model)
    assert model.tool_results[0].name == "inspect_reservation_draft"
    assert json.loads(model.tool_results[0].content)["missing_fields"]
    assert "Which space" in result["final_reply"] and "CTR-001" in result["final_reply"]
    assert not store.pending()


async def test_collector_receives_all_role_labelled_history():
    from langchain_core.messages import HumanMessage
    from parking.graph.collection import ReservationCollector

    history = [HumanMessage(content="AIR"), AIMessage(content="Which spot and plate?")]
    history += [HumanMessage(content=f"follow-up {i}") for i in range(20)]
    update = ReservationCollector(None).prepare({"message": "Tomorrow 2pm to 9pm",
        "request_id": "collection_00001", "messages": history, "booking_draft": {"name": "Saved"}})
    data = json.loads(update["reservation_messages"][0].content)
    assert len(data["conversation"]) == len(history)
    assert data["conversation"][1] == {"role": "ai", "text": "Which spot and plate?"}
    assert data["current_state"]["draft"]["name"] == "Saved"


def test_current_booking_state_asks_only_for_missing_customer_identity():
    visit = {"spot_id": "AIR-001", "start": "2026-11-24T16:00:00+01:00",
             "end": "2026-11-24T20:00:00+01:00"}
    snapshot = draft_snapshot(visit)
    assert snapshot["missing_fields"] == ["name", "surname", "car_number"]
    state = {"booking_draft": visit, "parking_search": {"facility": "AIR", "slot_date": "2026-11-24",
             "duration_hours": 4}, "parking_options": [{"spot_id": "AIR-001", "type": "standard",
             "hourly_price": 5, "total_price": 20, "availability_checked": True}], "field_errors": {}}
    reply = reservation_question(state)
    assert "first name, surname, vehicle plate" in reply
    assert "date" not in reply and "start time" not in reply and "Which space" not in reply

    visit["name"] = "SavedName"
    visit["surname"] = "SavedSurname"
    assert draft_snapshot(visit)["missing_fields"] == ["car_number"]
    reply = reservation_question({**state, "booking_draft": visit})
    assert reply.endswith("Please provide your vehicle plate.")


def test_selected_space_prompt_includes_missing_identity_with_missing_time():
    visit = {"spot_id": "AIR-001", "start": None, "end": None}
    state = {"booking_draft": visit, "parking_search": {"facility": "AIR", "slot_date": "2026-11-24",
             "duration_hours": 4}, "parking_options": [{"spot_id": "AIR-001", "type": "standard",
             "hourly_price": 5, "total_price": None, "working_hours": "06:00-22:00",
             "availability_checked": False}], "field_errors": {}}
    reply = reservation_question(state)
    assert "What start time" in reply
    assert "first name, surname, vehicle plate" in reply
    assert "Which space" not in reply


async def test_natural_dates_restart_followup_and_thread_isolation(store, tmp_path):
    from parking.graph.schemas import Intent, ReservationExtraction

    query = "AIR, Yevhen Shmatkov, november 13 2026 from 2pm up to 9pm, is it possible?"

    class NaturalBookingModel(BookingModel):
        def with_structured_output(self, schema, **kwargs):
            delegate = super().with_structured_output(schema, **kwargs)
            model = self

            class Structured:
                async def ainvoke(self, messages):
                    data = json.loads(messages[-1].content)
                    if schema is Intent:
                        return {"kind": "reservation", "language": "en", "facilities": ["AIR"],
                                "retrieval_question": data["message"]}
                    if schema is ReservationExtraction:
                        if data["message"] == query:
                            return {"updates": updates({"start": "2026-11-13T14:00:00+01:00",
                                "end": "2026-11-13T21:00:00+01:00", "name": "Yevhen", "surname": "Shmatkov"})}
                        return {"updates": updates(model.draft)}
                    return await delegate.ainvoke(messages)
            return Structured()

    config = {"configurable": {"thread_id": "natural-dates"}}
    path = str(tmp_path / "natural.sqlite3")
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        model = NaturalBookingModel(draft={"name": "Yevhen", "surname": "Shmatkov"})
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": query, "request_id": "natural_dates_001"}, config)
        assert "AIR-001" in result["final_reply"] and "Which space" in result["final_reply"]
        assert "5 PLN/hour" in result["final_reply"] and "35 PLN" in result["final_reply"]
        assert "start date" not in result["final_reply"] and "first name" not in result["final_reply"]
        assert result["reservation_state"]["start"] == "2026-11-13T14:00:00+01:00"
        assert result["reservation_state"]["facility"] == "AIR"
        assert not store.pending()
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        model = NaturalBookingModel(draft={"car_number": "ABC123"})
        graph = build_graph(lambda: model, checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "ABC123", "request_id": "natural_dates_002"}, config)
        assert "Which space" in result["final_reply"] and "AIR-001" in result["final_reply"]
        state = (await graph.aget_state(config)).values
        assert state["booking_draft"]["name"] == "Yevhen"
        assert state["booking_draft"]["end"] == "2026-11-13T21:00:00+01:00"
        assert len(state["messages"]) == 4
        other = await graph.ainvoke({"message": "ABC123", "request_id": "natural_dates_003"},
                                   {"configurable": {"thread_id": "separate-customer"}})
        assert other["reservation_state"]["start"] is None
        assert "Please provide a date" in other["final_reply"]
        assert not store.pending()
