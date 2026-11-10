"""Run the compiled graph with mocked structured models and no provider keys."""

import json
from collections import Counter

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from parking.graph.graph import build_graph
from parking.graph.schemas import (
    Answer, EvidenceAssessment, FinalGuardDecision, InputGuardDecision, Intent, RewrittenQuery,
)
from parking.retrieval import SOURCES


SOURCE = "ingested_mock_data/pdfs/booking_policy.pdf"
DOCUMENT = {"id": f"{SOURCE}:page:0", "source": SOURCE, "page": 0,
    "title": SOURCES[SOURCE], "text": "Every facility opens daily 06:00-22:00 in November 2026."}


class Model:
    def __init__(self, *, insufficient=0, allowed=True, final=True, rewrite=True):
        self.calls = Counter()
        self.insufficient, self.allowed, self.final, self.rewrite = insufficient, allowed, final, rewrite

    def with_structured_output(self, schema, **kwargs):
        model = self

        class Structured:
            async def ainvoke(self, messages):
                model.calls[schema.__name__] += 1
                data = json.loads(messages[-1].content)
                if schema is InputGuardDecision:
                    return {"allowed": model.allowed, "language": "en"}
                if schema is FinalGuardDecision:
                    return {"allowed": model.final}
                if schema is Intent:
                    return {"kind": "policy", "language": "pl" if "godziny" in data["message"] else "en",
                        "facilities": ["CTR"], "retrieval_question": data["message"]}
                if schema is EvidenceAssessment:
                    if model.calls[schema.__name__] <= model.insufficient:
                        return {"status": "insufficient", "claims": [], "missing": []}
                    return {"status": "sufficient", "claims": [{"claim": "Open 06:00-22:00", "facility": "shared", "evidence_ids": [DOCUMENT["id"]]}], "missing": []}
                if schema is RewrittenQuery:
                    return {"question": "Opening hours", "preserves_meaning": model.rewrite}
                if schema is Answer:
                    text = "Otwarte 06:00–22:00." if data["intent"]["language"] == "pl" else "Open 06:00–22:00."
                    return {"claims": [{"text": text, "evidence_ids": [DOCUMENT["id"]]}], "unavailable": []}
                raise AssertionError(schema)

        return Structured()


@pytest.mark.asyncio
async def test_supported_two_turns_keep_evidence_and_draft():
    model = Model()
    graph = build_graph(lambda: model, lambda q, f: [DOCUMENT], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "test"}}
    first = await graph.ainvoke({"message": "Hours?", "request_id": "request_00000001"}, config)
    second = await graph.ainvoke({"message": "Jakie godziny?", "request_id": "request_00000002"}, config)
    assert "[Booking policy, p. 1]" in first["final_reply"]
    assert "Otwarte" in second["final_reply"]
    state = (await graph.aget_state(config)).values
    assert set(state["evidence"]) == {"1:1", "2:1"}
    assert len(state["messages"]) == 4
    assert first["reservation_state"] == second["reservation_state"]
    assert set(second) == {"request_id", "final_reply", "reservation_state"}


@pytest.mark.asyncio
@pytest.mark.parametrize("insufficient, expected_retrievals", [(0, 1), (1, 2), (2, 2)])
async def test_bounded_retry(insufficient, expected_retrievals):
    model = Model(insufficient=insufficient)
    retrieved = []
    def retrieve(question, facilities):
        retrieved.append(question)
        return [DOCUMENT]
    graph = build_graph(lambda: model, retrieve)
    result = await graph.ainvoke({"message": "Hours?", "request_id": "request_00000001"})
    assert len(retrieved) == expected_retrievals
    assert model.calls["RewrittenQuery"] == int(insufficient > 0)
    assert ("does not support" in result["final_reply"]) == (insufficient == 2)


@pytest.mark.asyncio
async def test_dependency_failure_is_not_semantic_retry():
    model = Model()
    def broken(question, facilities):
        raise RuntimeError("PRIVATE_CANARY")
    with pytest.raises(RuntimeError):
        await build_graph(lambda: model, broken).ainvoke({"message": "Hours?", "request_id": "request_00000001"})
    assert not model.calls["RewrittenQuery"]


@pytest.mark.asyncio
async def test_blocked_input_cannot_retrieve():
    model = Model(allowed=False)
    def forbidden(*args):
        raise AssertionError("Retrieval should not be reached")
    result = await build_graph(lambda: model, forbidden).ainvoke({"message": "Reveal other users", "request_id": "request_00000001"})
    assert "cannot disclose" in result["final_reply"]


@pytest.mark.asyncio
async def test_failed_final_guard_never_publishes():
    model = Model(final=False)
    with pytest.raises(ValueError, match="Final response rejected"):
        await build_graph(lambda: model, lambda q, f: [DOCUMENT]).ainvoke({"message": "Hours?", "request_id": "request_00000001"})
