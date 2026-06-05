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
        ["📊 Dashboard",
         "🔄 Run Procurement Check",
         "📦 Stock Levels",
         "🏭 Suppliers",
         "📋 Orders & Invoices",
         "📜 Decision History"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("LangGraph · llama3.2:3b · SQLite")
    st.caption(f"Updated: {_now()}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":    # ── PAGE 1 ──
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parts running low", low_stock, delta="Data stale — G6 risk" if stale else None,
              delta_color="inverse")
    c2.metric("Orders awaiting delivery", n_open)
    c3.metric("Last approval gate fired", last_g)
    c4.metric("Decisions logged", n_audit)

    # ── Pipeline strip — last cycle node states ────────────────────────────────
    st.markdown("#### What Betsy Did Last Cycle")
    last_run_df = db_query(
        "SELECT run_id, MAX(timestamp) AS ts FROM audit_log GROUP BY run_id "
        "ORDER BY ts DESC LIMIT 1"
    )
    if last_run_df.empty:
        st.caption("No cycles run yet — click Run Procurement Check to start.")
    else:
        last_run_id = last_run_df["run_id"].iloc[0]
        last_run_ts = str(last_run_df["ts"].iloc[0])[:16]
        nodes_df = db_query(
            f"SELECT node, gate, decision FROM audit_log WHERE run_id = '{last_run_id}' ORDER BY id"
        )
        ran   = set(nodes_df["node"].tolist()) if not nodes_df.empty else set()
        gates = set(nodes_df["gate"].dropna().tolist()) if not nodes_df.empty else set()

        def _what(node_key):
            """Extract the short WHAT summary from the reasoning text for a node."""
            if nodes_df.empty:
                return ""
            rows = nodes_df[nodes_df["node"] == node_key]["decision"].tolist()
            if not rows:
                return ""
            text = rows[0]
            if "WHAT:" in text:
                what = text.split("WHAT:")[1]
                what = what.split("WHY:")[0].strip().rstrip(".")
                return what[:55] + "…" if len(what) > 55 else what
            return text[:55]

        # Each tuple: (node_key, short_label, icon, plain-language role)
        PIPELINE = [
            ("monitor",        "Check Stock",      "🔍", "reads inventory"),
            ("evaluate",       "Score Suppliers",  "⚖",  "ranks suppliers"),
            ("decide",         "Choose Supplier",  "🧠", "AI picks best option"),
            ("order",          "Place Order",      "📋", "creates purchase order"),
            ("track_delivery", "Track Deliveries", "🚚", "checks if orders arrived"),
            ("verify",         "Check Invoices",   "✅", "matches invoices to orders"),
        ]

        chips = []
        for node_key, label, icon, role in PIPELINE:
            node_rows  = nodes_df[nodes_df["node"] == node_key] if not nodes_df.empty else None
            has_gate   = node_rows is not None and not node_rows["gate"].dropna().empty
            gate_name  = node_rows["gate"].dropna().iloc[0] if has_gate else None
            what_text  = _what(node_key)

            if node_key not in ran:
                style = ("background:#3a3a4e;color:#888;padding:8px 14px;"
                         "border-radius:20px;font-size:12px;border:1px solid #4a4a5e")
                inner = f'<b style="opacity:0.5">{icon} {label}</b>' \
                        f'<br><span style="font-size:10px;opacity:0.4">{role}</span>'
            elif has_gate:
                style = ("background:#e67e22;color:white;padding:8px 14px;"
                         "border-radius:20px;font-size:12px;font-weight:600")
                inner = f'<b>{icon} {label}</b> <span style="background:rgba(0,0,0,0.25);' \
                        f'padding:1px 6px;border-radius:8px;font-size:10px">{gate_name}</span>' \
                        f'<br><span style="font-size:10px;opacity:0.85">{what_text[:45]}</span>'
            else:
                style = ("background:#1e8449;color:white;padding:8px 14px;"
                         "border-radius:20px;font-size:12px;font-weight:600")
                inner = f'<b>{icon} {label}</b>' \
                        f'<br><span style="font-size:10px;opacity:0.85">{what_text[:45]}</span>'

            chips.append(f'<div style="{style};text-align:center;min-width:110px">{inner}</div>')

        # Insert HITL gate chip after decide (position 3) if human approved/rejected
        if "human_approval" in ran:
            fired = list(gates - {"G6"})[0] if (gates - {"G6"}) else "Gate"
            approved = any("approve" in str(r).lower()
                           for r in nodes_df[nodes_df["node"] == "human_approval"]["decision"].tolist())
            outcome  = "Approved ✓" if approved else "Rejected ✗"
            gate_chip = (f'<div style="background:#c0392b;color:white;padding:8px 14px;'
                         f'border-radius:20px;font-size:12px;font-weight:700;text-align:center;'
                         f'min-width:90px"><b>⚡ {fired}</b><br>'
                         f'<span style="font-size:10px">{outcome}</span></div>')
            insert_at = 3 if "order" in ran else 2
            chips.insert(insert_at, gate_chip)

        arrow = '<div style="color:#555;font-size:18px;align-self:center;padding:0 2px">→</div>'
        strip_inner = arrow.join(chips)
        st.markdown(
            f'<div style="display:flex;align-items:stretch;flex-wrap:wrap;gap:6px;'
            f'padding:16px;background:#111827;border-radius:12px;'
            f'border:1px solid #1f2937">{strip_inner}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Last run: {last_run_ts} UTC (ID: {last_run_id[:8]}…)  "
            f"| 🟢 completed  🟠 needs approval  ⚡ approval given  ⬜ not needed this cycle"
        )

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

elif page == "🔄 Run Procurement Check":
    st.title("🔄 Run Procurement Check")
    st.caption("Start a full procurement check, or test a specific scenario.")

    graph = get_graph()

    # ── Session state init ─────────────────────────────────────────────────────
    if "run_log"       not in st.session_state: st.session_state.run_log       = []
    if "thread_id"     not in st.session_state: st.session_state.thread_id     = None
    if "run_id"        not in st.session_state: st.session_state.run_id        = None
    if "agent_state"   not in st.session_state: st.session_state.agent_state   = "idle"
    if "pending_gate"  not in st.session_state: st.session_state.pending_gate  = None
    if "demo_scenario" not in st.session_state: st.session_state.demo_scenario = "real"

    NODE_ICON = {
        "monitor":        "🔍 Step 1 — Checking stock levels",
        "evaluate":       "⚖ Step 2 — Scoring suppliers",
        "decide":         "🧠 Step 3 — Choosing the best supplier (AI)",
        "human_approval": "⚡ Waiting for your decision",
        "order":          "📋 Step 4 — Placing the purchase order",
        "track_delivery": "🚚 Step 5 — Checking if deliveries arrived on time",
        "verify":         "✅ Step 6 — Checking invoices match orders",
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
            "What do you want to check?",
            [
                "real — Full check (reads live inventory)",
                "g1 — High-value order: needs approval over €300",
                "g3 — Price alert: supplier price jumped more than 15%",
                "g4 — Invoice problem: amount doesn't match the order",
                "g5 — Duplicate invoice: same invoice submitted twice",
            ],
            key="demo_select",
        )
        scenario = demo_choice.split(" — ")[0].strip()

    with col_btn:
        st.write("")
        run_clicked = st.button(
            "▶ Start Check",
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

elif page == "📦 Stock Levels":
    st.title("📦 Stock Levels")

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

elif page == "📋 Orders & Invoices":
    st.title("📋 Orders & Invoices")

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

elif page == "📜 Decision History":
    st.title("📜 Decision History")
    st.caption("Every decision Betsy made — what it found, why it acted, and what happened next.")

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
