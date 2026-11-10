"""Real customer ToolNode calls with scripted model choices and isolated storage."""

import json
from uuid import uuid4

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from parking.graph.graph import build_graph
from tests.integration.test_admin_flow import BookingModel, DRAFT, store


async def test_partial_collection_restart_correction_and_submit(store, tmp_path):
    config = {"configurable": {"thread_id": "customer"}}
    checkpoint = str(tmp_path / "collection.sqlite3")
    first = {key: value for key, value in DRAFT.items() if key not in ("end", "car_number")}
    async with AsyncSqliteSaver.from_conn_string(checkpoint) as saver:
        graph = build_graph(lambda: BookingModel(draft=first), checkpointer=saver, booking_store=store)
        result = await graph.ainvoke({"message": "Book with these initial details", "request_id": "collection_00001"}, config)
        assert "__interrupt__" not in result and not store.pending()
        assert "end date and time" in result["final_reply"] and "vehicle plate" in result["final_reply"]
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
    assert "first name" not in result["final_reply"] and "surname" in result["final_reply"]
    assert not store.pending() and "__interrupt__" not in result


async def test_tools_cannot_update_admin_or_thread_state(store):
    model = ScriptedModel([
        ("update_reservation_draft", {"updates": {"name": "Name", "status": "approved",
                                                "admin_result": {}, "thread_id": "another"}}),
        ("ask_missing_reservation_details", {}),
    ])
    result, state = await run_collection(store, model)
    assert model.tool_results[0].status == "error"
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
    assert "Please provide" in result["final_reply"]
