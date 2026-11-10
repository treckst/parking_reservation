"""Server-managed persistence; only the final guard publishes public output."""

from langgraph.graph import END, START, StateGraph

from parking.graph.nodes import PolicyNodes
from parking.graph.schemas import MainState, PolicyOutput
from parking.models import create_llm
from parking.retrieval import retrieve


def build_policy_graph(model_factory=create_llm, retriever=retrieve):
    nodes = PolicyNodes(model_factory, retriever)
    workflow = StateGraph(MainState, output_schema=PolicyOutput)
    for name in ("retrieve", "assess", "rewrite", "compose", "fallback", "publish"):
        workflow.add_node(name, getattr(nodes, name))
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "assess")

    def after_assessment(state):
        if state["assessment"]["status"] != "insufficient":
            return "compose"
        return "rewrite" if state["attempt"] == 1 else "fallback"

    workflow.add_conditional_edges("assess", after_assessment)
    workflow.add_conditional_edges("rewrite", lambda s: "retrieve" if s["rewritten_question"] else "fallback")
    workflow.add_edge("compose", "publish")
    workflow.add_edge("fallback", "publish")
    workflow.add_edge("publish", END)
    return workflow
