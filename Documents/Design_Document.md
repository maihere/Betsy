# Design Document
## Betsy — Autonomous Procurement Agent
### GenAI Semester 2026 | Professional Research Project

---

## 1. Purpose of This Document

This document describes how Betsy is designed — what the system does, how it is structured, and how the interface is laid out. It is written so that anyone can read it without needing to look at the code. It covers two things:

1. **Workflow design** — the 6-step process Betsy runs, how decisions are made, and where human approval is required
2. **Interface design** — the six screens of the Streamlit dashboard and what each one shows and does

---

## 2. What the System Is Designed to Do

Betsy is an autonomous procurement agent. It monitors a manufacturing company's inventory and manages the purchasing process automatically. It is not a chatbot — it does not wait to be asked questions. It acts on a schedule, makes decisions, and only involves a human when the decision is too risky to make alone.

**The business problem it solves:**

A procurement manager was spending 30+ hours per week on tasks that follow a consistent, rule-bound pattern: check what's running low, find the best supplier, place an order, verify the invoice. These tasks do not require strategic judgment — they require consistency and attention to detail. Betsy handles all of this automatically. The manager only sees decisions that genuinely need their judgment.

**The design principle:**

> Automate the routine. Escalate the exceptional.

Every design decision in the system traces back to this principle.

---

## 3. Agent Workflow Design

### 3.1 The Six-Step Process

Betsy runs a monitoring cycle every 4 hours. Each cycle follows the same six steps in the same order. Every step writes a plain-language record of what it found, why it acted, and what it passed to the next step. This record is the audit trail.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Step 1      │     │  Step 2      │     │  Step 3      │
│  Check Stock │────▶│  Score       │────▶│  Choose      │
│              │     │  Suppliers   │     │  Supplier    │
│  Reads the   │     │  Ranks every │     │  AI selects  │
│  inventory   │     │  approved    │     │  best option,│
│  file. Finds │     │  supplier    │     │  calculates  │
│  parts below │     │  using the   │     │  order total │
│  reorder     │     │  scoring     │     │              │
│  level.      │     │  formula.    │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                    ┌─────────────────────────────▼──────┐
                    │  GATE CHECK (Step 3)                │
                    │  G1: Order value > €300?  → STOP   │
                    │  G3: Price jumped > 15%?  → STOP   │
                    │  If neither: continue ──────────▶  │
                    └────────────────────────────────────┘
                                                  │
