"""
LangGraph Simple Agent — Supplier Evaluation Demo
==================================================
Demonstrates all three DL1 criteria natively:

  C1 — Human Approval Gate : interrupt() pauses the graph when spend > threshold.
                             The workflow resumes from the exact same point after
                             human input — this is impossible to replicate in
                             AutoGen or CrewAI without rebuilding the framework.

  C2 — Readable Audit Log  : every node appends to reasoning_log in state.
                             The log is automatic — no extra code needed.

  C3 — Persistent Memory   : past_decisions live in the state dict.
                             With MemorySaver (SQLite in production), state
                             survives between runs without any external database.

"""
from operator import add
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from .shared_data import ORDER_REQUEST, PAST_DECISIONS, SUPPLIERS

DIVIDER = "-" * 56


# ── State ──────────────────────────────────────────────────────────────────────

class EvalState(TypedDict):
    order:             dict
    suppliers:         list
    past_decisions:    list          
    scores:            list
    selected_supplier: dict
    total_value:       float
    order_confirmed:   bool
    reasoning_log:     Annotated[list, add]   


# ── Scoring formula (from Design Document) ─────────────────────────────────────

def _score_suppliers(suppliers: list, past_decisions: list) -> list:
    """
    Final score = (S_reliability × 0.40) + (S_price × 0.35) + (S_delivery × 0.25)
    S values are normalised 0–100.  Late-delivery history deducts 20 from reliability.

    Design choice (Option A): pure Python — no LLM call in this node.
    LangGraph allows mixing deterministic steps and LLM steps in the same graph.
    AutoGen and CrewAI always route through the LLM for every step.
    This is a structural advantage for Betsy: rule-based scoring is faster,
    cheaper, and fully auditable without relying on LLM output variance.
    """
    past_index = {p["supplier_id"]: p for p in past_decisions}

    prices     = [s["price_per_unit"]  for s in suppliers]
    deliveries = [s["delivery_hours"]  for s in suppliers]
    min_p, max_p = min(prices),     max(prices)
    min_d, max_d = min(deliveries), max(deliveries)
    price_range    = max_p - min_p or 1
    delivery_range = max_d - min_d or 1

    scored = []
    for s in suppliers:
        p_score = 100 - ((s["price_per_unit"] - min_p)  / price_range)    * 100
        d_score = 100 - ((s["delivery_hours"] - min_d)  / delivery_range) * 100
        r_score = float(s["reliability_score"])
        penalty = ""

        # C3 in action: past delivery record changes the score this run
        if s["id"] in past_index and "late" in past_index[s["id"]].get("notes", "").lower():
            r_score = max(0.0, r_score - 20.0)
            penalty = " [−20 reliability: late delivery on record]"

        final = (r_score * 0.40) + (p_score * 0.35) + (d_score * 0.25)
        scored.append({**s, "final_score": round(final, 2), "penalty_note": penalty})

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored


# ── Nodes ──────────────────────────────────────────────────────────────────────

def evaluate_node(state: EvalState) -> dict:
    """Score every supplier and pick the top one."""
    scored   = _score_suppliers(state["suppliers"], state["past_decisions"])
    selected = scored[0]
    total    = round(selected["price_per_unit"] * state["order"]["quantity"], 2)

    return {
        "scores":            scored,
        "selected_supplier": selected,
        "total_value":       total,
        "reasoning_log": [
            f"[evaluate] Scored {len(scored)} suppliers. "
            f"Winner: {selected['name']} "
            f"(score {selected['final_score']:.1f}){selected['penalty_note']}. "
            f"Order total: €{total}."
        ],
    }


