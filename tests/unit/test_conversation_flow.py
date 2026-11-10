"""General assistance routes around retrieval while retaining scoped state."""

import json

from langgraph.checkpoint.memory import InMemorySaver
import pytest

from parking.graph.graph import build_graph
from parking.graph.schemas import Intent
from tests.unit.test_policy_flow import DOCUMENT, Model


HELP_MESSAGES = ["can you help?", "Hello", "What can you do?", "How do I get started?", "Thanks"]


class ConversationModel(Model):
    def with_structured_output(self, schema, **kwargs):
        delegate = super().with_structured_output(schema, **kwargs)

        class Structured:
            async def ainvoke(self, messages):
                data = json.loads(messages[-1].content)
                if schema is Intent and data["message"] in HELP_MESSAGES:
                    instructions = messages[0].content
                    assert "Use conversation" in instructions
                    assert "parking reservation assistant" in instructions
                    return {"kind": "conversation", "language": "en", "facilities": [],
                            "retrieval_question": data["message"]}
                return await delegate.ainvoke(messages)
        return Structured()


@pytest.mark.parametrize("message", HELP_MESSAGES)
async def test_help_is_assistance_without_retrieval_or_booking(message):
    model = ConversationModel()

    def forbidden(*args):
        raise AssertionError("General help must not retrieve documents")

    graph = build_graph(lambda: model, forbidden, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "help"}}
    output = await graph.ainvoke({"message": message, "request_id": "help_request_0001"}, config)
    assert "request a parking reservation" in output["final_reply"]
    assert "Where would you like to park" in output["final_reply"]
    assert "does not support" not in output["final_reply"]
    assert "policy question" not in output["final_reply"]
    state = (await graph.aget_state(config)).values
    assert not state.get("booking_draft") and not state.get("reservation_id")
    assert not state.get("evidence")
    assert len(state["messages"]) == 2
    assert model.calls["EvidenceAssessment"] == model.calls["ReservationExtraction"] == 0


async def test_help_continues_missing_details_and_preserves_evidence():
    model = ConversationModel()
    queries = []

    def retrieve(question, facilities):
        queries.append(question)
        return [DOCUMENT]

    graph = build_graph(lambda: model, retrieve, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "existing-draft"}}
    await graph.ainvoke({"message": "Opening hours?", "request_id": "info_request_0001"}, config)
    draft = {"name": "PrivateName", "surname": "PrivateSurname", "spot_id": "AIR-001",
             "start": "2026-11-13T14:00:00+01:00", "end": "2026-11-13T21:00:00+01:00"}
    await graph.aupdate_state(config, {"booking_draft": draft})
    before = (await graph.aget_state(config)).values
    result = await graph.ainvoke({"message": "can you help?", "request_id": "help_request_0001"}, config)
    assert result["final_reply"] == "Yes, I can help you continue your parking reservation. Please provide your vehicle plate."
    after = (await graph.aget_state(config)).values
    assert after["booking_draft"] == draft
    assert after["evidence"] == before["evidence"]
    assert len(queries) == 1 and len(after["messages"]) == 4
    assert not after.get("reservation_id")
    assert "Private" not in json.dumps(result)


async def test_blocked_help_cannot_bypass_input_guard():
    model = ConversationModel(allowed=False)
    result = await build_graph(lambda: model, lambda *args: pytest.fail("Must not retrieve")).ainvoke(
        {"message": "can you help?", "request_id": "help_request_0001"})
    assert "cannot disclose" in result["final_reply"]


async def test_unknown_parking_fact_retains_limit_without_policy_only_redirect():
    model = ConversationModel(insufficient=2)
    result = await build_graph(lambda: model, lambda *args: []).ainvoke(
        {"message": "Are there helicopters at AIR?", "request_id": "info_request_0001"})
    assert "does not support" in result["final_reply"]
    assert "request a reservation" in result["final_reply"]
    assert "policy question" not in result["final_reply"]