┌──────────────┐     ┌──────────────┐     ┌──────▼───────┐
│  Step 6      │     │  Step 5      │     │  Step 4      │
│  Check       │◀────│  Check       │◀────│  Place Order │
│  Invoices    │     │  Deliveries  │     │              │
│              │     │              │     │  Creates the │
│  Matches     │     │  Checks all  │     │  purchase    │
│  invoice     │     │  open orders │     │  order and   │
│  amount to   │     │  against     │     │  saves it to │
│  purchase    │     │  expected    │     │  the system. │
│  order total.│     │  delivery    │     │  Notifies    │
│  Flags if    │     │  dates.      │     │  manager.    │
│  different.  │     │  Flags late. │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │
┌──────▼─────────────────────────────────────────────────┐
│  GATE CHECK (Step 6)                                   │
│  G4: Invoice amount ≠ purchase order total?  → STOP   │
│  G5: Same invoice submitted twice?           → STOP   │
│  If neither: cycle complete ──────────────────────▶   │
└────────────────────────────────────────────────────────┘
```

### 3.2 How Decisions Are Made

**Supplier scoring — pure arithmetic, no AI involved:**

Every approved supplier is scored on three criteria:
- Reliability (weight 40%) — track record of on-time delivery
- Price (weight 35%) — lower price = higher score, relative to other candidates
- Delivery speed (weight 25%) — faster delivery = higher score

The formula: `Score = (reliability × 0.40) + (price × 0.35) + (delivery × 0.25)`

This formula is calculated in Python. It always produces the same result for the same inputs. It is not influenced by the AI model.

**Supplier selection — AI involved for explanation only:**

Once scores are calculated, the AI model (llama3.2:3b running locally) receives the scored list and is asked to confirm the highest-scored supplier and write a two-sentence explanation of why that supplier was chosen. The AI does not calculate anything. It reads the pre-calculated scores and explains the top result in plain language.

**Why this split?** AI language models are not reliable calculators — they can produce different answers on different runs. The financial decision (which supplier, what price, what total) must be deterministic and auditable. The AI is used only for the part where it adds value: turning numbers into a readable explanation.

### 3.3 The Six Gates — When Human Approval Is Required

Each gate is a defined risk condition. When a gate fires, the workflow freezes completely. Nothing proceeds until the manager approves or rejects.

| Gate | Fires when | Type | Why this threshold |
|---|---|---|---|
| G1 | Order total exceeds €300 | Human approval required | €300 is the tail-spend boundary — routine consumable orders stay below this. Above it, the financial commitment is large enough to warrant review. |
| G2 | No approved supplier exists for this part | Human approval required | Cannot order from an unapproved supplier — compliance violation. System must stop until resolved. |
| G3 | Current price is more than 15% above the last recorded price | Human approval required | A spike above 15% may indicate a pricing error, supply chain disruption, or opportunistic inflation. Needs judgment. |
| G4 | Invoice amount does not match the purchase order total | Human approval required — payment held | Zero-tolerance policy. Any discrepancy, however small, must be investigated before payment. |
| G5 | Same invoice submitted twice (same supplier, same PO, same amount) | Human approval required — payment blocked | Duplicate invoice submission is the most common form of accounts payable fraud. |
| G6 | Inventory data is more than 4 hours old | Notification only — no order placed | Stale data cannot be trusted for ordering. Betsy halts the cycle and notifies the manager. No approval needed — the problem is with the data feed, not a specific order. |

**The difference between G1–G5 and G6:**
- G1–G5 are HITL (Human-in-the-Loop): the workflow is frozen by `interrupt()`. Nothing runs until the human sends a response.
- G6 is HOTL (Human-on-the-Loop): Betsy acts (halts the cycle) and notifies, but does not wait. The human can acknowledge and the next scheduled cycle will check again.

### 3.4 The Audit Trail

Every step writes three lines to the audit log:
- **WHAT** — what the step observed or decided
- **WHY** — the rule or data that drove the action
- **NEXT** — what was passed to the following step

This format is designed to be readable by anyone in the procurement team, not just technical staff. Every autonomous decision has a plain-language explanation that can be reviewed at any time.

Example from Step 3:
```
WHAT: Selected AccuParts Corp for 40 × PART-001 @ €247/unit = €9,880.
WHY:  AccuParts Corp had the highest SAW score (73.0) among 3 approved
      suppliers. Reliability score 88, price competitive at €247,
      delivery 2 days.
NEXT: Order value €9,880 exceeds €300 threshold — Gate G1 triggered,
      workflow paused for approval.
```

### 3.5 Data the System Stores

The system uses four database tables:

| Table | What it holds | Why it matters |
|---|---|---|
| Suppliers | Every approved supplier: name, price per unit, delivery days, reliability score, which parts they supply | The scoring formula reads from this table on every cycle. Reliability scores update automatically after delivery outcomes. |
| Purchase Orders | Every order Betsy has placed: part, supplier, quantity, price, total, delivery status, which gate fired (if any) | The permanent record of every autonomous and approved decision. Used for delivery tracking and invoice matching. |
| Invoices | Invoices received from suppliers: amount, which purchase order it refers to, status | Used by Step 6 to check whether the invoice matches the order. |
| Audit Log | Every WHAT/WHY/NEXT entry from every step of every cycle | The transparency mechanism. Full decision trail for every run. |

And two additional tables added to support learning:

| Table | What it holds |
|---|---|
| Price History | The unit price recorded for each supplier on each cycle — enables rolling average price comparison for Gate G3 |

---

## 4. Interface Design

The Betsy dashboard is a web application built with Streamlit. It runs at `http://localhost:8501`. It has six pages accessible from the sidebar. Each page is described below.

