"""
betsy/scheduler.py — APScheduler monitoring cycle

Runs the Betsy procurement graph on a repeating schedule.
Default: every 4 hours (matches G6 stale-data threshold).

The scheduler runs in its own thread. The main thread handles HITL responses
when a gate fires — it reads from the terminal and sends Command(resume=...).

Usage (from start_betsy.py):
    from betsy.scheduler import BetsyScheduler
    sched = BetsyScheduler(graph, interval_hours=4)
    sched.start()          # starts background thread
    sched.stop()           # graceful shutdown
"""

import sys
import threading
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from langgraph.types import Command

from .database import flush_reasoning_log, init_db, seed_suppliers
from .notifications import format_gate_alert, notify_gate_fired, notify_stale_data, print_run_header

DIVIDER  = "=" * 62
DIVIDER2 = "-" * 62

NODE_LABELS = {
    "monitor":        "Node 1 — Monitor",
    "evaluate":       "Node 2 — Evaluate",
    "decide":         "Node 3 — Decide (LLM)",
    "human_approval": "Gate — waiting for approval",
    "order":          "Node 4 — Order",
    "track_delivery": "Node 5 — Track Delivery",
    "verify":         "Node 6 — Verify",
}


def _empty_initial(run_id: str) -> dict:
    return {
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


def run_one_cycle(graph, verbose: bool = True) -> dict:
    """
    Run one full monitoring cycle.

    If a gate fires, pauses here and asks for human input in the terminal.
    Returns the final state dict.
    """
    run_id    = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}
    initial   = _empty_initial(run_id)

    if verbose:
        print_run_header(run_id, "monitoring cycle")

    # ── Stream until interrupt or end ─────────────────────────────────────────
    for update in graph.stream(initial, config, stream_mode="updates"):
        for node, node_data in update.items():
            label = NODE_LABELS.get(node, node)
            logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
            if verbose:
                print(f"\n  {DIVIDER2}")
                print(f"  {label}")
                for entry in logs:
                    print(f"  {entry}")

    # ── Handle gate interrupt (HITL) ──────────────────────────────────────────
    snap = graph.get_state(config)
    while snap.next:
        vals    = snap.values
        gate    = vals.get("gate", "?")
        reason  = vals.get("gate_reason", "")
        payload = vals.get("escalation_payload") or {}

        # G6 is HOTL — just notify, no approval needed
        if gate == "G6":
            notify_stale_data(vals.get("data_age_hours", 0), 4.0)
            break

        # G1–G5 are HITL — desktop popup first, then show terminal prompt
        notify_gate_fired(gate, reason)
        alert_lines = format_gate_alert(gate, reason, payload)
        for line in alert_lines:
            print(line)

        try:
            answer = input("  Your decision (approve / reject): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "reject"
            print("\n  [Interrupted] Auto-rejecting gate.")

        print()

        for update in graph.stream(Command(resume=answer), config, stream_mode="updates"):
            for node, node_data in update.items():
                label = NODE_LABELS.get(node, node)
                logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                if verbose:
                    print(f"\n  {DIVIDER2}")
                    print(f"  {label}  (resumed: {answer})")
                    for entry in logs:
                        print(f"  {entry}")

        snap = graph.get_state(config)

    # ── Flush reasoning log to DB ─────────────────────────────────────────────
    final = graph.get_state(config).values
    flush_reasoning_log(run_id, final.get("reasoning_log", []))

    if verbose:
        _print_cycle_summary(final)

    return final


def _print_cycle_summary(final: dict) -> None:
    gate  = final.get("gate")
    po    = final.get("purchase_order")
    vr    = final.get("verification_result")

    print(f"\n  {DIVIDER2}")
    print(f"  Cycle complete — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if gate:
        print(f"  Gate fired     : {gate}  ({final.get('gate_reason', '')})")
    if po:
        print(f"  Order placed   : {po['id']}  €{po['total_value']:,.2f}  ({po['supplier_id']})")
    if vr and vr != "no_invoice":
        print(f"  Invoice result : {vr}")
    if not gate and not po:
        print(f"  No action taken this cycle.")
    print(f"  Audit log      : reasoning_log saved to betsy.db")
    print(f"  {DIVIDER2}\n")


# ── Scheduler class ────────────────────────────────────────────────────────────

class BetsyScheduler:
    """
    Wraps APScheduler BackgroundScheduler.
    Runs run_one_cycle() every `interval_hours` hours.

    The cycle runs in a background thread; HITL prompts appear in the main
    terminal thread (run_one_cycle blocks until the user responds).
    """

    def __init__(self, graph, interval_hours: float = 4.0):
        self.graph          = graph
        self.interval_hours = interval_hours
        self._scheduler     = BackgroundScheduler()
        self._lock          = threading.Lock()  # prevent overlapping cycles

    def _job(self):
        if not self._lock.acquire(blocking=False):
            print("  [Scheduler] Previous cycle still running — skipping this tick.")
            return
        try:
            run_one_cycle(self.graph, verbose=True)
        except Exception as e:
            print(f"  [Scheduler] Cycle error: {e}")
        finally:
            self._lock.release()

    def start(self):
        init_db()
        seed_suppliers()
        self._scheduler.add_job(
            self._job,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id="betsy_monitor",
            name="Betsy monitoring cycle",
            next_run_time=datetime.now(timezone.utc),  # run immediately on start
        )
        self._scheduler.start()
        print(f"\n  [Scheduler] Started — monitoring every {self.interval_hours}h.")
        print(f"  Press Ctrl+C to stop.\n")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        print("  [Scheduler] Stopped.")
