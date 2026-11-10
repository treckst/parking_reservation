"""Main graph composed from compiled policy, reservation and admin subgraphs."""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from parking.bookings import BookingStore
from parking.graph.admin import build_admin_graph
from parking.graph.nodes import PolicyNodes
from parking.graph.policy import build_policy_graph
from parking.graph.reservation import build_reservation_graph
from parking.graph.schemas import GraphInput, GraphOutput, MainState
from parking.models import create_llm
from parking.retrieval import retrieve
from parking.settings import Settings


def build_graph(model_factory=create_llm, retriever=retrieve, *, checkpointer=None, booking_store=None):
    store = booking_store or BookingStore(Settings.from_env().booking_path)
    nodes = PolicyNodes(model_factory, retriever)
    workflow = StateGraph(MainState, input_schema=GraphInput, output_schema=GraphOutput)
    workflow.add_node("prepare", nodes.prepare)
    workflow.add_node("classify", nodes.classify)
    workflow.add_node("fallback", nodes.fallback)
    workflow.add_node("publish", nodes.publish)
    policy_graph = build_policy_graph(model_factory, retriever)
    reservation_graph = build_reservation_graph(model_factory, store)
    admin_graph = build_admin_graph(model_factory, store)
    workflow.add_node("policy", policy_graph.compile())
    workflow.add_node("reservation", reservation_graph.compile())
    workflow.add_node("admin", admin_graph.compile())

    def mock_node(state):
        # Placeholder for downstream work. The pending row already holds the slot.
        store.decide(state["reservation_id"], approved=True)
        return {}

    def reject(state):
        store.decide(state["reservation_id"], approved=False)
        return {}

    def booking_reply(state):
        if state.get("booking_error"):
            text = ("Please provide the spot, date, times with timezone offsets, name, surname and vehicle plate."
                    if state["booking_error"] == "missing_details" else
                    "This spot cannot be reserved for that interval. Please check the spot and times.")
        elif state["admin_decision"]["response"] == "approve":
            text = "The administrator approved your reservation."
        else:
            text = "The administrator rejected your reservation."
        if state["guard_language"] == "pl":
            text = {
                "Please provide the spot, date, times with timezone offsets, name, surname and vehicle plate.":
                    "Podaj miejsce, dat?, godziny ze stref? czasow?, imi?, nazwisko i numer rejestracyjny.",
                "This spot cannot be reserved for that interval. Please check the spot and times.":
                    "Nie mo?na zarezerwowa? miejsca w podanym terminie. Sprawd? miejsce i godziny.",
                "The administrator approved your reservation.": "Administrator zatwierdzi? rezerwacj?.",
                "The administrator rejected your reservation.": "Administrator odrzuci? rezerwacj?.",
            }[text]
        return {"final_reply": text, "messages": [AIMessage(content=text, id=f"assistant:{state['request_id']}")]}

    workflow.add_node("mock_node", mock_node)
    workflow.add_node("reject", reject)
    workflow.add_node("booking_reply", booking_reply)
    workflow.add_edge(START, "prepare")
    workflow.add_conditional_edges("prepare", lambda s: "fallback" if s["blocked"] else "classify")
    workflow.add_conditional_edges("classify", lambda s: {
        "policy": "policy", "reservation": "reservation", "unsupported": "fallback",
    }[s["intent"]["kind"]])
    workflow.add_edge("fallback", "publish")
    workflow.add_edge("publish", END)
    workflow.add_edge("policy", END)
    workflow.add_conditional_edges("reservation", lambda s: "admin" if s.get("reservation_id") else "booking_reply")
    workflow.add_conditional_edges("admin", lambda s: "mock_node" if s["admin_decision"]["response"] == "approve" else "reject")
    workflow.add_edge("mock_node", "booking_reply")
    workflow.add_edge("reject", "booking_reply")
    workflow.add_edge("booking_reply", END)
    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
