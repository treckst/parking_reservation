"""Context resolves only through typed intent and does not reuse old evidence."""

from langchain_core.messages import AIMessage, HumanMessage
import pytest

from parking.graph.nodes import PolicyNodes
from parking.graph.schemas import Intent


@pytest.mark.asyncio
async def test_contextual_followup_keeps_original_message_and_distinct_query():
    nodes = PolicyNodes(None, None)
    seen = []

    async def classify(schema, instructions, data):
        seen.append(data)
        return Intent(kind="policy", language="en", facilities=["CTR"], retrieval_question="CTR cancellation policy")

    nodes.ask = classify
    state = {
        "message": "And cancellation?", "request_id": "request_00000002",
        "messages": [HumanMessage(content="CTR hours?"), AIMessage(content="CTR opens 06:00."), HumanMessage(content="And cancellation?")],
        "queries": {"request_00000001": {"index": 1, "request_id": "request_00000001", "original_message": "CTR hours?", "retrieval_question": "CTR hours?"}},
    }
    update = await nodes.classify(state)
    assert update["query_index"] == 2
    assert update["queries"]["request_00000002"]["original_message"] == "And cancellation?"
    assert update["intent"]["facilities"] == ["CTR"]
    assert seen[0]["safe_history"][0]["text"] == "CTR hours?"


@pytest.mark.asyncio
async def test_ambiguous_facility_scope_uses_all_four():
    nodes = PolicyNodes(None, None)
    async def classify(*args):
        return Intent(kind="policy", language="en", facilities=[], retrieval_question="Opening hours")
    nodes.ask = classify
    update = await nodes.classify({"message": "Hours?", "request_id": "request_00000001"})
    assert update["intent"]["facilities"] == ["CTR", "RIV", "STA", "AIR"]
