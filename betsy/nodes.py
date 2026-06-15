"""
betsy/nodes.py  —  All 6 procurement nodes.

Every reasoning_log entry follows the WHAT / WHY / NEXT format:
  WHAT: what Betsy observed or decided
  WHY:  the rule or data that drove it
  NEXT: what happens as a result (next node, gate, or end)
"""

import csv
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langsmith import traceable

from .database import (
    check_duplicate_invoice,
    get_approved_suppliers_for_part,
    get_pending_invoices_from_csv,
    get_po_total,
    get_price_average,
    record_price_history,
    save_invoice,
    save_purchase_order,
    update_invoice_status,
    update_po_delivery_status,
    update_supplier_reliability,
    get_open_purchase_orders,
)
from .prompts import DECIDE_PROMPT
from .state import BetsyState

DATA_DIR       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INVENTORY_CSV  = os.path.join(DATA_DIR, "inventory.csv")

_llm = ChatOllama(model="llama3.2:3b", format="json", temperature=0)


@traceable(run_type="llm", name="supplier-selection-llm")
def _invoke_llm(prompt: str) -> str:
    """Traced LLM call — visible in LangSmith as a named span inside decide_node."""
    response = _llm.invoke([HumanMessage(content=prompt)])
    return response.content

APPROVAL_THRESHOLD  = 300.0      # G1 — €300 (DL2 tail-spend boundary)
PRICE_SPIKE_PCT     = 0.15       # G3 — 15 %
STALE_HOURS         = 4.0        # G6 — 4 hours

def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Scoring formula (Design Document) ─────────────────────────────────────────

def _score_suppliers(suppliers: list) -> list:
    """
    Final score = (S_reliability × 0.40) + (S_price × 0.35) + (S_delivery × 0.25)
    reliability_score already on 0–100 scale (seeded from CSV × 100).
    delivery_days converted to hours for normalisation.
    """
    prices     = [s["price_per_unit"]           for s in suppliers]
    deliveries = [s["delivery_days"] * 24        for s in suppliers]  # days → hours
    min_p, max_p = min(prices),     max(prices)
    min_d, max_d = min(deliveries), max(deliveries)
    p_range = max_p - min_p or 1
    d_range = max_d - min_d or 1

    scored = []
    for s in suppliers:
        p_score = 100 - ((s["price_per_unit"] - min_p) / p_range) * 100
        d_hours = s["delivery_days"] * 24
        d_score = 100 - ((d_hours - min_d) / d_range) * 100
        r_score = float(s["reliability_score"])   # already 0–100
        final   = (r_score * 0.40) + (p_score * 0.35) + (d_score * 0.25)
        scored.append({**s, "final_score": round(final, 2)})

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored


# ── Node 1: Monitor ────────────────────────────────────────────────────────────

