"""
app.py — Betsy Procurement Agent Dashboard
==========================================
Streamlit web UI. Shows live inventory, agent flow, gate approval,
purchase orders, and audit log.

Usage:
    streamlit run app.py
"""

import csv
import os
import sqlite3
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from langgraph.types import Command

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Betsy Procurement Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
DB_PATH    = os.path.join(os.path.dirname(__file__), "betsy.db")
INV_CSV    = os.path.join(DATA_DIR, "inventory.csv")
SUP_CSV    = os.path.join(DATA_DIR, "suppliers.csv")
INV_CSV_2  = os.path.join(DATA_DIR, "invoices.csv")

GATE_COLOR = {"G1": "#e74c3c", "G2": "#e67e22", "G3": "#f39c12",
              "G4": "#c0392b", "G5": "#8e44ad", "G6": "#2980b9"}


# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_graph():
    """Build the persistent graph once and reuse across all reruns."""
    from betsy.database import init_db, seed_suppliers
    from betsy.graph import build_persistent_graph
    init_db()
    seed_suppliers()
    return build_persistent_graph()


def read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def db_query(sql: str, params=()) -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar navigation
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🤖 Betsy")
    st.caption("Autonomous Procurement Agent")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "▶ Run Agent", "📦 Inventory",
         "🏭 Suppliers", "🧾 Purchase Orders", "📜 Audit Log"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("LangGraph · llama3.2:3b · SQLite")
    st.caption(f"Updated: {_now()}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption("Live snapshot of Betsy's world.")

    # ── KPI row ────────────────────────────────────────────────────────────────
    inv_df = read_csv(INV_CSV)
    low_stock = 0
    stale     = False
    if not inv_df.empty:
        inv_df["current_stock"]    = pd.to_numeric(inv_df["current_stock"], errors="coerce")
        inv_df["reorder_threshold"] = pd.to_numeric(inv_df["reorder_threshold"], errors="coerce")
        low_stock = int((inv_df["current_stock"] < inv_df["reorder_threshold"]).sum())
        try:
            ts = datetime.fromisoformat(inv_df["data_timestamp"].iloc[0])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            stale = age_h > 4.0
        except Exception:
            pass

    open_pos = db_query("SELECT COUNT(*) AS n FROM purchase_orders WHERE delivery_status='awaiting'")
    n_open   = int(open_pos["n"].iloc[0]) if not open_pos.empty else 0

    last_gate = db_query("SELECT gate FROM purchase_orders WHERE gate IS NOT NULL ORDER BY created_at DESC LIMIT 1")
    last_g    = last_gate["gate"].iloc[0] if not last_gate.empty else "—"

    audit_count = db_query("SELECT COUNT(*) AS n FROM audit_log")
    n_audit     = int(audit_count["n"].iloc[0]) if not audit_count.empty else 0

    # Autonomy rate: orders placed without a HITL gate / total orders placed
    auto_df    = db_query("SELECT COUNT(*) AS total, SUM(CASE WHEN gate IS NULL THEN 1 ELSE 0 END) AS autonomous FROM purchase_orders")
    if not auto_df.empty and int(auto_df["total"].iloc[0]) > 0:
        total_po   = int(auto_df["total"].iloc[0])
        auto_po    = int(auto_df["autonomous"].iloc[0])
        auto_rate  = f"{auto_po / total_po * 100:.0f}%"
        auto_delta = "✅ target met" if auto_po / total_po >= 0.95 else "⚠ below 95% target"
    else:
        auto_rate  = "—"
        auto_delta = "No orders yet"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Low stock items", low_stock, delta="G6 risk" if stale else None,
              delta_color="inverse")
    c2.metric("Open POs (awaiting)", n_open)
    c3.metric("Last gate fired", last_g)
    c4.metric("Audit log entries", n_audit)
    c5.metric("Autonomy rate", auto_rate, delta=auto_delta,
              delta_color="normal" if auto_rate == "—" or auto_rate >= "95%" else "inverse")

    st.divider()

    # ── Inventory health bar chart ─────────────────────────────────────────────
    if not inv_df.empty:
        st.subheader("Inventory Health")
        chart_df = inv_df[["part_name", "current_stock", "reorder_threshold"]].copy()
        chart_df["status"] = chart_df.apply(
            lambda r: "🔴 LOW" if r["current_stock"] < r["reorder_threshold"] else "🟢 OK", axis=1
        )
        chart_df = chart_df.sort_values("current_stock")
        st.dataframe(
            chart_df.rename(columns={
                "part_name": "Part", "current_stock": "Stock",
                "reorder_threshold": "Threshold", "status": "Status"
            }),
            use_container_width=True, hide_index=True,
        )
        st.bar_chart(
            chart_df.set_index("part_name")[["current_stock", "reorder_threshold"]],
            color=["#3498db", "#e74c3c"],
        )

    # ── Recent POs ─────────────────────────────────────────────────────────────
    st.subheader("Recent Purchase Orders")
    po_df = db_query(
        "SELECT id, part_id, supplier_id, total_value, status, delivery_status, created_at "
        "FROM purchase_orders ORDER BY created_at DESC LIMIT 5"
    )
    if not po_df.empty:
        st.dataframe(po_df, use_container_width=True, hide_index=True)
    else:
        st.info("No purchase orders yet. Run the agent to generate one.")

    # ── Data freshness warning ─────────────────────────────────────────────────
    if stale:
        st.warning(f"⚠ Inventory data is stale (>4h old). Gate G6 will fire on next run. "
                   f"Update inventory.csv timestamps before running.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Run Agent
# ══════════════════════════════════════════════════════════════════════════════

elif page == "▶ Run Agent":
    st.title("▶ Run Agent")
    st.caption("Start a monitoring cycle. See each node execute. Approve or reject gates.")

    graph = get_graph()

    # ── Session state init ─────────────────────────────────────────────────────
    if "run_log"       not in st.session_state: st.session_state.run_log       = []
    if "thread_id"     not in st.session_state: st.session_state.thread_id     = None
    if "run_id"        not in st.session_state: st.session_state.run_id        = None
    if "agent_state"   not in st.session_state: st.session_state.agent_state   = "idle"
    if "pending_gate"  not in st.session_state: st.session_state.pending_gate  = None
    if "demo_scenario" not in st.session_state: st.session_state.demo_scenario = "real"

    NODE_ICON = {
        "monitor":        "🔍 Node 1 — Monitor",
        "evaluate":       "⚖ Node 2 — Evaluate",
        "decide":         "🧠 Node 3 — Decide (LLM)",
        "human_approval": "⚡ Gate — Human Approval",
        "order":          "📋 Node 4 — Order",
        "track_delivery": "🚚 Node 5 — Track Delivery",
        "verify":         "✅ Node 6 — Verify",
    }

    DEMO_STATES = {
        "real": None,
        "g1":  [{"part_id":"PART-001","part_name":"Bearing Assembly","current_stock":"12",
                  "reorder_threshold":"20","reorder_quantity":"40","assembly_line":"Line 2",
                  "unit":"units","data_timestamp":"2026-06-04T08:00:00"}],
        "g3":  [{"part_id":"PART-017","part_name":"Viton Seal Kit 32mm","current_stock":"5",
                  "reorder_threshold":"35","reorder_quantity":"3","assembly_line":"Line 2",
                  "unit":"units","data_timestamp":"2026-06-04T08:00:00"}],
        "g4":  [{"part_id":"PART-002","part_name":"Hydraulic Seal Ring","current_stock":"8",
                  "reorder_threshold":"30","reorder_quantity":"60","assembly_line":"Line 1",
                  "unit":"units","data_timestamp":"2026-06-04T08:00:00"}],
        "g5":  [],   # invoice-only mode — no ordering step
    }
    DEMO_INVOICE = {
        "g4": {"id":"INV-TEST-001","po_id":"PO-2025-005","supplier_id":"SUP-003",
               "amount":6200.00,"status":"pending","received_at":"2026-06-04T10:00:00"},
        "g5": {"id":"INV-TEST-DUP","po_id":"PO-2025-005","supplier_id":"SUP-003",
               "amount":6200.00,"status":"pending","received_at":"2026-06-04T12:00:00"},
    }

    # ── Controls ───────────────────────────────────────────────────────────────
    col_btn, col_demo = st.columns([2, 3])
    with col_demo:
        demo_choice = st.selectbox(
            "Scenario",
            ["real — read live inventory.csv",
             "g1 — Spend gate (PART-001, €9,880)",
             "g3 — Price spike (PART-017, +26.7%)",
             "g4 — Invoice mismatch (INV-TEST-001)",
             "g5 — Duplicate invoice (INV-TEST-DUP)"],
            key="demo_select",
        )
        scenario = demo_choice.split(" — ")[0].strip()

    with col_btn:
        st.write("")
        run_clicked = st.button(
            "▶ Start New Run",
            type="primary",
            disabled=(st.session_state.agent_state == "running"),
            use_container_width=True,
        )

    if st.button("🗑 Clear log", use_container_width=True):
        st.session_state.run_log       = []
        st.session_state.agent_state   = "idle"
        st.session_state.pending_gate  = None
        st.session_state.thread_id     = None
        st.session_state.gate_notified = False
        st.rerun()

    st.divider()

    # ── Start a new run ────────────────────────────────────────────────────────
    if run_clicked:
        from betsy.database import flush_reasoning_log
        st.session_state.run_log     = []
        st.session_state.agent_state = "running"
        st.session_state.pending_gate = None
        st.session_state.run_id      = str(uuid.uuid4())
        st.session_state.thread_id   = str(uuid.uuid4())

        low_stock_items = DEMO_STATES.get(scenario)
        invoice         = DEMO_INVOICE.get(scenario)

        initial = {
            "run_id":              st.session_state.run_id,
            "inventory_snapshot":  [],
            "low_stock_items":     low_stock_items or [],
            "data_age_hours":      0.0,
            "candidate_suppliers": [],
            "selected_supplier":   None,
            "order_quantity":      0,
            "order_value":         0.0,
            "decision":            "",
            "purchase_order":      None,
            "invoice":             invoice,
            "verification_result": None,
            "gate":                None,
            "gate_reason":         None,
            "escalation_payload":  None,
            "human_response":      None,
            "reasoning_log":       [],
        }
        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        log_box = st.empty()

        def _render_log():
            log_box.markdown(
                "\n\n".join(st.session_state.run_log) or "*Waiting for first node...*"
            )

        for update in graph.stream(initial, config, stream_mode="updates"):
            for node, node_data in update.items():
                label = NODE_ICON.get(node, node)
                logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                entry = f"**{label}**\n"
                for l in logs:
                    entry += f"\n> {l}"
                st.session_state.run_log.append(entry)
                _render_log()

        snap = graph.get_state(config)
        if snap.next:
            vals    = snap.values
            gate    = vals.get("gate", "?")
            payload = vals.get("escalation_payload") or {}
            st.session_state.pending_gate = {
                "gate":    gate,
                "reason":  vals.get("gate_reason", ""),
                "payload": payload,
                "config":  config,
            }
            st.session_state.agent_state = "waiting_approval"
        else:
            final = snap.values
            flush_reasoning_log(
                st.session_state.run_id,
                final.get("reasoning_log", [])
            )
            st.session_state.agent_state = "complete"

        st.rerun()

    # ── Live log display ───────────────────────────────────────────────────────
    if st.session_state.run_log:
        with st.expander("Agent log", expanded=True):
            for entry in st.session_state.run_log:
                st.markdown(entry)
                st.divider()

    # ── Gate approval panel ────────────────────────────────────────────────────
    if st.session_state.agent_state == "waiting_approval" and st.session_state.pending_gate:
        from betsy.database import flush_reasoning_log
        from betsy.notifications import notify_gate_fired
        g  = st.session_state.pending_gate
        color = GATE_COLOR.get(g["gate"], "#e74c3c")

        # Browser toast + desktop popup (fires once when gate first appears)
        if not st.session_state.get("gate_notified"):
            st.toast(f"⚡ Gate {g['gate']} fired — your approval is needed", icon="🔔")
            notify_gate_fired(g["gate"], g["reason"])
            st.session_state.gate_notified = True

        st.markdown(
            f'<div style="background:{color}22;border-left:4px solid {color};'
            f'padding:16px;border-radius:6px;margin:12px 0">'
            f'<h3 style="color:{color};margin:0">⚡ Gate {g["gate"]} Fired</h3>'
            f'<p style="margin:6px 0 0">{g["reason"]}</p></div>',
            unsafe_allow_html=True,
        )

        payload = g["payload"]
        if payload.get("what_betsy_planned"):
            st.info(f"**Betsy planned:** {payload['what_betsy_planned']}")
        if payload.get("llm_reasoning"):
            with st.expander("Betsy's reasoning"):
                st.write(payload["llm_reasoning"])
        alts = payload.get("alternatives", [])
        if alts:
            st.write("**Alternatives considered:**")
            alt_df = pd.DataFrame(alts)
            st.dataframe(alt_df, hide_index=True, use_container_width=True)

        st.write(payload.get("action_required", "Approve or reject?"))

        ca, cr = st.columns(2)
        if ca.button("✅ Approve", type="primary", use_container_width=True):
            config = g["config"]
            for update in graph.stream(Command(resume="approve"), config, stream_mode="updates"):
                for node, node_data in update.items():
                    label = NODE_ICON.get(node, node)
                    logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                    entry = f"**{label}** *(approved)*\n"
                    for l in logs: entry += f"\n> {l}"
                    st.session_state.run_log.append(entry)

            snap2 = graph.get_state(config)
            if snap2.next:
                vals2    = snap2.values
                gate2    = vals2.get("gate", "?")
                payload2 = vals2.get("escalation_payload") or {}
                st.session_state.pending_gate = {
                    "gate": gate2, "reason": vals2.get("gate_reason",""),
                    "payload": payload2, "config": config,
                }
            else:
                final2 = snap2.values
                flush_reasoning_log(st.session_state.run_id, final2.get("reasoning_log", []))
                st.session_state.pending_gate  = None
                st.session_state.agent_state   = "complete"
                st.session_state.gate_notified = False
            st.rerun()

        if cr.button("❌ Reject", use_container_width=True):
            config = g["config"]
            for update in graph.stream(Command(resume="reject"), config, stream_mode="updates"):
                for node, node_data in update.items():
                    label = NODE_ICON.get(node, node)
                    logs  = list(node_data.get("reasoning_log", [])) if isinstance(node_data, dict) else []
                    entry = f"**{label}** *(rejected)*\n"
                    for l in logs: entry += f"\n> {l}"
                    st.session_state.run_log.append(entry)

            final3 = graph.get_state(config).values
            flush_reasoning_log(st.session_state.run_id, final3.get("reasoning_log", []))
            st.session_state.pending_gate = None
            st.session_state.agent_state  = "complete"
            st.rerun()

    # ── Complete banner ────────────────────────────────────────────────────────
    if st.session_state.agent_state == "complete":
        st.success("✅ Run complete — reasoning log saved to betsy.db")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Inventory
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📦 Inventory":
    st.title("📦 Inventory")

    inv_df = read_csv(INV_CSV)
    if inv_df.empty:
        st.warning("inventory.csv not found.")
    else:
        inv_df["current_stock"]    = pd.to_numeric(inv_df["current_stock"],    errors="coerce")
        inv_df["reorder_threshold"] = pd.to_numeric(inv_df["reorder_threshold"], errors="coerce")
        inv_df["reorder_quantity"]  = pd.to_numeric(inv_df["reorder_quantity"],  errors="coerce")
        inv_df["low_stock"]         = inv_df["current_stock"] < inv_df["reorder_threshold"]
        inv_df["gap"]               = inv_df["reorder_threshold"] - inv_df["current_stock"]

        show_only_low = st.toggle("Show only low-stock items", value=False)
        if show_only_low:
            inv_df = inv_df[inv_df["low_stock"]]

        st.metric("Low stock items", int(inv_df["low_stock"].sum()),
                  delta=f"of {len(read_csv(INV_CSV))} total parts")

        def highlight_low(row):
            try:
                is_low = row["Stock"] < row["Threshold"]
                style  = "background-color: #c0392b; color: white; font-weight: bold" if is_low else ""
            except (KeyError, TypeError):
                style = ""
            return [style] * len(row)

        display = inv_df[["part_id","part_name","assembly_line","current_stock",
                           "reorder_threshold","reorder_quantity","data_timestamp"]].copy()
        display.columns = ["Part ID","Name","Line","Stock","Threshold","Reorder Qty","Last Updated"]
        st.dataframe(display.style.apply(highlight_low, axis=1),
                     use_container_width=True, hide_index=True)

        st.subheader("Stock vs Threshold")
        chart = inv_df.set_index("part_name")[["current_stock","reorder_threshold"]]
        chart.columns = ["Current Stock", "Reorder Threshold"]
        st.bar_chart(chart, color=["#3498db","#e74c3c"])

        # Data freshness
        try:
            ts = datetime.fromisoformat(inv_df["data_timestamp"].iloc[0])
            if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age > 4:
                st.error(f"⚠ Data is {age:.1f}h old — G6 will fire on next run.")
            else:
                st.success(f"✅ Data is {age:.1f}h old — fresh (threshold 4h).")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Suppliers
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🏭 Suppliers":
    st.title("🏭 Suppliers")

    # Read from DB — has correct column names (price_per_unit, name, is_approved)
    sup_df = db_query(
        "SELECT id, name, price_per_unit, last_price, delivery_days, "
        "reliability_score, is_approved, parts_supplied FROM suppliers"
    )

    if sup_df.empty:
        st.info("No suppliers in betsy.db yet. Run the agent once to seed from suppliers.csv.")
    else:
        sup_df["price_per_unit"]    = pd.to_numeric(sup_df["price_per_unit"],   errors="coerce")
        sup_df["last_price"]        = pd.to_numeric(sup_df["last_price"],        errors="coerce")
        sup_df["delivery_days"]     = pd.to_numeric(sup_df["delivery_days"],     errors="coerce")
        sup_df["reliability_score"] = pd.to_numeric(sup_df["reliability_score"], errors="coerce")

        # Compute final score (same formula as nodes.py)
        prices     = sup_df["price_per_unit"]
        deliveries = sup_df["delivery_days"] * 24
        p_min, p_range = prices.min(), (prices.max() - prices.min()) or 1
        d_min, d_range = deliveries.min(), (deliveries.max() - deliveries.min()) or 1

        sup_df["S_rel"]   = sup_df["reliability_score"].round(1)
        sup_df["S_price"] = (100 - ((prices - p_min) / p_range) * 100).round(1)
        sup_df["S_del"]   = (100 - ((deliveries - d_min) / d_range) * 100).round(1)
        sup_df["Score"]   = (
            sup_df["S_rel"]   * 0.40 +
            sup_df["S_price"] * 0.35 +
            sup_df["S_del"]   * 0.25
        ).round(2)

        # Filter by part
        part_filter = st.text_input("Filter by part supplied (e.g. PART-001)")
        if part_filter:
            sup_df = sup_df[sup_df["parts_supplied"].str.contains(part_filter, na=False, case=False)]

        display_cols = ["id","name","is_approved","price_per_unit","last_price",
                        "delivery_days","reliability_score","Score","parts_supplied"]
        st.dataframe(
            sup_df[display_cols].sort_values("Score", ascending=False),
            use_container_width=True, hide_index=True,
        )

        st.subheader("Score Breakdown (SAW: reliability×0.40 + price×0.35 + delivery×0.25)")
        score_chart = sup_df.set_index("name")[["S_rel","S_price","S_del","Score"]]
        score_chart.columns = ["S_reliability (40%)","S_price (35%)","S_delivery (25%)","Final Score"]
        st.dataframe(score_chart.sort_values("Final Score", ascending=False),
                     use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Purchase Orders
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🧾 Purchase Orders":
    st.title("🧾 Purchase Orders")

    po_df = db_query(
        "SELECT id, part_id, supplier_id, quantity, unit_price, total_value, "
        "status, delivery_status, expected_by, created_at "
        "FROM purchase_orders ORDER BY created_at DESC"
    )

    if po_df.empty:
        st.info("No purchase orders in betsy.db yet. Run the agent to create one.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total POs", len(po_df))
        col2.metric("Awaiting delivery", int((po_df["delivery_status"] == "awaiting").sum()))
        col3.metric("Delayed", int((po_df["delivery_status"] == "delayed").sum()))

        status_filter = st.selectbox("Filter by delivery status",
                                     ["all", "awaiting", "delayed", "delivered"])
        if status_filter != "all":
            po_df = po_df[po_df["delivery_status"] == status_filter]

        def color_status(val):
            styles = {
                "awaiting":  "background-color: #d68910; color: white; font-weight: bold",
                "delayed":   "background-color: #c0392b; color: white; font-weight: bold",
                "delivered": "background-color: #1e8449; color: white; font-weight: bold",
                "confirmed": "background-color: #1a5276; color: white; font-weight: bold",
            }
            return styles.get(val, "")

        st.dataframe(
            po_df.style.map(color_status, subset=["delivery_status"]),
            use_container_width=True, hide_index=True,
        )

        # Pending invoices + on-demand verification
        st.subheader("Pending Invoices (invoices.csv)")
        inv_df = read_csv(INV_CSV_2)
        if not inv_df.empty:
            pending = inv_df[inv_df["status"].str.lower() == "pending"]
            if not pending.empty:
                st.dataframe(pending, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("**Verify an invoice now** — runs G4 (mismatch) and G5 (duplicate) checks without a full ordering cycle.")

                # Session state for inline verification flow
                for k, v in [("vinv_state","idle"), ("vinv_log",[]),
                              ("vinv_gate",None), ("vinv_thread",None), ("vinv_run_id",None)]:
                    if k not in st.session_state:
                        st.session_state[k] = v

                inv_col1, inv_col2 = st.columns([2, 2])
                with inv_col1:
                    inv_options = pending["invoice_id"].tolist() if "invoice_id" in pending.columns else []
                    selected_inv = st.selectbox("Invoice to verify", inv_options, key="inv_sel")
                with inv_col2:
                    st.write("")
                    vinv_clicked = st.button(
                        "🔍 Verify Now",
                        type="primary",
                        disabled=(st.session_state.vinv_state == "running"),
                        use_container_width=True,
                        key="vinv_btn",
                    )

                if vinv_clicked and selected_inv:
                    from betsy.database import flush_reasoning_log
                    inv_row = pending[pending["invoice_id"] == selected_inv].iloc[0]
                    invoice_payload = {
                        "id":          inv_row["invoice_id"],
                        "po_id":       inv_row["po_id"],
                        "supplier_id": inv_row["supplier_id"],
                        "amount":      float(inv_row["amount"]),
                        "status":      "pending",
                        "received_at": str(inv_row.get("invoice_date", _now())),
                    }
                    st.session_state.vinv_log     = []
                    st.session_state.vinv_state   = "running"
                    st.session_state.vinv_run_id  = str(uuid.uuid4())
                    st.session_state.vinv_thread  = str(uuid.uuid4())

                    graph = get_graph()
                    config = {"configurable": {"thread_id": st.session_state.vinv_thread}}
                    initial = {
                        "run_id": st.session_state.vinv_run_id,
                        "inventory_snapshot": [], "low_stock_items": [],
                        "data_age_hours": 0.0, "candidate_suppliers": [],
                        "selected_supplier": None, "order_quantity": 0,
                        "order_value": 0.0, "decision": "", "purchase_order": None,
                        "invoice": invoice_payload, "verification_result": None,
                        "gate": None, "gate_reason": None,
                        "escalation_payload": None, "human_response": None,
                        "reasoning_log": [],
                    }
                    for update in graph.stream(initial, config, stream_mode="updates"):
                        for node, node_data in update.items():
                            for entry in (node_data.get("reasoning_log", []) if isinstance(node_data, dict) else []):
                                st.session_state.vinv_log.append(entry)

                    snap = graph.get_state(config)
                    if snap.next:
                        vals = snap.values
                        st.session_state.vinv_gate = {
                            "gate": vals.get("gate"), "reason": vals.get("gate_reason",""),
                            "payload": vals.get("escalation_payload") or {}, "config": config,
                        }
                        st.session_state.vinv_state = "waiting_approval"
                    else:
                        flush_reasoning_log(st.session_state.vinv_run_id,
                                            snap.values.get("reasoning_log", []))
                        st.session_state.vinv_state = "complete"
                    st.rerun()

                # Log display
                if st.session_state.vinv_log:
                    with st.expander("Verification log", expanded=True):
                        for entry in st.session_state.vinv_log:
                            st.markdown(f"> {entry}")

                # Gate approval panel for invoice verification
                if st.session_state.vinv_state == "waiting_approval" and st.session_state.vinv_gate:
                    from betsy.database import flush_reasoning_log
                    g = st.session_state.vinv_gate
                    color = GATE_COLOR.get(g["gate"], "#e74c3c")
                    st.markdown(
                        f"<div style='background:{color};padding:14px;border-radius:8px;color:white;margin:8px 0'>"
                        f"<b>⚡ Gate {g['gate']} — {g['reason']}</b></div>",
                        unsafe_allow_html=True,
                    )
                    payload = g["payload"]
                    if payload.get("why_gate_fired"):
                        st.info(payload["why_gate_fired"])

                    graph = get_graph()
                    c_a, c_r = st.columns(2)
                    with c_a:
                        if st.button("✅ Approve payment", type="primary",
                                     use_container_width=True, key="vinv_approve"):
                            for update in graph.stream(Command(resume="approve"),
                                                       g["config"], stream_mode="updates"):
                                for node, node_data in update.items():
                                    for entry in (node_data.get("reasoning_log", [])
                                                  if isinstance(node_data, dict) else []):
                                        st.session_state.vinv_log.append(entry)
                            flush_reasoning_log(st.session_state.vinv_run_id,
                                                graph.get_state(g["config"]).values.get("reasoning_log",[]))
                            st.session_state.vinv_state = "complete"
                            st.session_state.vinv_gate = None
                            st.rerun()
                    with c_r:
                        if st.button("❌ Hold payment", use_container_width=True, key="vinv_reject"):
                            for _ in graph.stream(Command(resume="reject"),
                                                  g["config"], stream_mode="updates"):
                                pass
                            st.session_state.vinv_state = "complete"
                            st.session_state.vinv_gate = None
                            st.rerun()

                if st.session_state.vinv_state == "complete":
                    st.success("✅ Verification complete — audit log and supplier scores updated.")
                    if st.button("Clear", key="vinv_clear"):
                        for k in ("vinv_state","vinv_log","vinv_gate","vinv_thread","vinv_run_id"):
                            st.session_state[k] = "idle" if k == "vinv_state" else ([] if k == "vinv_log" else None)
                        st.rerun()
            else:
                st.success("No pending invoices.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Audit Log
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📜 Audit Log":
    st.title("📜 Audit Log")
    st.caption("Every WHAT/WHY/NEXT entry Betsy wrote to betsy.db during runs.")

    # The WHAT/WHY/NEXT text is stored in the 'decision' column
    audit_df = db_query(
        "SELECT run_id, node, gate, decision AS reasoning, timestamp "
        "FROM audit_log ORDER BY timestamp DESC"
    )

    if audit_df.empty:
        st.info("No audit log entries yet. Run the agent first.")
    else:
        st.metric("Total log entries", len(audit_df))

        search = st.text_input("Search reasoning text")
        if search:
            audit_df = audit_df[
                audit_df["reasoning"].str.contains(search, case=False, na=False)
            ]

        gate_filter = st.multiselect(
            "Filter by gate",
            options=sorted(audit_df["gate"].dropna().unique()),
        )
        if gate_filter:
            audit_df = audit_df[audit_df["gate"].isin(gate_filter)]

        st.dataframe(audit_df, use_container_width=True, hide_index=True)

        # Show as readable log
        if st.toggle("Show as readable log"):
            NODE_COLOR = {
                "monitor":        "#2980b9",
                "evaluate":       "#8e44ad",
                "decide":         "#d35400",
                "order":          "#27ae60",
                "track_delivery": "#16a085",
                "verify":         "#c0392b",
                "human_approval": "#e74c3c",
            }
            for _, row in audit_df.iterrows():
                ts   = str(row.get("timestamp") or "")[:16]
                node = str(row.get("node") or "unknown")
                text = str(row.get("reasoning") or "")

                # gate: pandas reads SQL NULL as float NaN — must guard
                raw_gate = row.get("gate")
                gate = str(raw_gate) if (raw_gate is not None and str(raw_gate) != "nan") else ""

                node_color = NODE_COLOR.get(node, "#555")
                gate_color = GATE_COLOR.get(gate, node_color)
                border     = gate_color if gate else node_color
                badge      = (
                    f' <span style="background:{gate_color};color:white;padding:1px 6px;'
                    f'border-radius:3px;font-size:11px">⚡ Gate {gate}</span>'
                    if gate else ""
                )

                st.markdown(
                    f'<div style="border-left:4px solid {border};padding:10px 14px;margin:6px 0;'
                    f'background:{border}18;border-radius:5px">'
                    f'<small style="color:#aaa">{ts}</small>'
                    f' <span style="background:{node_color};color:white;padding:1px 6px;'
                    f'border-radius:3px;font-size:11px">{node}</span>{badge}'
                    f'<br><span style="color:#e8e8e8;font-size:13px;line-height:1.6">{text}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
