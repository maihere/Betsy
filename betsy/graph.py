import os
import sqlite3

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_STATE_DB = os.path.join(_DATA_DIR, "betsy_state.db")

from .nodes import (
    decide_node,
    evaluate_node,
    monitor_node,
    order_node,
    track_delivery_node,
    verify_node,
)
from .state import BetsyState


# ── Routing logic (edges with conditions) ─────────────────────────────────────

def _after_monitor(state: BetsyState) -> str:
    if state.get("gate") == "G6":
        return "human_approval"          # stale data → HOTL flag → stop
    if not state.get("low_stock_items"):
        if state.get("invoice"):
            return "track_delivery"      # invoice-only verification — skip ordering
        return END                       # nothing to do
    return "evaluate"


def _after_evaluate(state: BetsyState) -> str:
    if state.get("gate") == "G2":
        return "human_approval"          # no approved supplier → HITL
    return "decide"


def _after_decide(state: BetsyState) -> str:
    gate = state.get("gate")
    if gate in ("G1", "G3"):
        return "human_approval"          # spend or price spike → HITL
    if state.get("decision") == "order":
        return "order"
    return END                           # skip or escalate without gate


def _after_human_approval(state: BetsyState) -> str:
    """Route after Jenny approves or rejects the escalation."""
    approved = "approve" in (state.get("human_response") or "").lower()
    if not approved:
        return END

    gate = state.get("gate", "")
    if gate in ("G1", "G2", "G3"):
        return "order"                   # approved → proceed to order
    if gate in ("G4", "G5"):
        return END                       # invoice gates resolve at END
    if gate == "G6":
        return END                       # stale data — approved means user acknowledged
    return END


def _after_order(_: BetsyState) -> str:
    return "track_delivery"


def _after_track_delivery(_: BetsyState) -> str:
    return "verify"   # always verify — verify_node handles "no invoice" gracefully


def _after_verify(state: BetsyState) -> str:
    gate = state.get("gate")
    if gate in ("G4", "G5"):
        return "human_approval"          # mismatch or duplicate → HITL
    return END


# ── Human approval node (interrupt + resume) ──────────────────────────────────

def human_approval_node(state: BetsyState) -> dict:
    """
    This node uses LangGraph interrupt() to pause the workflow.
    The graph state is saved by the checkpointer. When the user sends
    Command(resume=answer), the graph resumes from this exact node.
    """
    from langgraph.types import interrupt

    payload = state.get("escalation_payload") or {
        "gate":           state.get("gate"),
        "reason":         state.get("gate_reason"),
        "action_required": "Type 'approve' or 'reject'.",
    }

    human_response = interrupt(payload)

    return {
        "human_response": human_response,
        "reasoning_log":  [
            f"[human_approval] Gate {state.get('gate')} — "
            f"human response: '{human_response}'."
        ],
    }


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """Build graph with an in-memory checkpointer (testing / proof scripts)."""
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(BetsyState)

    builder.add_node("monitor",         monitor_node)
    builder.add_node("evaluate",        evaluate_node)
    builder.add_node("decide",          decide_node)
    builder.add_node("human_approval",  human_approval_node)
    builder.add_node("order",           order_node)
    builder.add_node("track_delivery",  track_delivery_node)
    builder.add_node("verify",          verify_node)

    builder.set_entry_point("monitor")

    builder.add_conditional_edges("monitor",        _after_monitor)
    builder.add_conditional_edges("evaluate",       _after_evaluate)
    builder.add_conditional_edges("decide",         _after_decide)
    builder.add_conditional_edges("human_approval", _after_human_approval)
    builder.add_conditional_edges("order",          _after_order)
    builder.add_conditional_edges("track_delivery", _after_track_delivery)
    builder.add_conditional_edges("verify",         _after_verify)

    return builder.compile(checkpointer=checkpointer)


def build_persistent_graph():
    """
    Build graph with SqliteSaver — for production use.

    State survives process restarts. A HITL interrupt() can be resumed hours
    later by passing the same thread_id to Command(resume=...).

    The connection is kept open for the lifetime of the process.
    """
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_STATE_DB, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return build_graph(checkpointer=checkpointer)