def monitor_node(state: BetsyState) -> dict:
    # Invoice-only verification mode: skip inventory read entirely
    if state.get("invoice") and not state.get("low_stock_items"):
        return {
            "low_stock_items": [],
            "data_age_hours":  0.0,
            "reasoning_log": [
                "WHAT: invoice verification requested — skipping inventory check. "
                "WHY: invoice pre-specified, no ordering step needed. "
                "NEXT: routing directly to track_delivery and verify nodes."
            ],
        }

    # Demo / test: if low_stock_items already injected, pass through without reading CSV
    if state.get("low_stock_items"):
        return {
            "data_age_hours": 0.0,
            "reasoning_log": [
                "WHAT: inventory items pre-injected by demo mode. "
                "WHY: skip CSV read — running a specific gate test scenario. "
                f"NEXT: {len(state['low_stock_items'])} item(s) passed to evaluate_node."
            ],
        }

    try:
        if not os.path.exists(INVENTORY_CSV):
            return {
                "inventory_snapshot": [],
                "low_stock_items":    [],
                "data_age_hours":     0.0,
                "gate":               None,
                "gate_reason":        None,
                "reasoning_log": [
                    "WHAT: inventory.csv not found. "
                    "WHY: file missing from data/. "
                    "NEXT: ending run — no data to process."
                ],
            }

        with open(INVENTORY_CSV, newline="", encoding="utf-8") as f:
            snapshot = list(csv.DictReader(f))

        # G6: data freshness check
        data_age_hours = 0.0
        if snapshot:
            ts_str = snapshot[0].get("data_timestamp", "")
            try:
                # Handle both offset-aware and naive timestamps
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                data_age_hours = (_now() - ts).total_seconds() / 3600
            except ValueError:
                data_age_hours = 0.0

        low_stock = [
            row for row in snapshot
            if int(row["current_stock"]) < int(row["reorder_threshold"])
        ]

        gate = gate_reason = None
        if data_age_hours > STALE_HOURS:
            gate        = "G6"
            gate_reason = (
                f"Inventory data is {data_age_hours:.1f}h old "
                f"(threshold: {STALE_HOURS}h)."
            )
            log = (
                f"WHAT: inventory data is stale ({data_age_hours:.1f}h old). "
                f"WHY: G6 rule — data older than {STALE_HOURS}h cannot be trusted for ordering. "
                f"NEXT: G6 HOTL flag raised — notifying user, halting order cycle."
            )
        else:
            log = (
                f"WHAT: read {len(snapshot)} inventory rows, "
                f"found {len(low_stock)} below reorder threshold. "
                f"WHY: current_stock < reorder_threshold for each flagged item. "
                f"NEXT: {'passing to evaluate_node.' if low_stock else 'no low-stock items — ending run.'}"
            )

        return {
            "inventory_snapshot": snapshot,
            "low_stock_items":    low_stock,
            "data_age_hours":     data_age_hours,
            "gate":               gate,
            "gate_reason":        gate_reason,
            "reasoning_log":      [log],
        }
    except Exception as e:
        return {
            "low_stock_items": [],
            "data_age_hours":  0.0,
            "reasoning_log": [
                f"WHAT: monitor_node encountered an error and could not complete. "
                f"WHY: Exception — {e!r}. "
                f"NEXT: Cycle halted at monitor_node. Review audit_log for this run_id."
            ],
        }


# ── Node 2: Evaluate ───────────────────────────────────────────────────────────

def evaluate_node(state: BetsyState) -> dict:
    try:
        item    = state["low_stock_items"][0]
        part_id = item["part_id"]

        suppliers = get_approved_suppliers_for_part(part_id)

        if not suppliers:
            return {
                "candidate_suppliers": [],
                "gate":        "G2",
                "gate_reason": f"No approved suppliers found for {part_id}.",
                "reasoning_log": [
                    f"WHAT: no approved suppliers found for {part_id}. "
                    f"WHY: G2 rule — cannot place an order without a vetted supplier. "
                    f"NEXT: G2 HITL interrupt — human must add an approved supplier."
                ],
            }

        scored = _score_suppliers(suppliers)
        top    = scored[0]

        log = (
            f"WHAT: scored {len(scored)} approved supplier(s) for {part_id}. "
            f"WHY: formula = reliability×0.40 + price×0.35 + delivery×0.25. "
            f"NEXT: passing top candidate {top['name']} (score {top['final_score']:.1f}) to decide_node."
        )

        return {
            "candidate_suppliers": scored,
            "gate":                None,
            "gate_reason":         None,
            "reasoning_log":       [log],
        }
    except Exception as e:
        return {
            "candidate_suppliers": [],
            "reasoning_log": [
                f"WHAT: evaluate_node encountered an error and could not complete. "
                f"WHY: Exception — {e!r}. "
                f"NEXT: Cycle halted at evaluate_node. Review audit_log for this run_id."
            ],
        }


# ── Node 3: Decide (LLM) ───────────────────────────────────────────────────────

