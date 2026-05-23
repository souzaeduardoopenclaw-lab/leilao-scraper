"""LangGraph compilation for Leilao scraper agent."""

from langgraph.graph import StateGraph, END

from agent.state import LeilaoState
from agent.nodes import (
    start_node,
    crawl_node,
    parse_node,
    aggregate_node,
    render_node,
    save_node,
    error_node,
)


def create_graph() -> StateGraph:
    """Create and compile the LangGraph state machine.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Define the graph
    graph = StateGraph(state_schema=LeilaoState)

    # Add nodes
    graph.add_node("start", start_node)
    graph.add_node("crawl", crawl_node)
    graph.add_node("parse", parse_node)
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("render", render_node)
    graph.add_node("save", save_node)
    graph.add_node("error", error_node)

    # Define edges
    # Start -> crawl (valid URL)
    graph.add_edge("start", "crawl")

    # Crawl -> parse (HTML received)
    graph.add_edge("crawl", "parse")

    # Parse -> aggregate (auctions extracted)
    graph.add_conditional_edges(
        "parse",
        lambda state: "aggregate" if state.get("status") in ("done", "parsing") else "error",
    )

    # Aggregate -> render (data cleaned)
    graph.add_edge("aggregate", "render")

    # Render -> save
    graph.add_conditional_edges(
        "render",
        lambda state: "save" if state.get("status") == "done" and state.get("markdown") else "error",
    )

    # Save -> end
    graph.add_edge("save", END)

    # Error handling - retry once then end
    graph.add_conditional_edges(
        "error",
        lambda state: "crawl" if state.get("metadata", {}).get("retry_count", 0) < 1 else END,
    )

    # Set entry point
    graph.set_entry_point("start")

    return graph


def get_compiled_graph() -> StateGraph:
    """Get the compiled graph for execution.

    Returns:
        Compiled StateGraph.
    """
    return create_graph().compile()