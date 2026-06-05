from operator import add
from typing import Annotated, Optional
from typing_extensions import TypedDict


class BetsyState(TypedDict):
    """
    Shared state flowing through all 6 nodes.

    Lifetime: one procurement run (created fresh each run, then checkpointed).
    Persistence: LangGraph SqliteSaver saves this between runs so the graph
                 can be resumed after a HITL interrupt.

    Separate from the SQLite business tables (suppliers, purchase_orders, etc.)
    which persist supplier history, PO records, and invoices across all runs.
    """

    run_id: str

    # ── Node 1: Monitor ───────────────────────────────────────────────────────
    inventory_snapshot: list    # all rows read from inventory.csv
    low_stock_items:    list    # items whose stock <= reorder_threshold
    data_age_hours:     float   # hours since inventory was last updated (G6 check)

    # ── Node 2: Evaluate ──────────────────────────────────────────────────────
    candidate_suppliers: list   # scored + ranked, approved suppliers only

    # ── Node 3: Decide (LLM) ─────────────────────────────────────────────────
    selected_supplier: Optional[dict]
    order_quantity:    int
    order_value:       float
    decision:          str      # "order" | "skip" | "escalate"

    # ── Node 4: Order ─────────────────────────────────────────────────────────
    purchase_order: Optional[dict]

    # ── Node 5: Track Delivery ────────────────────────────────────────────────
    # (reads directly from SQLite; no extra state fields needed)

    # ── Node 6: Verify ────────────────────────────────────────────────────────
    invoice:              Optional[dict]
    verification_result:  Optional[str]   # "match" | "mismatch" | "duplicate" | "no_po"

    # ── Human oversight ───────────────────────────────────────────────────────
    gate:               Optional[str]   # "G1" – "G6" | None
    gate_reason:        Optional[str]
    escalation_payload: Optional[dict]  # full summary sent to user at gate
    human_response:     Optional[str]   # "approve" | "reject"

    # ── Audit trail (auto-accumulated — every node appends) ───────────────────
    reasoning_log: Annotated[list, add]
