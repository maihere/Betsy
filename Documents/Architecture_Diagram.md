# Betsy — Architecture Diagram
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