def decide_node(state: EvalState) -> dict:
    """C2 demonstrated: interrupt() fires when spend exceeds threshold."""
    threshold = state["order"]["approval_threshold"]
    total     = state["total_value"]
    selected  = state["selected_supplier"]

    if total > threshold:
        # ── HITL GATE ────────────────────────────────────────────────────────
        # The graph pauses HERE. It does not continue until Command(resume=...)
        # is sent. No equivalent exists natively in AutoGen or CrewAI.
        human_response = interrupt({
            "gate":    "G1 — Spend threshold exceeded",
            "reason":  f"Order value €{total} exceeds approval threshold €{threshold}.",
            "planned": (
                f"Order {state['order']['quantity']} units of {state['order']['item']} "
                f"from {selected['name']} @ €{selected['price_per_unit']}/unit."
            ),
            "action":  "Type 'approve' to confirm or anything else to cancel.",
        })
        approved = str(human_response).strip().lower() == "approve"
        gate_note = f"Gate G1 fired (€{total} > €{threshold}). Human response: '{human_response}'. Approved: {approved}."
    else:
        approved  = True
        gate_note = f"Gate G1 not triggered (€{total} ≤ €{threshold}). Auto-approved."

    return {
        "order_confirmed": approved,
        "reasoning_log":   [f"[decide] {gate_note}"],
    }


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_langgraph_agent(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()   # C4: in production, swap for SqliteSaver

    builder = StateGraph(EvalState)
    builder.add_node("evaluate", evaluate_node)
    builder.add_node("decide",   decide_node)
    builder.set_entry_point("evaluate")
    builder.add_edge("evaluate", "decide")
    builder.add_edge("decide",   END)

    return builder.compile(checkpointer=checkpointer)


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_langgraph_agent(interactive: bool = False) -> dict:
    """
    Run the demo agent.
    interactive=True : asks for real human input at the HITL gate.
    interactive=False: auto-approves (useful in run_all.py).
    """
    graph  = build_langgraph_agent()
    config = {"configurable": {"thread_id": "lg-demo-001"}}

    initial = {
        "order":             ORDER_REQUEST,
        "suppliers":         SUPPLIERS,
        "past_decisions":    PAST_DECISIONS,   # C4: memory injected via state
        "scores":            [],
        "selected_supplier": {},
        "total_value":       0.0,
        "order_confirmed":   False,
        "reasoning_log":     [],
    }

    print(f"\n  {'LangGraph Agent':^{len(DIVIDER) - 2}}")
    print(f"  {DIVIDER}")

    for update in graph.stream(initial, config, stream_mode="updates"):
        for node in update:
            print(f"    ✓ {node}")

    snap      = graph.get_state(config)
    gate_fired = bool(snap.next)

    if gate_fired:
        payload = snap.values.get("reasoning_log", [])
        print(f"\n    ⚡ HITL GATE FIRED  (C2 in action — graph is paused)")
        sel = snap.values.get("selected_supplier", {})
        print(f"    Supplier : {sel.get('name')} @ €{sel.get('price_per_unit')}/unit")
        print(f"    Total    : €{snap.values.get('total_value')}")

        if interactive:
            answer = input("\n    Your decision (approve / reject): ").strip()
        else:
            answer = "approve"
            print(f"    [demo mode] Auto-approving order.")

        for update in graph.stream(Command(resume=answer), config, stream_mode="updates"):
            for node in update:
                print(f"    ✓ {node}  (resumed after approval)")

    final = graph.get_state(config).values

    print(f"\n    Reasoning log (C3 — every step logged automatically):")
    for entry in final.get("reasoning_log", []):
        print(f"      {entry}")

    return {
        "framework":         "LangGraph",
        "selected_supplier": final.get("selected_supplier", {}).get("name", "—"),
        "total_value":       final.get("total_value", 0),
        "order_confirmed":   final.get("order_confirmed", False),
        "reasoning_log":     final.get("reasoning_log", []),
        "criteria_evidence": {
            "C1_scheduling_native": True,   # graph.invoke() runs standalone, no human message needed
            "C2_hitl_native":       True,   # interrupt() built-in — graph paused and resumed
            "C3_log_native":        True,   # reasoning_log accumulated automatically via state
        },
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_langgraph_agent(interactive=True)