### 4.1 Overall Layout

**Sidebar (always visible):**
- Betsy logo and name
- Navigation — six pages listed as a radio button group
- Footer showing the technology stack (LangGraph, llama3.2:3b, SQLite) and the last update time

**Main content area:**
- Page title and short description at the top
- Page-specific content below

---

### 4.2 Page 1 — Dashboard

**Purpose:** Give the manager a complete picture of the current situation in under 30 seconds.

**What it shows:**

*KPI row (four metrics side by side):*
- **Parts running low** — count of parts currently below their reorder threshold. Turns red with a warning if the inventory data is stale (older than 4 hours).
- **Orders awaiting delivery** — count of purchase orders placed but not yet received.
- **Last approval gate fired** — which gate most recently required human input (e.g. G1, G4). Shows "—" if no gate has fired.
- **Decisions logged** — total number of audit log entries across all runs.

*"What Betsy Did Last Cycle" pipeline strip:*
A horizontal row of six chips, one per step. Each chip shows:
- The step name in plain language (Check Stock / Score Suppliers / Choose Supplier / Place Order / Check Deliveries / Check Invoices)
- A short summary of what that step found (e.g. "found 8 below reorder threshold")
- Colour: green = completed without issue, orange = a gate fired in this step, grey = this step was not needed in the last cycle

If a gate fired and the manager approved or rejected it, a red chip appears in the strip showing which gate it was and whether it was approved or rejected.

*Inventory Health section:*
- A table of all 20 parts showing current stock, reorder threshold, and status (LOW / OK)
- A bar chart comparing current stock to reorder threshold for every part

*Recent Purchase Orders:*
- The five most recent purchase orders with part, supplier, total value, and delivery status

*Stale data warning:*
If inventory data is more than 4 hours old, a warning banner appears explaining that Gate G6 will fire on the next run.

---

### 4.3 Page 2 — Run Procurement Check

**Purpose:** Let the manager trigger a check manually, or test a specific scenario without waiting for the scheduled cycle.

**What it shows:**

*"What do you want to check?" dropdown:*
Five options:
1. **Full check (reads live inventory)** — runs the complete 6-step cycle against the real inventory file
2. **High-value order: needs approval over €300** — demonstrates Gate G1 with a real order that exceeds the threshold
3. **Price alert: supplier price jumped more than 15%** — demonstrates Gate G3
4. **Invoice problem: amount doesn't match the order** — demonstrates Gate G4
5. **Duplicate invoice: same invoice submitted twice** — demonstrates Gate G5 (invoice-only check, skips ordering)

*Start Check button:*
Triggers the selected scenario. While running, each step appears in the log as it completes.

*Agent log (expandable):*
Shows each step as it executes, with its WHAT/WHY/NEXT reasoning visible in real time.

*Approval panel (appears when a gate fires):*
A coloured banner showing:
- Which gate fired and why
- What Betsy was planning to do
- Betsy's reasoning (from the AI model)
- Alternative suppliers considered
- Two buttons: **Approve** and **Reject**

Clicking Approve or Reject resumes the workflow from the paused point. The result is written to the database immediately.

*Completion banner:*
When the cycle finishes, a green banner confirms the reasoning log has been saved.

---

### 4.4 Page 3 — Stock Levels

**Purpose:** Show the current state of all 20 inventory parts. Let the manager filter to see only low-stock items.

**What it shows:**

*Toggle: "Show only low-stock items"*
When on, filters the table to show only parts below their reorder threshold.

*Parts table:*
Columns: Part ID, Name, Assembly Line, Current Stock, Reorder Threshold, Reorder Quantity, Last Updated

Rows where stock is below threshold are highlighted in red with bold text.

*Stock vs Threshold bar chart:*
A bar chart for all 20 parts showing current stock (blue) alongside the reorder threshold (red). Parts where the blue bar is shorter than the red bar are the ones Betsy will act on in the next cycle.

*Data freshness indicator:*
A green or red banner at the bottom showing how old the inventory data is and whether it is within the 4-hour freshness threshold.

---

