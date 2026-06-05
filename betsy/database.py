"""
betsy/database.py
=================
SQLite layer for Betsy.

betsy.db         — business data (suppliers, POs, invoices, audit_log)
betsy_state.db   — LangGraph checkpointer (managed by LangGraph, separate file)

Suppliers are seeded from data/suppliers.csv on first init.
Reliability scores are stored as 0–100 (CSV uses 0–1 → multiply × 100 on load).
"""

import csv
import os
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

DB_PATH   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "betsy.db")
DATA_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            price_per_unit    REAL NOT NULL,
            last_price        REAL,
            delivery_days     INTEGER NOT NULL,
            reliability_score REAL DEFAULT 70.0,
            is_approved       INTEGER DEFAULT 1,
            parts_supplied    TEXT
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id               TEXT PRIMARY KEY,
            run_id           TEXT NOT NULL,
            part_id          TEXT NOT NULL,
            supplier_id      TEXT NOT NULL,
            quantity         INTEGER NOT NULL,
            unit_price       REAL NOT NULL,
            total_value      REAL NOT NULL,
            status           TEXT DEFAULT 'pending',
            delivery_status  TEXT DEFAULT 'awaiting',
            expected_by      TEXT,
            gate             TEXT,
            created_at       TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id           TEXT PRIMARY KEY,
            po_id        TEXT NOT NULL,
            supplier_id  TEXT NOT NULL,
            amount       REAL NOT NULL,
            status       TEXT DEFAULT 'pending',
            received_at  TEXT NOT NULL,
            FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id    TEXT NOT NULL,
            node      TEXT NOT NULL,
            gate      TEXT,
            decision  TEXT NOT NULL,
            reasoning TEXT,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT NOT NULL,
            part_id     TEXT NOT NULL,
            unit_price  REAL NOT NULL,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
        """)
        # Migrate existing databases that predate the gate and price_history columns
        try:
            conn.execute("ALTER TABLE purchase_orders ADD COLUMN gate TEXT")
        except Exception:
            pass


# ── Seed suppliers from CSV ────────────────────────────────────────────────────

def seed_suppliers() -> None:
    """Load suppliers from data/suppliers.csv. Skips if table already has rows."""
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] > 0:
            return

    csv_path = os.path.join(DATA_DIR, "suppliers.csv")
    if not os.path.exists(csv_path):
        return

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            approved = 1 if str(row.get("approved", "True")).strip().lower() == "true" else 0
            rows.append((
                row["supplier_id"],
                row["supplier_name"],
                float(row["unit_price"]),
                float(row["last_price"]),
                int(row["delivery_days"]),
                round(float(row["reliability_score"]) * 100, 1),  # 0–1 → 0–100
                approved,
                row.get("parts_supplied", ""),
            ))

    with get_conn() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO suppliers
                (id, name, price_per_unit, last_price, delivery_days,
                 reliability_score, is_approved, parts_supplied)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)


# ── Suppliers ──────────────────────────────────────────────────────────────────

def get_approved_suppliers_for_part(part_id: str) -> list[dict]:
    """Return approved suppliers that supply the given part, ordered by reliability."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM suppliers
            WHERE is_approved = 1
              AND (parts_supplied LIKE ? OR parts_supplied LIKE ? OR parts_supplied LIKE ?)
            ORDER BY reliability_score DESC
        """, (f"{part_id},%", f"%,{part_id},%", f"%,{part_id}")).fetchall()
    return [dict(r) for r in rows]


def get_supplier(supplier_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM suppliers WHERE id = ?", (supplier_id,)
        ).fetchone()
    return dict(row) if row else None


def update_supplier_reliability(supplier_id: str, adjustment: float) -> None:
    with get_conn() as conn:
        conn.execute("""
            UPDATE suppliers
            SET reliability_score = MAX(0, MIN(100, reliability_score + ?))
            WHERE id = ?
        """, (adjustment, supplier_id))


# ── Purchase Orders ────────────────────────────────────────────────────────────

def save_purchase_order(po: dict) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO purchase_orders
                (id, run_id, part_id, supplier_id, quantity, unit_price,
                 total_value, status, delivery_status, expected_by, gate, created_at)
            VALUES
                (:id, :run_id, :part_id, :supplier_id, :quantity, :unit_price,
                 :total_value, :status, :delivery_status, :expected_by, :gate, :created_at)
        """, po)


def get_po_total(po_id: str) -> float | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT total_value FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
    if row:
        return row["total_value"]
    # Fall back to purchase_orders.csv if PO not yet in DB
    csv_path = os.path.join(DATA_DIR, "purchase_orders.csv")
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["po_id"] == po_id:
                    return float(r["total"])
    return None