def decide_node(state: BetsyState) -> dict:
    candidates = state["candidate_suppliers"]
    if not candidates:
        return {
            "decision":      "skip",
            "reasoning_log": [
                "WHAT: no candidates available. "
                "WHY: evaluate_node returned empty list. "
                "NEXT: skipping order this cycle."
            ],
        }

    item     = state["low_stock_items"][0]
    part_id  = item["part_id"]
    quantity = int(item.get("reorder_quantity", int(item["reorder_threshold"]) * 2))

    # ── LLM call — isolated so a failure falls back gracefully ────────────────
    try:
        table_lines = ["id | name | price | last_price | delivery_days | reliability | score"]
        for s in candidates:
            table_lines.append(
                f"{s['id']} | {s['name']} | €{s['price_per_unit']} "
                f"| €{s.get('last_price', 'N/A')} "
                f"| {s['delivery_days']}d | {s['reliability_score']:.0f} | {s['final_score']}"
            )
        prompt = DECIDE_PROMPT.format(
            item_id=part_id,
            quantity=quantity,
            suppliers_table="\n".join(table_lines),
        )
        raw_content = _invoke_llm(prompt)
        try:
            result = json.loads(raw_content)
        except (json.JSONDecodeError, AttributeError):
            result = {}
        selected_id = result.get("selected_supplier_id", candidates[0]["id"])
        reasoning   = result.get("reasoning", "No reasoning returned — using top-scored supplier.")
        selected    = next((s for s in candidates if s["id"] == selected_id), candidates[0])
    except Exception as llm_err:
        # Ollama unavailable or returned garbage — fall back to top-scored supplier.
        selected  = candidates[0]
        reasoning = f"LLM unavailable ({llm_err!r}) — defaulting to highest-scored supplier."

    # LLM provides supplier choice and reasoning only.
    # Prices and quantities always come from the actual supplier data — never trusted from LLM output.
    unit_price  = float(selected["price_per_unit"])   # real price from DB/CSV
    order_qty   = quantity                             # real quantity from inventory
    total_value = round(unit_price * order_qty, 2)

    # ── G1: spend threshold ────────────────────────────────────────────────────
    gate = gate_reason = escalation = None
    if total_value > APPROVAL_THRESHOLD:
        gate        = "G1"
        gate_reason = (
            f"Order value €{total_value:,.2f} exceeds approval threshold "
            f"€{APPROVAL_THRESHOLD:,.0f}."
        )
        escalation = {
            "what_betsy_planned": (
                f"Order {order_qty} units of {part_id} from {selected['name']} "
                f"@ €{unit_price}/unit = €{total_value:,.2f}"
            ),
            "why_gate_fired":     gate_reason,
            "llm_reasoning":      reasoning,
            "alternatives": [
                {"name": s["name"], "price": s["price_per_unit"], "score": s["final_score"]}
                for s in candidates[1:3]
            ],
            "action_required": "Type 'approve' to confirm or 'reject' to cancel.",
        }

    # ── G3: price spike (only if G1 not already set) ───────────────────────────
    # Use last_price (curated baseline from suppliers CSV) as the primary reference.
    # Fall back to price_history rolling average only when last_price is not set.
    if not gate:
        last_price = selected.get("last_price")
        avg_price  = get_price_average(selected["id"], part_id, n=3)
        baseline   = last_price if last_price else avg_price
        if baseline and float(baseline) > 0:
            spike_pct = (unit_price - float(baseline)) / float(baseline)
            if spike_pct > PRICE_SPIKE_PCT:
                ref_label = f"last price €{baseline}" if last_price else f"avg of last prices €{baseline:.2f}"
                gate        = "G3"
                gate_reason = (
                    f"Price spike: €{unit_price} vs {ref_label} "
                    f"({spike_pct * 100:.1f}% increase, threshold "
                    f"{PRICE_SPIKE_PCT * 100:.0f}%)."
                )
                escalation = {
                    "what_betsy_planned": (
                        f"Order {order_qty} units of {part_id} from {selected['name']} "
                        f"@ €{unit_price}/unit"
                    ),
                    "why_gate_fired":     gate_reason,
                    "llm_reasoning":      reasoning,
                    "alternatives": [
                        {"name": s["name"], "price": s["price_per_unit"], "score": s["final_score"]}
                        for s in candidates[1:3]
                    ],
                    "action_required": "Type 'approve' to accept new price or 'reject' to renegotiate.",
                }

    # Record price observation after gate checks so history doesn't inflate the baseline
    record_price_history(selected["id"], part_id, unit_price)

    log = (
        f"WHAT: selected {selected['name']} for {order_qty} × {part_id} "
        f"@ €{unit_price} = €{total_value:,.2f}. "
        f"WHY: {reasoning} "
        f"NEXT: {'Gate ' + gate + ' triggered — ' + gate_reason if gate else 'no gate — proceeding to order_node.'}"
    )

    return {
        "selected_supplier":  selected,
        "order_quantity":     order_qty,
        "order_value":        total_value,
        "decision":           "escalate" if gate else "order",
        "gate":               gate,
        "gate_reason":        gate_reason,
        "escalation_payload": escalation,
        "reasoning_log":      [log],
    }


