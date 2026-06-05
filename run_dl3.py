"""
run_dl3.py  —  DL3 Skeleton Agent Proof
========================================
Proves the workflow design works:
  - All 6 nodes execute in the correct order
  - The graph pauses at the right gate (interrupt fires on real data)
  - Every node logs a WHAT/WHY/NEXT reasoning entry
  - Human approve/reject resumes or ends the workflow

Reads from real inventory.csv and suppliers.csv — nothing injected.
Graph structure, data schema, and scoring formula are in the Design Document.

Usage:
    python run_dl3.py
"""

import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from langgraph.types import Command

from betsy.database import flush_reasoning_log, init_db, seed_suppliers
from betsy.graph import build_graph

DIVIDER  = "=" * 62
DIVIDER2 = "-" * 62

NODE_LABEL = {
    "monitor":        "Node 1 — Monitor",
    "evaluate":       "Node 2 — Evaluate",
    "decide":         "Node 3 — Decide (LLM)",
    "human_approval": "Gate — Human Approval",
    "order":          "Node 4 — Order",
    "track_delivery": "Node 5 — Track Delivery",
    "verify":         "Node 6 — Verify",
}


def run() -> None:
    print(f"\n{DIVIDER}")
    print("  BETSY — DL3 SKELETON AGENT PROOF")
    print(f"  Data: inventory.csv  suppliers.csv  betsy.db")
    print(DIVIDER)

    init_db()
    seed_suppliers()

    graph     = build_graph()
    run_id    = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial = {
        "run_id":              run_id,
        "inventory_snapshot":  [],
        "low_stock_items":     [],
        "data_age_hours":      0.0,
        "candidate_suppliers": [],
        "selected_supplier":   None,
        "order_quantity":      0,
        "order_value":         0.0,
        "decision":            "",
        "purchase_order":      None,
        "invoice":             None,
        "verification_result": None,
        "gate":                None,
        "gate_reason":         None,
        "escalation_payload":  None,
        "human_response":      None,
        "reasoning_log":       [],
    }

    print(f"\n  Run: {run_id[:8]}...\n")

    # ── Stream until interrupt or end ──────────────────────────────────────────
    for update in graph.stream(initial, config, stream_mode="updates"):
        for node, node_data in update.items():
            label = NODE_LABEL.get(node, node)
            logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
            print(f"  {DIVIDER2}")
            print(f"  {label}")
            for entry in logs:
                print(f"  {entry}")

    # ── Gate interrupt ─────────────────────────────────────────────────────────
    snap = graph.get_state(config)
    while snap.next:
        vals    = snap.values
        gate    = vals.get("gate", "?")
        payload = vals.get("escalation_payload") or {}

        print(f"\n  {DIVIDER2}")
        print(f"  GATE {gate} — workflow paused at interrupt()")
        print(f"  Reason   : {vals.get('gate_reason', '')}")
        if payload.get("what_betsy_planned"):
            print(f"  Planned  : {payload['what_betsy_planned']}")
        if payload.get("llm_reasoning"):
            print(f"  Reasoning: {payload['llm_reasoning']}")
        alts = payload.get("alternatives", [])
        if alts:
            print("  Alternatives:")
            for a in alts:
                print(f"    {a['name']}  EUR {a['price']}/unit  score {a.get('score','?')}")
        print(f"\n  {payload.get('action_required', 'Type approve or reject:')}")
        print(f"  {DIVIDER2}")

        try:
            answer = input("  Your decision: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "reject"
            print("  (auto-reject)")

        print()
        for update in graph.stream(Command(resume=answer), config, stream_mode="updates"):
            for node, node_data in update.items():
                label = NODE_LABEL.get(node, node)
                logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                print(f"  {DIVIDER2}")
                print(f"  {label}  (resumed: {answer})")
                for entry in logs:
                    print(f"  {entry}")

        snap = graph.get_state(config)

    # ── Reasoning log ──────────────────────────────────────────────────────────
    final = graph.get_state(config).values
    flush_reasoning_log(run_id, final.get("reasoning_log", []))

    print(f"\n{DIVIDER}")
    print("  REASONING LOG  (saved to betsy.db audit_log)")
    print(DIVIDER)
    for i, entry in enumerate(final.get("reasoning_log", []), 1):
        print(f"  {i:>2}. {entry}")

    gate = final.get("gate")
    po   = final.get("purchase_order")
    vr   = final.get("verification_result")
    print(f"\n  Gate fired     : {gate or 'none'}")
    if po:
        print(f"  PO created     : {po['id']}  EUR {po['total_value']:,.2f}")
    if vr and vr != "no_invoice":
        print(f"  Invoice result : {vr}")
    print(f"  Audit log      : saved to betsy.db")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
