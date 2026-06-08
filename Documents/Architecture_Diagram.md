# Betsy — Architecture Diagram

## C4 Model — System, Container, and Component Views

### Level 1 — System Context

```mermaid
C4Context
    title System Context diagram for Betsy

    Person(user, "Procurement Manager", "Reviews gate alerts, approves or rejects orders, monitors stock and spend")

    System(betsy, "Betsy", "Autonomous procurement agent — monitors inventory, selects suppliers, places orders, verifies invoices")

    System_Ext(ollama, "Ollama (llama3.2:3b)", "Local LLM — selects supplier and explains reasoning in plain language")
    SystemDb_Ext(datafiles, "Data Files", "inventory.csv, suppliers.csv, purchase_orders.csv, invoices.csv — read each monitoring cycle")

    Rel(user, betsy, "Starts cycles, approves/rejects gate decisions (G1–G5)", "Streamlit dashboard / CLI")
    Rel(betsy, user, "Sends HITL/HOTL alerts when a gate fires", "Terminal + desktop notification + log file")
    Rel(betsy, ollama, "Sends supplier shortlist, requests selection + reasoning", "HTTP — Ollama API")
    Rel(betsy, datafiles, "Reads stock levels, supplier terms, PO history, pending invoices", "File I/O")
```

### Level 2 — Containers

```mermaid
C4Container
    title Container diagram for Betsy

    Person(user, "Procurement Manager")

    System_Boundary(betsy, "Betsy") {
        Container(dashboard, "Streamlit Dashboard", "Python, Streamlit", "app.py — 6-page UI: run a cycle, watch nodes live, approve/reject gates, view orders & audit log")
        Container(cli, "CLI", "Python", "start_betsy.py — --run / --schedule / --status / --demo g1|g3|g4")
        Container(scheduler, "Scheduler", "APScheduler", "betsy/scheduler.py — fires a full monitoring cycle every 4 hours")
        Container(agentcore, "Agent Core", "Python, LangGraph", "betsy/ — 6-node ReAct graph: Monitor → Evaluate → Decide → Order → Track → Verify, with gates G1–G6 and interrupt()")
        ContainerDb(db, "betsy.db", "SQLite", "suppliers, purchase_orders, invoices, audit_log")
        ContainerDb(checkpointdb, "betsy_state.db", "SQLite (LangGraph checkpointer)", "graph state — lets a paused run resume after a human decision")
    }

    System_Ext(ollama, "Ollama (llama3.2:3b)", "Local LLM runtime")
    SystemDb_Ext(datafiles, "CSV Data Files", "inventory, suppliers, purchase orders, invoices")

    Rel(user, dashboard, "Uses", "HTTPS, localhost:8501")
    Rel(user, cli, "Runs commands", "Terminal / PowerShell")

    Rel(dashboard, agentcore, "Starts a cycle, streams each node's output, sends approve/reject")
    Rel(cli, agentcore, "Starts a cycle, prints reasoning, prompts for gate decisions")
    Rel(scheduler, agentcore, "Triggers a full cycle on a timer")

    Rel(agentcore, ollama, "Supplier-selection prompt → JSON choice + reasoning", "HTTP API")
    Rel(agentcore, datafiles, "Reads inventory & supplier data each cycle")
    Rel(agentcore, db, "Reads suppliers, writes purchase orders, invoices, audit log entries")
    Rel(agentcore, checkpointdb, "Saves/restores graph state via SqliteSaver around interrupt()")

    Rel(dashboard, db, "Reads orders, invoices, audit log for display")
    Rel(dashboard, checkpointdb, "Resumes a paused graph after the user approves/rejects")
```

### Level 3 — Components (inside Agent Core)

```mermaid
C4Component
    title Component diagram for Betsy Agent Core (betsy/)

    Container_Boundary(agentcore, "Agent Core") {
        Component(graph, "Graph Builder", "graph.py", "Wires the 6 nodes into a LangGraph StateGraph, defines routing edges, calls interrupt() on gate fire, attaches the checkpointer")
        Component(nodes, "Nodes", "nodes.py", "Monitor, Evaluate, Decide, Order, Track, Verify — each checks its gate condition (G1–G6) and writes a WHAT/WHY/NEXT reasoning_log entry")
        Component(state, "State Schema", "state.py", "BetsyState TypedDict — the shared dict passed between every node")
        Component(prompts, "Prompt Templates", "prompts.py", "Builds the supplier-selection prompt; instructs the LLM to choose + explain, never to do arithmetic")
        Component(database, "Database Layer", "database.py", "init_db(), seed_suppliers(), save_purchase_order(), flush_reasoning_log() — all SQLite reads/writes")
        Component(notify, "Notifications", "notifications.py", "Formats and sends HITL/HOTL alerts to the terminal, desktop popup, and betsy_notifications.log")
        Component(sched, "Scheduler", "scheduler.py", "Wraps the graph in an APScheduler job that fires every MONITOR_INTERVAL_HOURS")
    }

    ContainerDb(db, "betsy.db", "SQLite")
    ContainerDb(checkpointdb, "betsy_state.db", "SQLite checkpointer")
    System_Ext(ollama, "Ollama (llama3.2:3b)")

    Rel(graph, nodes, "Registers as graph nodes, wires conditional routing edges")
    Rel(graph, state, "Uses BetsyState as the graph's state schema")
    Rel(graph, checkpointdb, "Persists/restores state via SqliteSaver")
    Rel(sched, graph, "Invokes a full run on each scheduled tick")

    Rel(nodes, state, "Reads and updates state fields each step")
    Rel(nodes, prompts, "Decide node builds a prompt for supplier selection")
    Rel(nodes, database, "Order/Track/Verify nodes write POs, invoices, audit entries")
    Rel(nodes, notify, "Sends an alert the moment a gate (G1–G6) fires")

    Rel(prompts, ollama, "Sends the prompt, receives a JSON supplier choice + reasoning text", "HTTP API")
    Rel(database, db, "CRUD against suppliers, purchase_orders, invoices, audit_log tables")
```

