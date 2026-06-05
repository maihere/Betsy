"""
start_betsy.py — Betsy Autonomous Procurement Agent
=====================================================
Production entry point. Four modes:

  python start_betsy.py --run              One monitoring cycle (interactive HITL)
  python start_betsy.py --schedule         Runs every 4h automatically (APScheduler)
  python start_betsy.py --status           Shows current DB state (POs, audit log)
  python start_betsy.py --demo g1          Demo: G1 spend gate (PART-001, 40 units)
  python start_betsy.py --demo g3          Demo: G3 price spike (PART-017, ViennaMach)
  python start_betsy.py --demo g4          Demo: G4 invoice mismatch (INV-TEST-001)
  python start_betsy.py --demo g5          Demo: G5 duplicate invoice (INV-TEST-DUP)

Architecture:
  - build_persistent_graph()  SqliteSaver checkpointer — state survives restarts
  - BetsyScheduler            APScheduler background thread — runs every 4h
  - run_one_cycle()           One full Monitor→Evaluate→Decide→Order→Verify pass
  - HITL: interrupt() pauses, user types approve/reject in terminal
  - HOTL: order_node and track_delivery_node print notifications + log to file
"""

import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from betsy.database import init_db, seed_suppliers, get_open_purchase_orders
from betsy.graph import build_persistent_graph
from betsy.scheduler import BetsyScheduler, run_one_cycle
from betsy.notifications import DIVIDER, DIVIDER2

import sqlite3
import os


# ══════════════════════════════════════════════════════════════════════════════
# --status: show current DB state
# ══════════════════════════════════════════════════════════════════════════════