# ── Node 4: Order ──────────────────────────────────────────────────────────────

def order_node(state: BetsyState) -> dict:
    try:
        supplier = state["selected_supplier"]
        item     = state["low_stock_items"][0]

        po = {
            "id":              f"PO-{uuid.uuid4().hex[:8].upper()}",
            "run_id":          state["run_id"],
            "part_id":         item["part_id"],
            "supplier_id":     supplier["id"],
            "quantity":        state["order_quantity"],
            "unit_price":      supplier["price_per_unit"],
            "total_value":     state["order_value"],
            "status":          "confirmed",
            "delivery_status": "awaiting",
            "expected_by":     (
                _now() + timedelta(days=supplier["delivery_days"])
            ).isoformat(),
            "gate":            state.get("gate"),   # None = fully autonomous; G1/G3 = human approved
            "created_at":      _now().isoformat(),
        }

        save_purchase_order(po)

        # HOTL: notify user (production: send email / Slack webhook)
        print(f"\n  [HOTL] PO {po['id']} placed — "
              f"{supplier['name']}, €{po['total_value']:,.2f}. "
              f"Override window: 1 hour.")

        log = (
            f"WHAT: PO {po['id']} created for {po['quantity']} × {po['part_id']} "
            f"from {supplier['name']} — total €{po['total_value']:,.2f}. "
            f"WHY: decide_node approved, all gates cleared or human approved. "
            f"NEXT: HOTL notification sent — passing to track_delivery_node."
        )

        return {
            "purchase_order": po,
            "reasoning_log":  [log],
        }
    except Exception as e:
        return {
            "reasoning_log": [
                f"WHAT: order_node encountered an error and could not complete. "
                f"WHY: Exception — {e!r}. "
                f"NEXT: Cycle halted at order_node. No PO was saved. Review audit_log for this run_id."
            ],
        }


# ── Node 5: Track Delivery ─────────────────────────────────────────────────────

def track_delivery_node(state: BetsyState) -> dict:  # noqa: ARG001
    try:
        now      = _now()
        open_pos = get_open_purchase_orders()
        delayed  = []
        logs     = []

        for po in open_pos:
            if not po.get("expected_by"):
                continue
            expected = datetime.fromisoformat(po["expected_by"])
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)
            if now > expected and po["delivery_status"] == "awaiting":
                update_po_delivery_status(po["id"], "delayed")
                update_supplier_reliability(po["supplier_id"], -3.0)
                delayed.append(po["id"])
                logs.append(
                    f"WHAT: PO {po['id']} overdue (expected {po['expected_by'][:10]}). "
                    f"WHY: current time {now.date()} is past expected delivery date. "
                    f"NEXT: HOTL flag raised — supplier reliability -3 points, status set to 'delayed'."
                )

        if not logs:
            logs = [
                f"WHAT: checked {len(open_pos)} open PO(s). "
                f"WHY: delivery_status = 'awaiting' and expected_by not yet passed. "
                f"NEXT: all deliveries on track — passing to verify_node."
            ]
        elif delayed:
            print(f"\n  [HOTL] {len(delayed)} delayed PO(s): {', '.join(delayed)}. "
                  f"Review recommended.")

        return {"reasoning_log": logs}
    except Exception as e:
        return {
            "reasoning_log": [
                f"WHAT: track_delivery_node encountered an error and could not complete. "
                f"WHY: Exception — {e!r}. "
                f"NEXT: Cycle halted at track_delivery_node. Review audit_log for this run_id."
            ],
        }