### 4.5 Page 4 — Suppliers

**Purpose:** Show all suppliers in the system, their scoring details, and the SAW formula breakdown.

**What it shows:**

*Filter by part:*
A text input that filters the supplier table to show only suppliers that supply a specific part (e.g. type "PART-001" to see only suppliers for Bearing Assembly).

*Suppliers table:*
Columns: Supplier ID, Name, Approved (yes/no), Price per Unit, Last Recorded Price, Delivery Days, Reliability Score, SAW Score, Parts Supplied

The SAW Score column shows the combined score used by the scoring formula. Higher = better.

*Score Breakdown table:*
Shows the three components of the SAW score for each supplier — reliability component (40%), price component (35%), delivery component (25%) — so the manager can see exactly how each score was calculated.

---

### 4.6 Page 5 — Orders & Invoices

**Purpose:** Show all purchase orders and pending invoices. Let the manager check a specific invoice without running a full procurement cycle.

**What it shows:**

*KPI row:*
- Total POs placed
- Awaiting delivery
- Delayed (past expected delivery date)

*Filter by delivery status:*
A dropdown to filter the orders table by: all / awaiting / delayed / delivered

*Orders table:*
Columns: PO ID, Part ID, Supplier ID, Quantity, Unit Price, Total Value, Status, Delivery Status, Expected By, Created At

Delayed rows are highlighted in red. Awaiting rows are highlighted in amber.

*Pending Invoices section:*
A table showing all invoices from the data file with status "pending".

*Verify an invoice now:*
A dropdown to select a specific pending invoice, and a "Verify Now" button. Clicking it runs only the invoice verification step (Step 6) against the selected invoice — no ordering cycle needed. The result appears inline:
- If the invoice matches the purchase order: a green confirmation
- If the invoice amount is different: Gate G4 fires with an Approve/Hold panel
- If the invoice is a duplicate: Gate G5 fires with an Approve/Void panel

---

### 4.7 Page 6 — Decision History

**Purpose:** Show the full audit trail of every decision Betsy made across all runs.

**What it shows:**

*Total log entries count.*

*Search box:*
Text search across all reasoning entries — the manager can type "G1" to see only high-value order approvals, or type a supplier name to see all decisions involving that supplier.

*Filter by gate:*
A multi-select to filter entries to specific gates only.

*Decisions table:*
Columns: Run ID, Step (node), Gate, Reasoning (WHAT/WHY/NEXT text), Timestamp

*"Show as readable log" toggle:*
When turned on, replaces the table with a formatted log view. Each entry is shown as a card with the step name in colour, the gate (if any) highlighted, and the full reasoning text visible. This is the human-readable version of the audit trail.

---

## 5. Technology Choices

| Component | Technology | Why |
|---|---|---|
| Agent framework | LangGraph | Only framework with native `interrupt()` for genuine HITL pause/resume and `SqliteSaver` for state persistence across restarts |
| Language model | llama3.2:3b via Ollama | Runs locally (no data leaves the machine), fast (2.5s average), reliable JSON output for the supplier selection task |
| Dashboard | Streamlit | Python-only, no frontend JavaScript required, built-in data tables and charts, session state for the approval flow |
| Database | SQLite | No server process, single file, portable, sufficient for prototype scale |
| Scheduling | APScheduler BackgroundScheduler | Non-blocking background thread, interval triggers, fires immediately on start |

---

## 6. What Is Out of Scope (Prototype Boundaries)

This is a working prototype. The following are known limitations that would need to be addressed before production deployment:

| Limitation | What a production system would need |
|---|---|
| Reads from CSV files | Live connection to an ERP or inventory management system |
| No real supplier APIs | Integration with supplier ordering portals or EDI |
| No email notifications | SMTP or messaging integration (Slack, Teams) |
| Single-part ordering per cycle | Batch ordering for multiple low-stock parts in one cycle |
| No multi-currency | Euro only in the prototype |
| Local Ollama required | Cloud-hosted or containerised LLM for production deployment |

---

*Design Document — Betsy Autonomous Procurement Agent — GenAI Semester 2026*