def get_open_purchase_orders() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM purchase_orders
            WHERE delivery_status IN ('awaiting', 'delayed')
            ORDER BY created_at ASC
        """).fetchall()
    return [dict(r) for r in rows]


def update_po_delivery_status(po_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE purchase_orders SET delivery_status = ? WHERE id = ?",
            (status, po_id)
        )


# ── Invoices ───────────────────────────────────────────────────────────────────

def check_duplicate_invoice(supplier_id: str, po_id: str, amount: float,
                             exclude_id: str = "") -> bool:
    """
    Return True if an invoice for the same supplier + PO + amount was already
    processed within the last `within_days` days. (G5 check)
    """
    with get_conn() as conn:
        row = conn.execute("""
            SELECT id FROM invoices
            WHERE supplier_id = ? AND po_id = ? AND amount = ?
              AND id != ?
              AND status NOT IN ('duplicate', 'held', 'matched')
            LIMIT 1
        """, (supplier_id, po_id, amount, exclude_id)).fetchone()
    # Also check the CSV history for duplicates
    csv_path = os.path.join(DATA_DIR, "invoices.csv")
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r["invoice_id"] != exclude_id          # skip self-match
                        and r["supplier_id"] == supplier_id
                        and r["po_id"] == po_id
                        and float(r["amount"]) == amount
                        and r["status"] not in ("flagged_duplicate", "duplicate")):
                    return True  # at least one earlier cleared/pending match
    return row is not None


def get_pending_invoices_from_csv() -> list[dict]:
    """Read invoices.csv and return all rows with status='pending'."""
    csv_path = os.path.join(DATA_DIR, "invoices.csv")
    if not os.path.exists(csv_path):
        return []
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status", "").strip() == "pending":
                results.append(dict(row))
    return results


def save_invoice(invoice: dict) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO invoices
                (id, po_id, supplier_id, amount, status, received_at)
            VALUES (:id, :po_id, :supplier_id, :amount, :status, :received_at)
        """, invoice)


def update_invoice_status(invoice_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE invoices SET status = ? WHERE id = ?",
            (status, invoice_id)
        )


# ── Audit Log ──────────────────────────────────────────────────────────────────

# ── Price History ──────────────────────────────────────────────────────────────

def record_price_history(supplier_id: str, part_id: str, unit_price: float) -> None:
    """Record the price observed for a supplier+part at this point in time."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO price_history (supplier_id, part_id, unit_price, recorded_at)
            VALUES (?, ?, ?, ?)
        """, (supplier_id, part_id, unit_price, _now()))


def get_price_average(supplier_id: str, part_id: str, n: int = 3) -> float | None:
    """Return the rolling average of the last n recorded prices for a supplier+part."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT unit_price FROM price_history
            WHERE supplier_id = ? AND part_id = ?
            ORDER BY recorded_at DESC LIMIT ?
        """, (supplier_id, part_id, n)).fetchall()
    if not rows:
        return None
    return sum(r["unit_price"] for r in rows) / len(rows)


# ── Audit Log ──────────────────────────────────────────────────────────────────

def flush_reasoning_log(run_id: str, reasoning_log: list) -> None:
    """
    Save every WHAT/WHY/NEXT entry to audit_log.

    Node is inferred from:
      - entries starting with [node_name] (human_approval format)
      - keyword patterns in the WHAT text
    """
    _KEYWORDS = {
        "inventory rows":   "monitor",
        "inventory items":  "monitor",
        "stale":            "monitor",
        "approved supplier": "evaluate",
        "scored":           "evaluate",
        "selected":         "decide",
        "Gate G1":          "decide",
        "Gate G3":          "decide",
        "PO ":              "order",
        "delivery":         "track_delivery",
        "invoice":          "verify",
        "Gate G4":          "verify",
        "Gate G5":          "verify",
    }

    timestamp = _now()
    with get_conn() as conn:
        for entry in reasoning_log:
            # [node_name] prefix format (human_approval)
            if entry.startswith("[") and "]" in entry:
                node = entry[1:entry.index("]")]
            else:
                node = next(
                    (v for k, v in _KEYWORDS.items() if k.lower() in entry.lower()),
                    "unknown"
                )

            # Extract gate from entry text
            gate = None
            for g in ("G1","G2","G3","G4","G5","G6"):
                if f"Gate {g}" in entry or f"gate {g}" in entry.lower():
                    gate = g
                    break

            conn.execute("""
                INSERT INTO audit_log (run_id, node, gate, decision, reasoning, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (run_id, node, gate, entry, "", timestamp))