---

## 6-Node Workflow with Gate Positions

### Full Workflow (normal cycle, no gates firing)

```mermaid
flowchart TD
    SCHED([APScheduler\nfires every 4h]) --> MON

    MON["🔍 Node 1: Monitor\n─────────────────\nReads inventory.csv\nFinds parts below threshold\nChecks data freshness"]
    EVA["⚖ Node 2: Evaluate\n─────────────────\nScores approved suppliers\nSAW formula:\nreliability×0.40\nprice×0.35\ndelivery×0.25"]
    DEC["🧠 Node 3: Decide\n─────────────────\nLLM selects top supplier\nCalculates order total\nChecks G1 and G3"]
    ORD["📋 Node 4: Order\n─────────────────\nCreates purchase order\nWrites to betsy.db\nSends HOTL notification"]
    TRK["🚚 Node 5: Track\n─────────────────\nChecks open POs\nFlags overdue deliveries\nUpdates reliability score"]
    VER["✅ Node 6: Verify\n─────────────────\nMatches invoice to PO\nChecks G4 and G5\nClears payment or holds"]
    END_OK([✅ Cycle complete\nAudit log saved])

    MON --> EVA --> DEC --> ORD --> TRK --> VER --> END_OK
```

---

### Gate Positions — Where Each Risk Check Sits

```mermaid
flowchart TD
    MON[Node 1: Monitor] -->|data > 4h old| G6
    MON -->|data fresh, stock low| EVA

    EVA[Node 2: Evaluate] -->|no approved supplier| G2
    EVA -->|suppliers scored| DEC

    DEC[Node 3: Decide] -->|order > €300| G1
    DEC -->|price spike > 15%| G3
    DEC -->|all clear| ORD

    ORD[Node 4: Order] --> TRK
    TRK[Node 5: Track] --> VER

    VER[Node 6: Verify] -->|invoice ≠ PO total| G4
    VER[Node 6: Verify] -->|duplicate invoice| G5
    VER -->|invoice matches| DONE

    G6["⚡ G6 — HOTL\nHalt + notify\nNo pause"]
    G1["⚡ G1 — HITL\nPause workflow\nWait for approve/reject"]
    G2["⚡ G2 — HITL\nPause workflow\nWait for approve/reject"]
    G3["⚡ G3 — HITL\nPause workflow\nWait for approve/reject"]
    G4["⚡ G4 — HITL\nHold payment\nWait for approve/reject"]
    G5["⚡ G5 — HITL\nBlock payment\nWait for approve/reject"]
    DONE([✅ Done])

    style G1 fill:#e74c3c,color:#fff
    style G2 fill:#e67e22,color:#fff
    style G3 fill:#f39c12,color:#fff
    style G4 fill:#c0392b,color:#fff
    style G5 fill:#8e44ad,color:#fff
    style G6 fill:#2980b9,color:#fff
```

---

### Human Oversight Model — Three Levels

```
FULL AUTONOMY          HOTL                    HITL
──────────────         ──────────────────      ──────────────────────────
Order < €300           Order placed            Order > €300       G1
No price spike         Notification sent       No approved supp.  G2
Approved supplier      User can override       Price spike >15%   G3
Invoice matches        within 1 hour           Invoice mismatch   G4
                                               Duplicate invoice  G5
Betsy acts alone       Betsy acts + alerts     Betsy STOPS
                                               User must decide
```

---

### State Dictionary — Data That Flows Between Nodes

```
BetsyState (shared across all 6 nodes)
├── run_id                    ← unique ID per cycle
├── inventory_snapshot        ← all rows from inventory.csv
├── low_stock_items           ← parts below reorder threshold
├── data_age_hours            ← for G6 freshness check
├── candidate_suppliers       ← scored + ranked list
├── selected_supplier         ← chosen by LLM
├── order_quantity            ← from inventory reorder_quantity
├── order_value               ← unit_price × quantity (Python)
├── decision                  ← "order" | "skip" | "escalate"
├── purchase_order            ← PO dict written to DB
├── invoice                   ← invoice dict for G4/G5
├── verification_result       ← "match" | "mismatch" | "duplicate"
├── gate                      ← "G1"–"G6" | None
├── gate_reason               ← plain-language explanation
├── escalation_payload        ← full context sent to human
├── human_response            ← "approve" | "reject"
└── reasoning_log             ← WHAT/WHY/NEXT from every node
```

---

*Architecture Diagram — Betsy Autonomous Procurement Agent — GenAI Semester 2026*
