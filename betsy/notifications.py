"""
betsy/notifications.py — HOTL and HITL notification handler

HOTL (Human-on-the-Loop): Betsy acts autonomously but notifies the user.
  - Order placed within approved limits
  - Delivery delay detected
  User has 1 hour to override by responding CANCEL.

HITL (Human-in-the-Loop): Betsy pauses and waits for approval.
  - Gate G1/G2/G3/G4/G5/G6 fired
  Handled by interrupt() in graph.py — this module formats the message.

All notifications go to THREE places:
  1. Windows desktop popup (corner of screen — shows even if terminal is minimised)
  2. Terminal — printed as a text block
  3. betsy_notifications.log — permanent text log
"""

import os
from datetime import datetime, timezone


def _desktop_notify(title: str, message: str, timeout: int = 8) -> None:
    """Show a Windows desktop toast notification in the corner of the screen."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Betsy Procurement Agent",
            timeout=timeout,
        )
    except Exception:
        pass  # desktop notification is best-effort — never crash the agent

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "betsy_notifications.log")

DIVIDER  = "=" * 62
DIVIDER2 = "-" * 62


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _write_log(lines: list[str]) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
        f.write("\n")


# ── HOTL: order placed automatically ──────────────────────────────────────────

def notify_order_placed(po: dict, supplier: dict) -> None:
    _desktop_notify(
        title="Betsy — Order Placed (HOTL)",
        message=(
            f"{po['part_id']} | {supplier['name']}\n"
            f"{po['quantity']} units @ €{po['unit_price']} = €{po['total_value']:,.2f}\n"
            f"No action needed. Override within 1 hour."
        ),
    )
    lines = [
        "",
        DIVIDER,
        f"  [HOTL] ORDER PLACED — {_now_str()}",
        DIVIDER,
        f"  Betsy placed an order automatically within your approved limits.",
        f"",
        f"  Part     : {po['part_id']}",
        f"  Supplier : {supplier['name']}",
        f"  Quantity : {po['quantity']} units @ €{po['unit_price']}/unit",
        f"  Total    : €{po['total_value']:,.2f}",
        f"  Expected : {po.get('expected_by', 'TBC')[:10]}",
        f"",
        f"  Why {supplier['name']}: highest reliability score in approved shortlist.",
        f"  No action needed. Override within 1 hour.",
        DIVIDER,
    ]
    for line in lines:
        print(line)
    _write_log(lines)


# ── HOTL: delivery delayed ─────────────────────────────────────────────────────

def notify_delivery_delayed(po_ids: list[str]) -> None:
    _desktop_notify(
        title="Betsy — Delivery Delayed (HOTL)",
        message=f"{len(po_ids)} overdue PO(s): {', '.join(po_ids[:3])}\nContact supplier. Check --status.",
        timeout=10,
    )
    lines = [
        "",
        DIVIDER,
        f"  [HOTL] DELIVERY DELAY — {_now_str()}",
        DIVIDER,
        f"  {len(po_ids)} purchase order(s) are overdue:",
    ]
    for po_id in po_ids:
        lines.append(f"    • {po_id}")
    lines += [
        f"",
        f"  Betsy has flagged these as delayed in the purchase_orders table.",
        f"  Review in --status mode. Contact supplier if needed.",
        DIVIDER,
    ]
    for line in lines:
        print(line)
    _write_log(lines)


# ── HITL: gate fired — format escalation payload for terminal ─────────────────

def notify_gate_fired(gate: str, gate_reason: str) -> None:
    """Desktop popup when a HITL gate fires — shown before the approval prompt."""
    _desktop_notify(
        title=f"Betsy — Gate {gate} Fired  ⚡  Action Required",
        message=f"{gate_reason}\n\nOpen the dashboard or terminal to approve or reject.",
        timeout=15,
    )


def format_gate_alert(gate: str, gate_reason: str, payload: dict) -> list[str]:
    """Return formatted lines for a HITL gate alert. Caller prints + logs."""
    lines = [
        "",
        DIVIDER,
        f"  [HITL] GATE {gate} — BETSY NEEDS YOUR APPROVAL",
        f"  {_now_str()}",
        DIVIDER,
        f"  Gate reason : {gate_reason}",
    ]

    planned = payload.get("what_betsy_planned")
    if planned:
        lines.append(f"  Betsy planned: {planned}")

    reasoning = payload.get("llm_reasoning")
    if reasoning:
        lines += ["", f"  Betsy's reasoning:", f"    {reasoning}"]

    alts = payload.get("alternatives", [])
    if alts:
        lines += ["", "  Alternatives considered:"]
        for a in alts:
            lines.append(f"    • {a['name']}: €{a['price']}/unit  score {a.get('score', '?')}")

    action = payload.get("action_required", "Type 'approve' or 'reject'.")
    lines += [
        "",
        f"  {action}",
        DIVIDER2,
    ]
    return lines


# ── G6 HOTL: stale data — no interrupt, just notify ───────────────────────────

def notify_stale_data(data_age_hours: float, threshold_hours: float) -> None:
    _desktop_notify(
        title="Betsy — Stale Inventory Data (G6)",
        message=(
            f"Data is {data_age_hours:.1f}h old (limit {threshold_hours:.0f}h).\n"
            f"No orders placed. Refresh inventory.csv and re-run."
        ),
        timeout=10,
    )
    lines = [
        "",
        DIVIDER,
        f"  [HOTL] STALE INVENTORY DATA — {_now_str()}",
        DIVIDER,
        f"  Inventory data is {data_age_hours:.1f}h old (threshold: {threshold_hours:.0f}h).",
        f"  Gate G6 fired. Betsy did NOT place any orders this cycle.",
        f"",
        f"  Action: refresh inventory.csv with current stock data, then re-run.",
        DIVIDER,
    ]
    for line in lines:
        print(line)
    _write_log(lines)


# ── Status summary ─────────────────────────────────────────────────────────────

def print_run_header(run_id: str, mode: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  BETSY PROCUREMENT AGENT — {mode.upper()}")
    print(f"  {_now_str()}  |  Run: {run_id[:8]}...")
    print(DIVIDER)
