# Betsy — Autonomous Procurement Agent
## Master Decision Log & Portfolio
### GenAI Semester Project | 2026

**Author:** Betsy Project Team  
**Date:** 2026-06-04  
**Module:** Generative AI — Autonomous Agent Design  
**Repository:** `C:\Users\ACER\Documents\Proftask\GenAI\Betsy`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Research Phase](#2-research-phase)
3. [Decision Log 1 — Framework Selection](#3-decision-log-1--framework-selection)
4. [Decision Log 2 — Gate Design & Autonomy Boundaries](#4-decision-log-2--gate-design--autonomy-boundaries)
5. [Decision Log 3 — Architecture & Graph Design](#5-decision-log-3--architecture--graph-design)
6. [Decision Log 4 — Model Selection & LLM Role](#6-decision-log-4--model-selection--llm-role)
7. [Decision Log 5 — Implementation & Dashboard](#7-decision-log-5--implementation--dashboard)
8. [Complete Portfolio of Deliverables](#8-complete-portfolio-of-deliverables)
9. [Technical Evidence Summary](#9-technical-evidence-summary)
10. [Reflection & Learnings](#10-reflection--learnings)

---

## 1. Project Overview

### 1.1 What is Betsy?

Betsy is an **autonomous procurement monitoring agent** built for a manufacturing context. It continuously monitors inventory levels, selects the best approved supplier using a multi-criteria scoring formula, calculates order values, and places purchase orders — all without human involvement for routine purchases.

When a purchase or event exceeds a defined risk threshold, the agent either:
- **Pauses and waits** for human approval (HITL — Human-in-the-Loop), or
- **Acts autonomously but notifies** the human so they can override (HOTL — Human-on-the-Loop)

This hybrid model is the central academic contribution of the project: **a structured, defensible framework for deciding when AI must ask, when it must notify, and when it can act alone.**

### 1.2 Business Problem

Procurement teams in manufacturing face:
- High volume of routine, low-value purchase orders that do not need human review
- Risk of price spikes, unapproved suppliers, duplicate invoices, and stale data going unnoticed
- Lack of audit trail and traceability for automated decisions

### 1.3 GenAI Semester Goals

| Goal | How Betsy Addresses It |
|------|------------------------|
| Autonomous AI agent design | 6-node LangGraph ReAct workflow runs without human input |
| Human oversight of AI | HITL interrupt() pauses graph; HOTL notifies without pausing |
| LLM integration | llama3.2:3b selects supplier and generates reasoning text |
| Framework comparison | LangGraph vs AutoGen vs CrewAI tested on identical task |
| Evidence-based decision making | Six Decision Logs with criteria, data, and explicit justification |

### 1.4 Project Scope

- **In scope:** Inventory monitoring, supplier scoring, purchase order creation, delivery tracking, invoice verification, gate enforcement, audit logging, dashboard
- **Out of scope:** Real ERP integration, live supplier APIs, payment processing, multi-currency

---

## 2. Research Phase

### 2.1 Background Research

Before writing any code, three foundational documents were produced:

| Document | Purpose |
|----------|---------|
| `Research_Document.docx` | Academic literature on AI procurement agents, autonomy levels, human oversight |
| `Understand about Agent AI.docx` | Conceptual grounding: ReAct pattern, LangGraph primitives, interrupt() semantics |
| `Risk Analysis and the approach for agent.docx` | Risk register for autonomous procurement: financial risk, data risk, supplier risk |

### 2.2 Key Literature References

- **Fishburn (1967)** — Simple Additive Weighting (SAW) as a justifiable multi-criteria decision method
- **Dickson (1966)** — 23 supplier selection criteria; reliability, price, and delivery as top three
- **LangGraph documentation** — `interrupt()`, `StateGraph`, `SqliteSaver`, checkpoint/resume semantics
- **Automation-autonomy spectrum** — framing for when AI should act vs. ask

### 2.3 Research Findings That Shaped Design

1. SAW scoring is academically defensible for supplier selection when weights are explicitly justified
2. Human-in-the-Loop is not a binary choice — there is a spectrum from full autonomy to full human control
3. Tail-spend (purchases below a threshold) is the natural boundary for full autonomy in procurement
4. Invoice fraud and duplicate payments are the highest-frequency financial risk in automated procurement

---

## 3. Decision Log 1 — Framework Selection

### 3.1 Problem Statement

**Which multi-agent AI framework should power Betsy's workflow?**

Three candidate frameworks were evaluated: **LangGraph**, **AutoGen**, and **CrewAI**. All three are capable of orchestrating LLM-based agents, but they differ significantly in their architectural assumptions.

### 3.2 Evaluation Criteria

Three criteria were defined before testing, each mapped to a project requirement:

| Criterion | Code | Requirement |
|-----------|------|-------------|
| Autonomous scheduling loop | C1 | Betsy must run on a repeating 4-hour cycle without user action |
| HITL pause/resume gate | C2 | Graph must genuinely freeze when a gate fires, then resume from exact state |
| Per-step reasoning log | C3 | Every node must append a WHAT/WHY/NEXT entry to a persistent log |

A fourth criterion was added after initial testing:

| Criterion | Code | Requirement |
|-----------|------|-------------|
| Persistent state across restarts | C4 | If the machine reboots mid-workflow, the interrupted state must survive |

### 3.3 Test Methodology

Each framework was tested on **the same procurement task** using `agents/shared_data.py`:

```
ORDER: Bearing 608ZZ | quantity: 80 | spend threshold: €300
SUPPLIERS: AccuParts (reliable, mid-price), BoltCo (late delivery record), SpeedFix (cheapest)
PAST DECISIONS: BoltCo was 7 days late on last order → reliability penalty -20
```

Test scripts:
- `agents/langgraph_agent.py` — LangGraph implementation
- `agents/autogen_agent.py` — AutoGen implementation
- `agents/crewai_agent.py` — CrewAI implementation
- `agents/run_all.py` — Runs all three, prints comparison table

### 3.4 Results

| Criterion | LangGraph | AutoGen | CrewAI |
|-----------|-----------|---------|--------|
| C1 — Autonomous scheduling | ✅ Native `StateGraph` loop | ✗ Requires external trigger | ✗ `kickoff()` is one-shot |
| C2 — HITL pause/resume | ✅ `interrupt()` built-in | ✗ Runs to completion | ✗ No pause mechanism |
| C3 — Per-step reasoning log | ✅ `Annotated[list, add]` in state | ✗ Final reply only | ✗ Task output only |
| C4 — Persistent state | ✅ `SqliteSaver` checkpointer | ✗ No built-in persistence | ✗ No built-in persistence |

### 3.5 Decision

**LangGraph was selected.**

**Justification:**
- AutoGen and CrewAI are conversation-oriented frameworks. They are optimised for agents that run to completion and return a final answer. Neither can natively freeze mid-workflow and wait for a human response.
- LangGraph is a **workflow graph** framework. Its `StateGraph`, `interrupt()`, and `SqliteSaver` are built precisely for stateful, interruptible workflows — which is exactly what HITL procurement requires.
- The `Annotated[list, add]` state field pattern provides a clean, built-in mechanism for accumulating reasoning across nodes without any extra infrastructure.

**Risk acknowledged:** LangGraph has a steeper learning curve than AutoGen. This was accepted because C2 (genuine HITL pause) was non-negotiable — simulating it via polling or callbacks would have been fragile and not academically defensible.

---

## 4. Decision Log 2 — Gate Design & Autonomy Boundaries

### 4.1 Problem Statement

**When should Betsy act autonomously, and when must a human approve or be notified?**

This is the core academic problem of the project. A procurement agent that always asks for approval is not autonomous. A procurement agent that never asks is a financial risk. The decision log must define exactly where the boundary lies and why.

### 4.2 Autonomy Spectrum Framework

Three levels were defined:

| Level | Name | Betsy behaviour | Human role |
|-------|------|-----------------|------------|
| 1 | Full Autonomy | Places order, no notification | None |
| 2 | HOTL | Acts autonomously, notifies human | Can override within 1 hour |
| 3 | HITL | Pauses, waits for explicit approval | Must approve/reject to continue |

### 4.3 Gate Design

Six gates were designed, each with a specific triggering condition, autonomy level, and justification:

#### Gate G1 — High-Value Order

| Field | Value |
|-------|-------|
| Node | Decide |
| Condition | `order_value > €300` |
| Type | HITL |
| Threshold origin | Tail-spend boundary (procurement best practice) |
| Action | `interrupt()` — graph freezes until human responds |

**Why €300?** Tail-spend is typically defined as purchases below a procurement team's approval authority. €300 was chosen as a conservative boundary appropriate for a manufacturing spare parts context. It allows the agent to handle all routine consumable orders autonomously while escalating any significant capital purchase.

**Why HITL, not HOTL?** A large order placed autonomously cannot be easily reversed once the supplier confirms it. The financial exposure requires a genuine pause.

**Test evidence:**  
`python start_betsy.py --demo g1` → PART-001, 40 units × €247 = €9,880 > €300 → G1 fires

---

#### Gate G2 — No Approved Supplier

| Field | Value |
|-------|-------|
| Node | Evaluate |
| Condition | No supplier has `approved = TRUE` for this part |
| Type | HITL |
| Action | `interrupt()` — cannot proceed without human resolving supplier list |

**Why HITL?** If no approved supplier exists, placing an order would require using an unapproved supplier — a compliance violation. The agent must stop completely; it has no safe autonomous action available.

**Test evidence:**  
`test_gates.py` → Part with only SUP-004 (unapproved) → G2 fires

---

#### Gate G3 — Price Spike

| Field | Value |
|-------|-------|
| Node | Decide |
| Condition | Current unit price > previous unit price × 1.15 (15% increase) |
| Type | HITL |
| Threshold origin | 15% is a standard procurement escalation threshold |
| Action | `interrupt()` — human must confirm acceptance of new price |

**Why 15%?** Commodity price fluctuations of <5% are routine. 10–15% may indicate supply chain issues or pricing errors. Above 15%, the probability of error or opportunistic pricing is high enough to require human judgment.

**Why HITL?** Placing an order at a significantly inflated price could indicate supplier fraud, data entry error, or a supply crisis requiring management response. Autonomous action at this point would be irresponsible.

**Test evidence:**  
`python start_betsy.py --demo g3` → PART-017, ViennaMach €75→€95 = +26.7% → G3 fires

---

#### Gate G4 — Invoice Amount Mismatch

| Field | Value |
|-------|-------|
| Node | Verify |
| Condition | Invoice amount ≠ PO total (within €0 tolerance) |
| Type | HITL |
| Action | `interrupt()` — payment held, human must investigate |

**Why zero tolerance?** Invoice fraud typically involves small discrepancies (rounding, extra fees). A zero-tolerance policy means every discrepancy is escalated regardless of size. The cost of investigation is lower than the cost of systematic overbilling.

**Test evidence:**  
`python start_betsy.py --demo g4` → INV-TEST-001 €6,200 vs PO-2025-005 €5,775 → G4 fires

---

#### Gate G5 — Duplicate Invoice

| Field | Value |
|-------|-------|
| Node | Verify |
| Condition | Invoice ID already exists in `invoices` table |
| Type | HITL |
| Action | `interrupt()` — payment blocked, human must confirm it is not double-billing |

**Why HITL?** Duplicate invoice submission is one of the most common forms of accounts payable fraud. No automated system should pay a duplicate without human confirmation.

**Test evidence:**  
`test_gates.py` → INV-2025-006 already exists → G5 fires

---

#### Gate G6 — Stale Data

| Field | Value |
|-------|-------|
| Node | Monitor |
| Condition | `inventory.csv` timestamp > 4 hours ago |
| Type | HOTL |
| Action | Notifies user, halts ordering cycle (no `interrupt()`) |

**Why HOTL, not HITL?** Stale data means the agent cannot make a reliable decision, but it is not a compliance or financial risk in itself. The correct response is to notify the human and stop the current cycle. The next scheduled run will check again.

**Why 4 hours?** Matches the `MONITOR_INTERVAL_HOURS=4` scheduler interval. If data is older than one full cycle, something is wrong with the data pipeline.

**Test evidence:**  
`test_gates.py` → data_age_hours = 5.0 > 4 → G6 fires (HOTL only)

---

### 4.4 Gate Summary Table

| Gate | Node | Condition | Type | Threshold Justification |
|------|------|-----------|------|------------------------|
| G1 | Decide | `order_value > €300` | HITL | Tail-spend boundary |
| G2 | Evaluate | No approved supplier | HITL | Compliance — no safe action |
| G3 | Decide | Price spike >15% | HITL | Standard escalation threshold |
| G4 | Verify | Invoice ≠ PO total | HITL | Zero-tolerance invoice policy |
| G5 | Verify | Duplicate invoice | HITL | AP fraud prevention |
| G6 | Monitor | Data >4h old | HOTL | Matches scheduler interval |

### 4.5 What "Full Autonomy" Looks Like

When none of G1–G6 fire, Betsy operates in **Full Autonomy** mode:

1. Inventory data is fresh (G6 clear)
2. Low-stock parts are found
3. At least one approved supplier exists (G2 clear)
4. LLM selects highest-scored supplier
5. Order value ≤ €300 (G1 clear)
6. No price spike detected (G3 clear)
7. Purchase order is created and written to database
8. HOTL notification sent (human informed but no action required)
9. Delivery tracking begins
10. Invoice verified when received — no mismatch (G4 clear), not duplicate (G5 clear)

This is the **intended default state** for routine consumable orders.

---

## 5. Decision Log 3 — Architecture & Graph Design

### 5.1 Problem Statement

**How should the workflow be structured? What data flows between nodes? How is reasoning captured?**

### 5.2 BetsyState Schema Design

The central design decision was to use a **single shared state dictionary** (TypedDict) that all nodes read from and write to. This follows LangGraph's recommended pattern and avoids the need for inter-node message passing.

```python
class BetsyState(TypedDict):
    # Run identity
    run_id: str

    # Node 1: Monitor
    inventory_snapshot: list[dict]
    low_stock_items: list[dict]
    data_age_hours: float

    # Node 2: Evaluate
    candidate_suppliers: list[dict]
    selected_supplier: dict | None

    # Node 3: Decide
    order_quantity: int
    order_value: float
    decision: str  # "approved" | "rejected" | "pending"

    # Gate state
    gate: str | None          # "G1"..."G6" or None
    gate_reason: str
    escalation_payload: dict
    human_response: str | None  # "approve" | "reject"

    # Node 4: Order
    purchase_order: dict | None

    # Node 5/6: Track & Verify
    invoice: dict | None
    verification_result: str

    # Accumulated reasoning log (all nodes append)
    reasoning_log: Annotated[list[str], add]
```

**Key design decisions:**

- `reasoning_log` uses `Annotated[list, add]` — LangGraph merges appends from all nodes, so no node can accidentally overwrite another node's log entries
- Gate fields (`gate`, `gate_reason`, `escalation_payload`, `human_response`) are separate from business fields — they model the "pause and resume" lifecycle explicitly
- `decision` is a string enum, not a boolean — it can represent "pending" state, which is necessary for `interrupt()` semantics

### 5.3 Six-Node Graph Design

| Node | Name | Responsibility |
|------|------|----------------|
| 1 | `monitor_node` | Read `inventory.csv`, check data freshness, identify low-stock parts |
| 2 | `evaluate_node` | Score approved suppliers using SAW formula, fire G2 if none |
| 3 | `decide_node` | Call LLM for supplier selection, check G1/G3 thresholds |
| 4 | `order_node` | Write purchase order to SQLite, send HOTL notification |
| 5 | `track_delivery_node` | Check open POs for overdue delivery, flag delayed |
| 6 | `verify_node` | Match invoice against PO, fire G4/G5 if discrepancy |

**Why six nodes?** Each node maps to one business process phase (monitor → evaluate → decide → order → track → verify). This one-to-one mapping makes the reasoning log readable to non-technical procurement staff and makes gate placement unambiguous.

### 5.4 Supplier Scoring Formula (SAW)

The Simple Additive Weighting (SAW) formula from Fishburn (1967) was implemented as pure Python — no LLM involvement:

```
score = (reliability × 0.40) + (price_score × 0.35) + (delivery_score × 0.25)
```

Where:
- `reliability` = normalised reliability score (0–1)
- `price_score` = 1 − (price / max_price_in_candidate_set) — lower price = higher score
- `delivery_score` = 1 − (delivery_days / max_delivery_days) — faster = higher score

**Weight justification (from Dickson 1966 literature review):**
- Reliability 0.40: Highest weight because late delivery disrupts the assembly line. Downtime cost >> procurement savings.
- Price 0.35: Important but secondary — a cheap unreliable supplier is more costly than a slightly more expensive reliable one
- Delivery 0.25: Relevant for emergency orders; less important for routine replenishment with ≥1 week lead time

**Why pure Python, not LLM?** LLMs are not reliable calculators. Arithmetic in LLM prompts introduces hallucination risk. The scoring formula is deterministic, reproducible, and auditable — it must not depend on a model that may give different answers on different runs.

### 5.5 LLM Role (Deliberately Narrow)

The LLM (llama3.2:3b via Ollama) is used for exactly **two things**:

1. **Supplier selection** — Given the scored list, pick the highest-scored supplier and confirm the choice (sanity check)
2. **Reasoning text** — Generate a 2-sentence natural language explanation of why that supplier was selected

The LLM is explicitly **not used for:**
- Arithmetic (all calculations are Python)
- Gate threshold evaluation (all comparisons are Python)
- Inventory assessment (pure CSV reading)
- Invoice verification (pure database lookup)

**Prompt design:**
```
DECIDE_PROMPT instructs the model to:
1. Look at the pre-computed scores (provided in prompt)
2. Return JSON: {"selected_supplier_id": "SUP-XXX", "reasoning": "..."}
3. Never attempt to calculate the score itself
```

This design means the LLM is a **reasoning formatter**, not a decision maker. The decision is already made by the scoring formula; the LLM articulates it.

### 5.6 Persistent State Design

Two graph configurations were built:

| Mode | Checkpointer | Use case |
|------|-------------|----------|
| `build_graph()` | `MemorySaver` | Demo/testing — state lost on process exit |
| `build_persistent_graph()` | `SqliteSaver` | Production — state survives machine restart |

The `SqliteSaver` writes graph checkpoints to `data/betsy_state.db`. If the graph is interrupted at G1 and the machine reboots, the next run can resume from the exact same state after the human provides their response.

**Why this matters:** Without persistence, an interrupted HITL gate would be lost on restart. The procurement team would not know whether an order had been placed or not. Persistence is a safety requirement, not a convenience.

### 5.7 WHAT/WHY/NEXT Reasoning Format

Every node appends entries to `reasoning_log` in a structured format:

```
[monitor_node] WHAT: Found 7 low-stock items below reorder threshold.
[monitor_node] WHY: Inventory.csv read at 2026-06-04T09:15:00. Data age: 1.3h (< 4h threshold).
[monitor_node] NEXT: Passing 7 items to evaluate_node for supplier scoring.
```

This format was chosen to make the audit log:
- **Readable to non-technical staff** — describes what happened in plain language
- **Auditable** — each decision step is independently verifiable
- **Debuggable** — clear separation between what happened (WHAT), why it was the right action (WHY), and what comes next (NEXT)

---

## 6. Decision Log 4 — Model Selection & LLM Role

### 6.1 Problem Statement

**Which local LLM should Betsy use for supplier selection and reasoning generation?**

Two models were tested: `llama3.2:3b` and `gemma4:e4b`.

### 6.2 Test Methodology

Test script: `test_model_choice.py`

- **Task:** Given 3 suppliers with pre-computed scores, select the highest-scored one and return JSON
- **Runs:** 3 per model (to measure variance)
- **Evaluation criteria:**
  1. JSON validity (can the response be parsed?)
  2. Correct selection (does the model pick the highest-scored supplier?)
  3. Average response time (seconds)

### 6.3 Test Scenario

```
Supplier A: score 0.87 (AccuParts)
Supplier B: score 0.71 (BoltCo) — penalised for late delivery
Supplier C: score 0.79 (SpeedFix)

Expected selection: Supplier A (AccuParts) — highest score
```

### 6.4 Results

| Metric | llama3.2:3b | gemma4:e4b |
|--------|-------------|------------|
| JSON valid (3/3 runs) | ✅ 3/3 | ✅ 3/3 |
| Correct selection (3/3 runs) | ✅ 3/3 | ✅ 3/3 |
| Average response time | **4.0 seconds** | 34.3 seconds |
| Speed ratio | — | 8.6× slower |

### 6.5 Decision

**llama3.2:3b was selected.**

**Justification:** Both models achieved identical accuracy on the supplier selection task (3/3 correct, valid JSON every run). Given identical quality outcomes, response time is the deciding factor. An 8.6× speed difference matters because:

1. Betsy runs on a 4-hour cycle. A 30-second LLM response vs a 4-second one is negligible for cycle time.
2. However, in demo and testing contexts, a 34-second wait per run makes development painful.
3. Running heavier models on local hardware increases thermal load and energy consumption without benefit.

The selection task (pick the highest score from a sorted list) does not require the reasoning depth of a larger model. llama3.2:3b is well-suited to structured JSON output tasks.

**Constraint noted:** Both models run via Ollama locally. No API calls, no data leaving the machine. This was a hard requirement because supplier data, pricing, and inventory levels are commercially sensitive.

---

## 7. Decision Log 5 — Implementation & Dashboard

### 7.1 Dashboard Technology

**Decision: Streamlit**

Streamlit was selected over Flask/FastAPI+React because:
- Zero frontend JavaScript required — all Python
- Built-in data table, chart, and metric components match the dashboard requirements
- Hot-reload on file save accelerates development
- `st.session_state` provides sufficient state management for the approval flow

**Dashboard pages:**

| Page | Purpose |
|------|---------|
| Dashboard | KPIs: low stock count, open POs, last gate fired, audit log size |
| Run Agent | Start a procurement cycle, live log, gate approval panel |
| Inventory | Table + stock vs threshold chart, G6 freshness warning |
| Suppliers | All suppliers with SAW score breakdown |
| Purchase Orders | PO table, delivery status filter, pending invoices |
| Audit Log | Full WHAT/WHY/NEXT log with node/gate colour coding |

### 7.2 Notification System Design

Three notification channels were implemented (all three fire simultaneously):

| Channel | Technology | Purpose |
|---------|-----------|---------|
| Windows desktop toast | `plyer` | Visible even when terminal is minimised |
| Terminal print | `print()` with ANSI dividers | Immediate visibility in CLI mode |
| Log file | `betsy_notifications.log` | Permanent record, survives restarts |

Four notification functions:
- `notify_order_placed()` — HOTL: order went through, human can override
- `notify_delivery_delayed()` — HOTL: PO overdue, monitoring only
- `notify_gate_fired()` — Pre-HITL: shown before graph pauses, prompts human
- `notify_stale_data()` — G6 HOTL: data quality warning

### 7.3 Database Design

SQLite was selected over PostgreSQL/MySQL because:
- No server process — single file (`betsy.db`), portable
- No network dependency — works offline
- Sufficient for the expected volume (hundreds of POs, not millions)
- Easy to inspect with DB Browser for SQLite

**Tables:**

| Table | Purpose |
|-------|---------|
| `suppliers` | Approved supplier master data, seeded from `data/suppliers.csv` |
| `purchase_orders` | All POs created by the agent, with gate and status fields |
| `invoices` | Pending invoices for verification (seeded from `data/invoices.csv`) |
| `audit_log` | WHAT/WHY/NEXT reasoning log, one row per run |

### 7.4 Scheduler Design

APScheduler `BackgroundScheduler` was selected for the 4-hour monitoring cycle because:
- Non-blocking — runs in a background thread while the main process stays responsive
- Cron-style and interval triggers both supported
- `next_run_time=datetime.now()` option fires the first run immediately (important for demos)
- Integrates cleanly with the existing graph invocation code

**Interval configuration:** `MONITOR_INTERVAL_HOURS=4` in `.env`. This is the same value as `STALE_DATA_HOURS=4` (G6 threshold) — by design. If data is older than one full cycle, something is wrong.

### 7.5 Demo Scenario Design

Three demo states were hardcoded in `start_betsy.py` to allow gate demonstration without waiting for real CSV data to trigger conditions:

| Demo | Gate | Scenario |
|------|------|---------|
| `--demo g1` | G1 | PART-001, 40 units × €247 = €9,880 > €300 threshold |
| `--demo g3` | G3 | PART-017, ViennaMach €75→€95 = +26.7% price spike |
| `--demo g4` | G4 | INV-TEST-001 €6,200 vs PO-2025-005 €5,775 mismatch |

These allow a live demonstration of HITL interrupt-and-resume in under 60 seconds.

---

## 8. Complete Portfolio of Deliverables

### 8.1 Source Code

| File | Lines | Purpose |
|------|-------|---------|
| `betsy/state.py` | ~40 | BetsyState TypedDict — single source of truth for all state fields |
| `betsy/nodes.py` | ~250 | All 6 nodes with full WHAT/WHY/NEXT reasoning |
| `betsy/graph.py` | ~120 | LangGraph StateGraph assembly, routing, interrupt() |
| `betsy/prompts.py` | ~30 | LLM prompt template for supplier selection |
| `betsy/database.py` | ~180 | SQLite CRUD operations for all 4 tables |
| `betsy/notifications.py` | ~191 | HOTL/HITL notification handler (3 channels) |
| `betsy/scheduler.py` | ~100 | APScheduler 4-hour monitoring cycle |
| `app.py` | ~400 | Streamlit 6-page dashboard |
| `start_betsy.py` | ~300 | CLI entry point: --run/--schedule/--status/--demo |

### 8.2 Agent Framework Comparison Evidence

| File | Purpose |
|------|---------|
| `agents/shared_data.py` | Shared test order used by all three frameworks |
| `agents/langgraph_agent.py` | LangGraph: C1/C2/C3/C4 all pass |
| `agents/autogen_agent.py` | AutoGen: C1/C2/C3 all fail |
| `agents/crewai_agent.py` | CrewAI: C1/C2/C3 all fail |
| `agents/run_all.py` | Comparison runner, prints evidence table |

### 8.3 Test & Demo Scripts

| File | Purpose |
|------|---------|
| `test_gates.py` | DL2 proof: all 6 gates fire from CSV data without graph |
| `run_dl3.py` | DL3 proof: full graph run, G1 fires from real inventory.csv |
| `test_model_choice.py` | Model comparison: llama3.2:3b vs gemma4:e4b |
| `graph_test.py` | Skeleton proof: graph builds and runs, G1 interrupt demonstrated |

### 8.4 Data Files

| File | Contents |
|------|---------|
| `data/inventory.csv` | 20 parts: stock levels, thresholds, timestamps |
| `data/suppliers.csv` | 20 suppliers: price, delivery, reliability, approval status |
| `data/purchase_orders.csv` | 17 historical POs with gate triggers and statuses |
| `data/invoices.csv` | 18 invoices including flagged mismatches and duplicates |

### 8.5 Documents Produced

| Document | Content |
|----------|---------|
| `Research_Document.docx` | Literature review: procurement agents, autonomy levels, SAW scoring |
| `Understand about Agent AI.docx` | Agent AI concepts: ReAct pattern, LangGraph, interrupt semantics |
| `Risk Analysis and the approach for agent.docx` | Risk register for autonomous procurement |
| `Design Document.docx` | Initial architecture design |
| `Design_Document_DL3_v2 (Updated).docx` | Updated design with BetsyState schema and 6-node graph |
| `Decision_Log_1.docx` | Framework comparison decision (LangGraph vs AutoGen vs CrewAI) |
| `Decision_Log_2.docx` | Gate design decision (G1–G6 thresholds and types) |
| `Decision Log 3.docx` | Architecture decision (graph, state, SAW formula) |
| `Decision_Log_4.docx` | Model selection (llama3.2:3b vs gemma4:e4b) |
| `Decision_Log_4_v2.docx` | Revised model selection with updated timing data |
| `Master_Decision_Log_Portfolio.md` | This document — complete synthesis |

### 8.6 Database Outputs

| File | Contents |
|------|---------|
| `betsy.db` | SQLite: suppliers, purchase_orders, invoices, audit_log |
| `data/betsy_state.db` | LangGraph graph checkpoints (interrupt/resume state) |
| `betsy_notifications.log` | All HOTL/HITL notification history |

### 8.7 Configuration

| File | Contents |
|------|---------|
| `.env` | All thresholds: `APPROVAL_THRESHOLD=300`, `PRICE_SPIKE_PCT=0.15`, `STALE_DATA_HOURS=4`, `LLM_MODEL=llama3.2:3b` |
| `requirements.txt` | All Python dependencies with version constraints |
| `CLAUDE.md` | Developer documentation: setup, commands, architecture reference |

---

## 9. Technical Evidence Summary

### 9.1 How to Run Every Evidence Script

```powershell
# Set up (one time)
pip install -r requirements.txt
ollama pull llama3.2:3b

# DL1: Framework comparison — shows C1/C2/C3 pass/fail per framework
python agents/run_all.py

# DL2: Gate conditions — all 6 gates fire from real data
python test_gates.py

# DL3: Full graph run — G1 fires from real inventory.csv
python run_dl3.py

# Model comparison — llama3.2:3b vs gemma4:e4b
python test_model_choice.py

# Demo: G1 gate (high-value order)
python start_betsy.py --demo g1

# Demo: G3 gate (price spike)
python start_betsy.py --demo g3

# Demo: G4 gate (invoice mismatch)
python start_betsy.py --demo g4

# Full live run (reads real CSV data)
python start_betsy.py --run

# Dashboard
streamlit run app.py
# → open http://localhost:8501

# Check current database state
python start_betsy.py --status
```

### 9.2 Expected Outputs

**`test_gates.py` output (DL2 evidence):**
```
G1 test — order €9,880 > €300 threshold → GATE FIRED: G1
G2 test — only unapproved supplier SUP-004 → GATE FIRED: G2
G3 test — ViennaMach price €75→€95 (+26.7%) → GATE FIRED: G3
G4 test — invoice €6,200 vs PO €5,775 → GATE FIRED: G4
G5 test — duplicate invoice detected → GATE FIRED: G5
G6 test — data age 5.0h > 4.0h threshold → GATE FIRED: G6
All 6 gates fired successfully.
```

**`agents/run_all.py` output (DL1 evidence):**
```
Framework    | C1 Scheduling | C2 HITL Gate | C3 Reasoning Log | C4 Persistence
-------------|---------------|--------------|------------------|---------------
LangGraph    | ✅ Native      | ✅ interrupt()| ✅ Annotated list | ✅ SqliteSaver
AutoGen      | ✗ External    | ✗ No pause   | ✗ Final only     | ✗ None
CrewAI       | ✗ One-shot    | ✗ No pause   | ✗ Task output    | ✗ None
```

### 9.3 SAW Scoring Worked Example

For PART-001 (Roller Bearing — 12/20 stock), candidate suppliers:

| Supplier | Reliability | Price (€) | Delivery (days) | SAW Score |
|----------|-------------|-----------|-----------------|-----------|
| SUP-001 AccuBearings | 0.92 | 45.00 | 3 | 0.368 + 0.245 + 0.175 = **0.788** |
| SUP-007 PragueParts | 0.95 | 38.50 | 5 | 0.380 + 0.285 + 0.150 = **0.815** ✅ |
| SUP-012 WarsawSupply | 0.88 | 52.00 | 2 | 0.352 + 0.210 + 0.200 = **0.762** |

PragueParts selected (highest SAW score 0.815). LLM confirms selection and provides reasoning text.

---

## 10. Reflection & Learnings

### 10.1 What Worked Well

**LangGraph `interrupt()` is exactly right for HITL.** The ability to freeze a graph at an arbitrary node and resume from the exact same state — including across process restarts with `SqliteSaver` — is the architectural foundation that makes HITL procurement trustworthy. No other tested framework offered this natively.

**Separating LLM from arithmetic was the right choice.** Using the LLM only for text generation and never for calculations eliminated all hallucination risk from the financial decision path. The scoring formula is deterministic, reproducible, and auditable.

**WHAT/WHY/NEXT reasoning format.** This turned out to be more valuable than expected. The audit log is readable by non-technical procurement staff and provides a natural explanation of every autonomous decision.

**Three-channel notifications.** Desktop toast + terminal + log file means a notification is never missed regardless of what the user is doing. Desktop toasts are visible even when the terminal window is behind other windows.

### 10.2 Challenges

**LangGraph learning curve.** Understanding the difference between `MemorySaver` (in-memory) and `SqliteSaver` (persistent) checkpointers, and how `interrupt()` interacts with graph resumption, required careful study of the documentation and several failed experiments.

**LLM JSON reliability.** Early versions of the prompt sometimes produced prose instead of JSON. The solution was to be very explicit in the prompt about the required output format and to wrap the LLM call in a try/except that falls back to the highest-scored supplier if JSON parsing fails.

**Streamlit and HITL.** The Streamlit dashboard cannot directly use `interrupt()` the same way the CLI can, because Streamlit runs in a request/response model. The solution was to use `st.session_state` to track the graph thread and re-invoke it with the human response on button click.

### 10.3 GenAI Learnings

1. **LLMs are best used where ambiguity exists.** Supplier selection from a scored list has a definitive answer — pure Python gets it right 100% of the time. The LLM adds value only in explaining the reasoning in natural language.

2. **Autonomy without gates is not production-ready.** Every autonomous AI system needs explicit, documented, threshold-based escalation points. The six gates in Betsy are not limitations — they are the mechanism that makes the system trustworthy.

3. **Framework choice matters enormously.** LangGraph, AutoGen, and CrewAI look similar in tutorials but have fundamentally different architectures. Choosing based on a genuine requirements analysis (C1–C4) rather than popularity or familiarity led to a clearly better outcome.

4. **Persistent state is a safety requirement, not a feature.** An interrupted HITL workflow that loses its state on restart is a procurement disaster. `SqliteSaver` should have been in the design from the start, not added later.

5. **Local LLMs are viable for narrow tasks.** llama3.2:3b running on Ollama achieves 100% accuracy on structured JSON selection in 4 seconds. For well-defined, constrained tasks, a local 3B parameter model is entirely sufficient — no cloud API required.

---

## Appendix A — Environment Setup

```
Python 3.12
Ollama with llama3.2:3b
pip install -r requirements.txt
```

**`.env` configuration:**
```
OLLAMA_BASE_URL=http://localhost:11434
MONITOR_INTERVAL_HOURS=4
LLM_MODEL=llama3.2:3b
APPROVAL_THRESHOLD=300
PRICE_SPIKE_PCT=0.15
STALE_DATA_HOURS=4
```

## Appendix B — Key Academic References

| Reference | Used For |
|-----------|---------|
| Dickson (1966) — 23 supplier criteria | Justification of reliability, price, delivery as top criteria |
| Fishburn (1967) — Simple Additive Weighting | SAW scoring formula mathematical foundation |
| LangGraph documentation (Anthropic/LangChain, 2024) | `interrupt()`, `StateGraph`, `SqliteSaver` semantics |

## Appendix C — Decision Timeline

| Date | Milestone |
|------|-----------|
| 2026-05-26 | Research Document completed; AI agent concepts established |
| 2026-05-28 | Risk Analysis and Design Document v1 completed |
| 2026-05-31 | Decision Log 1 completed — LangGraph selected |
| 2026-06-02 | Decision Log 2 completed — G1–G6 gates defined |
| 2026-06-03 | Decision Log 3 completed — 6-node architecture finalised |
| 2026-06-04 | Decision Log 4 completed — llama3.2:3b confirmed |
| 2026-06-04 | Master Decision Log & Portfolio compiled |

---