def cmd_status() -> None:
    print(f"\n{DIVIDER}")
    print("  BETSY STATUS — betsy.db")
    print(DIVIDER)

    db_path = "betsy.db"
    if not os.path.exists(db_path):
        print("  betsy.db not found. Run --run first to initialise.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Open purchase orders
    print("\n  OPEN PURCHASE ORDERS:")
    print(f"  {'PO ID':<20} {'Part':<12} {'Supplier':<12} {'Total':>10} {'Status':<20} {'Expected'}")
    print(f"  {DIVIDER2}")
    rows = cur.execute(
        "SELECT id, part_id, supplier_id, total_value, status, delivery_status, expected_by "
        "FROM purchase_orders ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    if rows:
        for r in rows:
            print(f"  {r['id']:<20} {r['part_id']:<12} {r['supplier_id']:<12} "
                  f"€{r['total_value']:>8,.2f}  {r['status']:<20} {(r['expected_by'] or '')[:10]}")
    else:
        print("  No purchase orders yet.")

    # Recent audit log
    print(f"\n  RECENT AUDIT LOG (last 10 entries):")
    print(f"  {DIVIDER2}")
    rows = cur.execute(
        "SELECT run_id, node, gate, decision, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    if rows:
        for r in rows:
            ts      = (r["timestamp"] or "")[:16]
            node_col = (r["node"] or "")[:12]
            text    = (r["decision"] or "")[:80]
            print(f"  [{ts}] {node_col:<12} {text}")
    else:
        print("  No audit log entries yet.")

    # Pending invoices from CSV
    print(f"\n  PENDING INVOICES (invoices.csv):")
    inv_path = os.path.join("data", "invoices.csv")
    if os.path.exists(inv_path):
        import csv
        with open(inv_path, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("status", "").lower() == "pending"]
        if rows:
            for r in rows:
                print(f"  {r.get('invoice_id','?'):<18} PO:{r.get('po_id','?'):<14} "
                      f"€{float(r.get('amount',0)):>10,.2f}")
        else:
            print("  No pending invoices.")
    else:
        print("  invoices.csv not found.")

    # Notification log
    log_path = "betsy_notifications.log"
    if os.path.exists(log_path):
        lines = open(log_path, encoding="utf-8").readlines()
        recent = [l.rstrip() for l in lines[-20:] if l.strip()]
        if recent:
            print(f"\n  RECENT NOTIFICATIONS (betsy_notifications.log):")
            print(f"  {DIVIDER2}")
            for line in recent:
                print(f"  {line}")

    conn.close()
    print(f"\n{DIVIDER}\n")


# ══════════════════════════════════════════════════════════════════════════════
# --demo: inject specific gate scenarios
# ══════════════════════════════════════════════════════════════════════════════

DEMO_STATES = {
    "g1": {
        # PART-001, AccuParts, 40 units × €247 = €9,880 → G1
        "low_stock_items": [{
            "part_id": "PART-001", "part_name": "Bearing Assembly",
            "current_stock": "12", "reorder_threshold": "20",
            "reorder_quantity": "40", "assembly_line": "Line 2",
            "unit": "units", "data_timestamp": "2026-06-04T08:00:00",
        }],
        "invoice": None,
        "label": "G1 — Spend gate (PART-001, 40 units × €247 = €9,880 > €300)",
    },
    "g3": {
        # PART-017, ViennaMach, price spike 26.7% → G3
        # reorder_quantity=3 keeps total at 3×€95=€285 (under €300) so G1 does NOT fire
        # G3 then fires because €95 is 26.7% above last_price €75
        "low_stock_items": [{
            "part_id": "PART-017", "part_name": "Viton Seal Kit 32mm",
            "current_stock": "5", "reorder_threshold": "35",
            "reorder_quantity": "3", "assembly_line": "Line 2",
            "unit": "units", "data_timestamp": "2026-06-04T08:00:00",
        }],
        "invoice": None,
        "label": "G3 — Price spike (PART-017, ViennaMach +26.7% above last price, 3 units = €285 < €300)",
    },
    "g4": {
        # PART-002 (no gates on order), then INV-TEST-001 triggers G4 at verify
        "low_stock_items": [{
            "part_id": "PART-002", "part_name": "Hydraulic Seal Ring",
            "current_stock": "8", "reorder_threshold": "30",
            "reorder_quantity": "60", "assembly_line": "Line 1",
            "unit": "units", "data_timestamp": "2026-06-04T08:00:00",
        }],
        "invoice": {
            "id": "INV-TEST-001", "po_id": "PO-2025-005",
            "supplier_id": "SUP-003", "amount": 6200.00,
            "status": "pending", "received_at": "2026-06-04T10:00:00",
        },
        "label": "G4 — Invoice mismatch (INV-TEST-001: €6,200 vs PO-2025-005: €5,775)",
    },
    "g5": {
        # Invoice-only mode: no ordering step, just verify a duplicate invoice
        # INV-TEST-DUP has same supplier/PO/amount as INV-TEST-001 in invoices.csv → G5
        "low_stock_items": [],
        "invoice": {
            "id": "INV-TEST-DUP", "po_id": "PO-2025-005",
            "supplier_id": "SUP-003", "amount": 6200.00,
            "status": "pending", "received_at": "2026-06-04T12:00:00",
        },
        "label": "G5 — Duplicate invoice (INV-TEST-DUP: matches INV-TEST-001 — same supplier, PO, amount €6,200)",
    },
}


def cmd_demo(scenario: str, graph) -> None:
    demo = DEMO_STATES.get(scenario.lower())
    if not demo:
        print(f"  Unknown demo '{scenario}'. Choose: g1, g3, g4, g5")
        return

    print(f"\n{DIVIDER}")
    print(f"  DEMO: {demo['label']}")
    print(DIVIDER)

    import uuid
    from betsy.database import flush_reasoning_log
    from langgraph.types import Command
    from betsy.notifications import format_gate_alert, notify_stale_data

    run_id    = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    initial = {
        "run_id":              run_id,
        "inventory_snapshot":  [],
        "low_stock_items":     demo["low_stock_items"],
        "data_age_hours":      0.0,
        "candidate_suppliers": [],
        "selected_supplier":   None,
        "order_quantity":      0,
        "order_value":         0.0,
        "decision":            "",
        "purchase_order":      None,
        "invoice":             demo.get("invoice"),
        "verification_result": None,
        "gate":                None,
        "gate_reason":         None,
        "escalation_payload":  None,
        "human_response":      None,
        "reasoning_log":       [],
    }

    NODE_LABELS = {
        "monitor":        "Node 1 — Monitor",
        "evaluate":       "Node 2 — Evaluate",
        "decide":         "Node 3 — Decide (LLM)",
        "human_approval": "Gate — waiting for approval",
        "order":          "Node 4 — Order",
        "track_delivery": "Node 5 — Track Delivery",
        "verify":         "Node 6 — Verify",
    }

    for update in graph.stream(initial, config, stream_mode="updates"):
        for node, node_data in update.items():
            label = NODE_LABELS.get(node, node)
            logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
            print(f"\n  {DIVIDER2}")
            print(f"  {label}")
            for entry in logs:
                print(f"  {entry}")

    snap = graph.get_state(config)
    while snap.next:
        vals    = snap.values
        gate    = vals.get("gate", "?")
        reason  = vals.get("gate_reason", "")
        payload = vals.get("escalation_payload") or {}

        if gate == "G6":
            notify_stale_data(vals.get("data_age_hours", 0), 4.0)
            break

        for line in format_gate_alert(gate, reason, payload):
            print(line)

        try:
            answer = input("  Your decision (approve / reject): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "reject"
            print("\n  Auto-rejecting.")

        print()
        for update in graph.stream(Command(resume=answer), config, stream_mode="updates"):
            for node, node_data in update.items():
                label = NODE_LABELS.get(node, node)
                logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                print(f"\n  {DIVIDER2}")
                print(f"  {label}  (resumed: {answer})")
                for entry in logs:
                    print(f"  {entry}")
        snap = graph.get_state(config)

    final = graph.get_state(config).values
    flush_reasoning_log(run_id, final.get("reasoning_log", []))

    print(f"\n{DIVIDER}")
    print("  REASONING LOG")
    print(DIVIDER)
    for i, entry in enumerate(final.get("reasoning_log", []), 1):
        print(f"  {i:>2}. {entry}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Always initialise DB first
    init_db()
    seed_suppliers()

    mode = args[0].lstrip("-").lower()

    # ── --status ──────────────────────────────────────────────────────────────
    if mode == "status":
        cmd_status()
        return

    # ── All other modes need the graph ────────────────────────────────────────
    print("\n  Building agent graph (persistent checkpointer)...")
    graph = build_persistent_graph()
    print("  Graph ready.\n")

    # ── --run ─────────────────────────────────────────────────────────────────
    if mode == "run":
        run_one_cycle(graph, verbose=True)

    # ── --schedule ────────────────────────────────────────────────────────────
    elif mode == "schedule":
        interval = 4.0
        for a in args:
            if a.startswith("--interval="):
                try:
                    interval = float(a.split("=")[1])
                except ValueError:
                    pass

        scheduler = BetsyScheduler(graph, interval_hours=interval)
        scheduler.start()
        try:
            while True:
                time.sleep(30)
        except KeyboardInterrupt:
            scheduler.stop()

    # ── --demo ────────────────────────────────────────────────────────────────
    elif mode == "demo":
        scenario = args[1] if len(args) > 1 else "g1"
        cmd_demo(scenario, graph)

    else:
        print(f"  Unknown mode: {mode}")
        print("  Use --run, --schedule, --status, or --demo g1/g3/g4")


if __name__ == "__main__":
    main()
