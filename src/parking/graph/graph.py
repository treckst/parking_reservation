"""Main graph composed from compiled policy, reservation and admin subgraphs."""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from parking.bookings import BookingStore
from parking.graph.admin import build_admin_graph
from parking.graph.collection import draft_snapshot, missing_details_question
from parking.graph.nodes import PolicyNodes
from parking.graph.policy import build_policy_graph
from parking.graph.reservation import build_reservation_graph
from parking.graph.schemas import AdminResult, GraphInput, GraphOutput, MainState
from parking.models import create_llm
from parking.retrieval import retrieve
from parking.settings import Settings


def build_graph(model_factory=create_llm, retriever=retrieve, *, checkpointer=None, booking_store=None):
    store = booking_store or BookingStore(Settings.from_env().booking_path)
    nodes = PolicyNodes(model_factory, retriever)
    workflow = StateGraph(MainState, input_schema=GraphInput, output_schema=GraphOutput)
    workflow.add_node("prepare", nodes.prepare)
    workflow.add_node("check_language", nodes.check_language)
    workflow.add_node("reject_language", nodes.reject_language)
    workflow.add_node("guard_input", nodes.guard_input)
    workflow.add_node("classify", nodes.classify)
    workflow.add_node("fallback", nodes.fallback)
    workflow.add_node("publish", nodes.publish)
    policy_graph = build_policy_graph(model_factory, retriever)
    reservation_graph = build_reservation_graph(model_factory, store)
    admin_graph = build_admin_graph(model_factory, store)
    workflow.add_node("policy", policy_graph.compile())
    workflow.add_node("reservation", reservation_graph.compile())
    workflow.add_node("admin", admin_graph.compile())

    def booking_reply(state):
        if state.get("booking_error"):
            if draft_snapshot(state.get("booking_draft", {}))["missing_fields"]:
                text = missing_details_question(state.get("booking_draft", {}))
            elif state["booking_error"] == "not_submitted":
                text = "Your details are saved. Would you like me to submit this reservation for approval?"
            else:
                text = "This spot cannot be reserved for that interval. Please check the spot and times."
        else:
            result = AdminResult.model_validate(state["admin_result"])
            if result.reservation_id != state["reservation_id"]:
                raise ValueError("Admin result belongs to another reservation")
            text = ("The administrator approved your reservation." if result.status == "approved" else
                    "Your reservation was rejected because it no longer meets the booking rules."
                    if result.reason else "The administrator rejected your reservation.")
        return {"final_reply": text, "messages": [AIMessage(content=text, id=f"assistant:{state['request_id']}")]}

    workflow.add_node("booking_reply", booking_reply)
    workflow.add_edge(START, "prepare")
    workflow.add_edge("prepare", "check_language")
    workflow.add_conditional_edges("check_language", lambda s: "guard_input" if s["is_english"] else "reject_language")
    workflow.add_edge("reject_language", END)
    workflow.add_conditional_edges("guard_input", lambda s: "fallback" if s["blocked"] else "classify")
    workflow.add_conditional_edges("classify", lambda s: {
        "policy": "policy", "reservation": "reservation", "unsupported": "fallback",
    }[s["intent"]["kind"]])
    workflow.add_edge("fallback", "publish")
    workflow.add_edge("publish", END)
    workflow.add_edge("policy", END)
    workflow.add_conditional_edges("reservation", lambda s: "admin" if s.get("reservation_id") else "booking_reply")
    workflow.add_edge("admin", "booking_reply")
    workflow.add_edge("booking_reply", END)
    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