# ── Node 6: Verify ─────────────────────────────────────────────────────────────

def verify_node(state: BetsyState) -> dict:
    """
    Process the first pending invoice from invoices.csv.
    G4: amount ≠ PO total  → HITL interrupt, hold payment.
    G5: duplicate invoice  → HITL interrupt, hold payment.
    """
    try:
        # Use invoice from state if present (from current run), else read CSV
        invoice = state.get("invoice")
        if not invoice:
            pending = get_pending_invoices_from_csv()
            if not pending:
                return {
                    "verification_result": "no_invoice",
                    "reasoning_log": [
                        "WHAT: no pending invoices found. "
                        "WHY: invoices.csv contains no rows with status='pending'. "
                        "NEXT: ending verification step — nothing to reconcile."
                    ],
                }
            # Use the last pending invoice (INV-TEST-001 for demo)
            raw = pending[-1]
            invoice = {
                "id":          raw["invoice_id"],
                "po_id":       raw["po_id"],
                "supplier_id": raw["supplier_id"],
                "amount":      float(raw["amount"]),
                "status":      "pending",
                "received_at": raw.get("invoice_date", _now().isoformat()),
            }

        po_id       = invoice["po_id"]
        amount      = float(invoice["amount"])
        supplier_id = invoice["supplier_id"]

        # Persist invoice to DB
        save_invoice(invoice)

        gate = gate_reason = escalation = None
        result = "match"

        # ── G5: duplicate check ────────────────────────────────────────────────────
        if check_duplicate_invoice(supplier_id, po_id, amount, exclude_id=invoice["id"]):
            gate        = "G5"
            gate_reason = (
                f"Duplicate invoice detected: supplier {supplier_id}, "
                f"PO {po_id}, amount €{amount:,.2f} already on record."
            )
            result = "duplicate"
            update_invoice_status(invoice["id"], "held")
            escalation = {
                "what_betsy_planned": f"Process invoice {invoice['id']} for €{amount:,.2f}",
                "why_gate_fired":     gate_reason,
                "action_required":    "Type 'approve' to release or 'reject' to void duplicate.",
            }

        # ── G4: amount mismatch ────────────────────────────────────────────────────
        if not gate:
            po_total = get_po_total(po_id)
            if po_total is not None and abs(amount - po_total) > 0.01:
                gate        = "G4"
                gate_reason = (
                    f"Invoice amount €{amount:,.2f} does not match "
                    f"PO {po_id} total €{po_total:,.2f} "
                    f"(difference €{abs(amount - po_total):,.2f})."
                )
                result = "mismatch"
                update_invoice_status(invoice["id"], "held")
                escalation = {
                    "what_betsy_planned": (
                        f"Approve payment of €{amount:,.2f} to {supplier_id} "
                        f"against PO {po_id} (total €{po_total:,.2f})"
                    ),
                    "why_gate_fired":     gate_reason,
                    "action_required":    "Type 'approve' to override or 'reject' to hold payment.",
                }
            elif po_total is not None:
                update_invoice_status(invoice["id"], "matched")
                update_supplier_reliability(supplier_id, +2.0)

        log = (
            f"WHAT: verified invoice {invoice['id']} — €{amount:,.2f} "
            f"against PO {po_id}. Result: {result}. "
            f"WHY: {'Gate ' + gate + ' — ' + gate_reason if gate else 'amount matches PO total exactly.'} "
            f"NEXT: {'Gate ' + gate + ' HITL interrupt — payment held.' if gate else 'invoice cleared — supplier reliability +2.'}"
        )

        return {
            "verification_result": result,
            "gate":                gate,
            "gate_reason":         gate_reason,
            "escalation_payload":  escalation,
            "reasoning_log":       [log],
        }
    except Exception as e:
        return {
            "verification_result": "error",
            "reasoning_log": [
                f"WHAT: verify_node encountered an error and could not complete. "
                f"WHY: Exception — {e!r}. "
                f"NEXT: Cycle halted at verify_node. Invoice not processed. Review audit_log for this run_id."
            ],
        }
