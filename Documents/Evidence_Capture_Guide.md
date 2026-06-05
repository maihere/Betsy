# Evidence Capture Guide
## Betsy Autonomous Procurement Agent
### What to screenshot, what to run, and which DL each piece supports

---

## How to use this guide

Each section below covers one Decision Log. For each piece of evidence:
- **Run** tells you the exact command to run first
- **Capture** tells you exactly what to screenshot or copy
- **It shows** describes the evidence in plain language (use this exact wording in your DL and portfolio)
- **DL section** tells you where in the DL template it belongs
- **Tags to** is the Learning Outcome for PortFlow

Screenshot the terminal in a dark-background window with the font large enough to read. For dashboard screenshots, use a maximised browser window.

---

## DL1 — Framework Selection (LO1 Analysing)

### Evidence 1A — Framework comparison table (Lab evidence)

**Run:**
```powershell
python -m agents.run_all
```

**Capture:** Screenshot the full terminal output. The most important section is the table at the bottom:
```
Criterion                          LangGraph    AutoGen    CrewAI
C1 — Runs without human trigger    ✓ Yes        ✗ No       ✗ No
C2 — HITL gate (native interrupt)  ✓ Yes        ✗ No       ✗ No
C3 — Per-step audit log (native)   ✓ Yes        ✗ No       ✗ No
```
Make sure the "WHAT THIS MEANS FOR BETSY" section is visible below the table.

**It shows:** Three frameworks given the same procurement task — score suppliers, trigger an approval gate if the order exceeds the budget. Only LangGraph paused correctly at the gate. AutoGen and CrewAI both ran to completion without pausing.

**DL section:** Section 5 (Evidence) and Section 7 (Evidence artifacts)

**Tags to:** LO1 Analysing

---

### Evidence 1B — LangGraph gate firing in the comparison run (Lab evidence)

**Same run as 1A.** Scroll up to the LangGraph section output:
```
⚡ HITL GATE FIRED  (C2 in action — graph is paused)
Supplier : AccuParts Ltd @ €4.2/unit
Total    : €336.0
[demo mode] Auto-approving order.
✓ decide  (resumed after approval)
```

**Capture:** Screenshot this section specifically — it shows the interrupt happening mid-run.

**It shows:** The LangGraph workflow pausing at the approval gate, then resuming after the response was sent. AutoGen and CrewAI have no equivalent output because they cannot pause.

**DL section:** Section 5 (What I found — from the comparison test)

**Tags to:** LO1 Analysing

---

## DL2 — Gate Design & Autonomy Boundaries (LO2 Advising)

### Evidence 2A — All 6 gates firing from real data (Lab evidence)

**Run:**
```powershell
python test_gates.py
```

**Capture:** Screenshot the SUMMARY section at the bottom:
```
G1: CONFIRMED — gate fires correctly
G2: CONFIRMED — gate fires correctly
G3: CONFIRMED — gate fires correctly
G4: CONFIRMED — gate fires correctly
G5: CONFIRMED — gate fires correctly
G6: CONFIRMED — gate fires correctly
All 6 DL2 gate conditions confirmed.
```

**It shows:** All six risk conditions triggering the correct gate when the threshold is reached — tested against the real CSV data. Every gate fires on the exact condition it was designed for and does not fire when the condition is not met.

**DL section:** Section 5 (Evidence) and Section 7 (Evidence artifacts)

**Tags to:** LO2 Advising

---

### Evidence 2B — Individual gate reasoning log (Lab evidence)

**Same run as 2A.** Scroll up to see one gate in detail. Best one to capture: G4 (invoice mismatch) because it shows the plain-language reasoning:
```
G4 — Invoice Mismatch
  [PASS] Invoice €6,200.00 vs PO €5,775.00 (difference €425.00)
  reasoning_log:
    WHAT: Gate G4 fired — invoice INV-TEST-001 amount €6,200.00 does not match PO-2025-005...
    WHY:  DL2 rule: an invoice mismatch indicates a billing error or potential fraud...
    NEXT: Workflow pauses, payment held...
```

**Capture:** Screenshot the G4 section showing the WHAT/WHY/NEXT reasoning.

**It shows:** Not just that the gate fires, but that the reasoning behind it is recorded in plain language — confirming that every gate decision is explainable and auditable.

**DL section:** Section 5 (What I found — from the gate test)

**Tags to:** LO2 Advising, LO6 Professional Standard (ethics and transparency)

---

### Evidence 2C — Live HITL gate panel on dashboard (Lab + Showroom evidence)

**Run (two terminals):**
```powershell
# Terminal 1
streamlit run app.py

# Browser: open http://localhost:8501
# Navigate to: Run Agent
# Scenario: g1 — Spend gate
# Click: Start New Run
```

**Capture:** Screenshot the moment the gate fires on the dashboard — the red/orange approval panel showing:
- The gate name and reason
- The order details Betsy planned
- The Approve / Reject buttons

**It shows:** The workflow genuinely pausing mid-process in a browser interface, presenting the decision to the operations manager with enough context to make a judgment. The Approve and Reject buttons are live — clicking either resumes or cancels the workflow.

**DL section:** Section 6 (Criterion 1 — ✅ genuine pause confirmed)

**Tags to:** LO2 Advising, LO4 Realising

---

## DL3 — Architecture & Graph Design (LO3 Designing)

### Evidence 3A — Skeleton proof terminal output (Workshop + Lab evidence)

**Run:**
```powershell
python run_dl3.py
```

**Capture:** Screenshot the full terminal output showing all 6 nodes executing in sequence, the SAW scores being calculated, and the G1 gate firing. The key lines to capture:
- Each node label printing (monitor → evaluate → decide → G1 interrupt)
- The SAW score table with the winning supplier highlighted
- The "Gate G1 fired" line with the order value

**It shows:** The 6-node workflow running end-to-end against real inventory data. Each node executes in the correct order, data passes correctly between them, and the G1 gate fires when the order value exceeds €300. This is the first confirmation that the architecture works as designed.

**DL section:** Section 5 (Evidence — skeleton proof output) and Section 7

**Tags to:** LO3 Designing

---

### Evidence 3B — WHAT/WHY/NEXT reasoning log from a full run (Lab evidence)

**Run the full agent and check the database:**
```powershell
python start_betsy.py --run
# After it completes:
python start_betsy.py --status
```

**Capture:** Screenshot the "RECENT AUDIT LOG" section from `--status`, showing 3-4 entries in WHAT/WHY/NEXT format from different nodes (monitor, evaluate, decide, order).

**It shows:** The audit log accumulating entries from every node in a full run. Each entry records what Betsy observed, why that observation led to the action it took, and what it handed to the next step. This is the transparency mechanism — any past decision can be explained from this log alone.

**DL section:** Section 5 (What I found — from the Lab test) and Section 6 (Criterion 3 — ✅)

**Tags to:** LO3 Designing, LO5 Managing

---

### Evidence 3C — SAW scoring worked example (Lab evidence)

**Run:**
```powershell
python run_dl3.py --design
```

**Capture:** Screenshot the scoring table showing 3 suppliers with their reliability, price, delivery, and final SAW score — with the winner highlighted.

**It shows:** The supplier scoring formula (reliability 40% + price 35% + delivery 25%) applied to real supplier data from the CSV. The calculation is deterministic — same inputs always produce the same output. The LLM is not involved in the arithmetic.

**DL section:** Section 5 (What this means — pure Python, deterministic)

**Tags to:** LO3 Designing, LO6 Professional Standard

---

### Evidence 3D — Dashboard workflow page (Showroom evidence)

**Run the dashboard and start a real cycle:**
```powershell
streamlit run app.py
# Navigate to: Run Agent
# Scenario: real — read live inventory.csv
# Click: Start New Run
```

**Capture:** Screenshot the agent log expanding as each node completes — showing the node names and their reasoning entries appearing in real time.

**It shows:** The 6-node graph executing live in the production interface, with each node's WHAT/WHY/NEXT entry visible as it completes. This is the "demonstrating it working against a defined standard" Showroom evidence.

**DL section:** Section 7 (Evidence artifacts — full system run)

**Tags to:** LO3 Designing, LO4 Realising

---

## DL4 — Model Selection (LO4 Realising)

### Evidence 4A — Model timing comparison table (Lab evidence)

**Run (requires Ollama running with both models pulled):**
```powershell
python test_model_choice.py
```

**Capture:** Screenshot the comparison table showing:
- llama3.2:3b: valid JSON ✅, correct selection ✅, ~4.0 seconds
- gemma4:e4b: valid JSON ✅, correct selection ✅, ~34.3 seconds

**It shows:** Both models producing identical results on the supplier selection task — correct supplier chosen, valid JSON returned, three runs each. The only difference is speed: llama3.2:3b is 8.6× faster. Same quality, different cost.

**DL section:** Section 5 (Evidence — model comparison table) and Section 7

**Tags to:** LO4 Realising

---

### Evidence 4B — LLM selection inside a full Betsy run (Showroom evidence)

**Run:**
```powershell
python start_betsy.py --run
```

**Capture:** Screenshot the terminal output when the decide_node runs — specifically the section showing:
- The LLM being called
- The supplier selected and the reasoning text returned
- The order value calculated (Python, not LLM)

**It shows:** llama3.2:3b running inside the actual Betsy workflow — confirming it behaves correctly in context, not just in the isolated test. The reasoning text is natural language; the price and quantity come from Python, not the model.

**DL section:** Section 6 (Criterion 1 ✅ — valid JSON in production) and Section 7 (Showroom evidence)

**Tags to:** LO4 Realising

---

### Evidence 4C — Dashboard Suppliers page showing reliability scores (Showroom evidence)

**Run the dashboard:**
```powershell
streamlit run app.py
# Navigate to: Suppliers
```

**Capture:** Screenshot the suppliers table showing all approved suppliers with their reliability scores.

**It shows:** The supplier data that the LLM receives in its prompt — confirming that the model works with pre-calculated scores and is not responsible for any arithmetic.

**DL section:** Section 5 (What this means — LLM as formatter, not calculator)

**Tags to:** LO4 Realising

---

## DL5 — Managing & Monitoring (LO5 Managing)

### Evidence 5A — Dashboard KPI overview with autonomy rate (Lab evidence)

**Run the dashboard after at least 2 complete cycles:**
```powershell
streamlit run app.py
# Navigate to: Dashboard (main page)
```

**Capture:** Screenshot the 5 KPI metrics at the top:
- Low stock items
- Open POs (awaiting)
- Last gate fired
- Audit log entries
- **Autonomy rate** (the new metric — should show % with "target met" or "below 95%" indicator)

**It shows:** The monitoring overview that answers "is Betsy working?" in under 30 seconds. The autonomy rate KPI directly demonstrates the assignment success criterion: if 95%+ of orders are placed without a gate firing, the system is making trustworthy autonomous decisions.

**DL section:** Section 5 (Evidence — dashboard screenshot) and Section 6 (Criterion 1 ✅)

**Tags to:** LO5 Managing

---

### Evidence 5B — Audit log showing 3 consecutive runs (Lab evidence)

**Run the dashboard:**
```powershell
streamlit run app.py
# Navigate to: Audit Log
# Toggle: "Show as readable log"
```

**Capture:** Screenshot 3-4 consecutive WHAT/WHY/NEXT entries from different runs, showing the log is consistent across multiple cycles.

**It shows:** The system generating a readable decision trail on every run — not just once. Three consecutive runs with consistent WHAT/WHY/NEXT format confirms that the monitoring infrastructure is working reliably over time, not just in a single demonstration.

**DL section:** Section 5 (Evidence — audit log sample) and Section 6 (Criterion 3 ✅)

**Tags to:** LO5 Managing

---

### Evidence 5C — Scheduler running two automated cycles (Lab evidence)

**Run:**
```powershell
python start_betsy.py --schedule --interval=0.02
# Wait for 2 cycles to complete (about 2-3 minutes at 0.02h interval)
# Ctrl+C to stop
```

**Capture:** Screenshot the terminal showing two separate cycle start/end messages with timestamps between them — confirming the scheduler fired automatically without any manual trigger.

**It shows:** Betsy running two full monitoring cycles autonomously on a schedule — no human input between cycles. This is the "automated without manual trigger" evidence for the managing stage.

**DL section:** Section 5 (Evidence — scheduler output) and Section 6 (Criterion 2 ✅)

**Tags to:** LO5 Managing

---

### Evidence 5D — Purchase Orders page with Verify Invoice button (Lab + Field evidence)

**Run the dashboard:**
```powershell
streamlit run app.py
# Navigate to: Purchase Orders
# Scroll to: Pending Invoices section
```

**Capture:** Screenshot showing:
- The pending invoices table
- The "Select invoice to verify" dropdown
- The "Verify Now" button

Then click "Verify Now" on INV-TEST-001 and screenshot the G4 gate firing on this page.

**It shows:** The operations manager can check a suspicious invoice on demand — without waiting for the next scheduled cycle. The invoice verification runs as an isolated check (skipping the ordering workflow entirely) and fires the same G4/G5 gates as the full cycle.

**DL section:** Section 5 (Evidence — Field evidence: what the operations manager needs)

**Tags to:** LO5 Managing

---

### Evidence 5E — Dynamic reliability scoring (Lab evidence)

**Run after a delivery has been marked as delayed:**
```powershell
python start_betsy.py --status
# Check the audit log for "supplier reliability -3" entries
```

OR check the database directly:
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('betsy.db')
rows = conn.execute('SELECT id, name, reliability_score FROM suppliers ORDER BY reliability_score DESC LIMIT 5').fetchall()
for r in rows: print(r)
conn.close()
"
```

**Capture:** Screenshot showing supplier reliability scores — ideally before and after a delivery delay, showing the score decreasing. If you have run multiple cycles with delayed POs, some supplier scores will have changed from their seeded values.

**It shows:** Betsy's reliability scores are not static — they update based on actual delivery outcomes. A late delivery reduces the score; a matched invoice increases it. This is the "learning from past decisions" feature the assignment requires.

**DL section:** Section 7 (What this unlocks — dynamic learning is now active)

**Tags to:** LO5 Managing

---

### Evidence 5F — Price history table (Lab evidence)

**Run after at least one full cycle:**
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('betsy.db')
rows = conn.execute('SELECT supplier_id, part_id, unit_price, recorded_at FROM price_history ORDER BY recorded_at DESC LIMIT 10').fetchall()
for r in rows: print(r)
conn.close()
"
```

**Capture:** Screenshot showing price history entries — supplier ID, part ID, price recorded, and timestamp.

**It shows:** The system recording the unit price observed for each supplier on each cycle. This is the data that G3 now uses to detect price spikes — comparing the current price against a rolling average of the last 3 recorded prices, not just one previous value.

**DL section:** Section 7 (What was improved — closes pricing trends memory gap)

**Tags to:** LO5 Managing

---

## Quick Capture Order (Recommended sequence)

Run these in order. Steps 1-4 do not need Ollama running. Steps 5-9 need Ollama.

| Step | Command | Evidence produced | DL |
|---|---|---|---|
| 1 | `python test_gates.py` | All 6 gates firing | DL2 |
| 2 | `python -m agents.run_all` | Framework comparison table | DL1 |
| 3 | `python run_dl3.py --design` | SAW scoring worked example | DL3 |
| 4 | Database query (price_history) | Price history entries | DL5 |
| 5 | `python test_model_choice.py` | Model timing comparison | DL4 |
| 6 | `python run_dl3.py` | Skeleton proof with G1 firing | DL3 |
| 7 | `python start_betsy.py --run` | Full cycle, audit log | DL3, DL4 |
| 8 | `python start_betsy.py --status` | WHAT/WHY/NEXT audit entries | DL3, DL5 |
| 9 | `python start_betsy.py --schedule --interval=0.02` | Two automated cycles | DL5 |
| 10 | `streamlit run app.py` → Dashboard | 5 KPIs incl. autonomy rate | DL5 |
| 11 | `streamlit run app.py` → Run Agent → g1 | Gate approval panel live | DL2 |
| 12 | `streamlit run app.py` → Audit Log | Readable log toggle | DL3, DL5 |
| 13 | `streamlit run app.py` → Purchase Orders → Verify Now | Invoice verification flow | DL5 |

---

## Evidence Index (for Portfolio)

Use these descriptions in your portfolio Evidence Index table. Copy the plain language description — do not use filenames.

| Evidence description | Supports | Tags to |
|---|---|---|
| Framework comparison table — three frameworks given the same procurement task, criteria pass/fail recorded. LangGraph passes all four; AutoGen and CrewAI fail all four. | DL1 | LO1 |
| LangGraph mid-run pause — terminal output showing the workflow stopping at the approval gate and resuming after the response, from the comparison run. | DL1 | LO1 |
| Gate trigger test summary — all six risk conditions firing correctly from real CSV data, with "CONFIRMED" for each and "no-fire" cases verified. | DL2 | LO2 |
| Gate reasoning log — WHAT/WHY/NEXT entry from a G4 invoice mismatch, showing the plain-language explanation recorded at the moment the gate fires. | DL2 | LO2, LO6 |
| Live HITL gate panel — dashboard screenshot showing the G1 approval gate with order details, supplier alternatives, and Approve/Reject buttons active. | DL2 | LO2, LO4 |
| Skeleton proof terminal log — all 6 nodes executing in sequence on real inventory data, SAW scores visible, G1 gate firing at the correct threshold. | DL3 | LO3 |
| SAW scoring worked example — three candidate suppliers scored on reliability, price, and delivery with the winning supplier highlighted. | DL3 | LO3, LO6 |
| Dashboard agent run — screenshot of the Run Agent page with node execution log expanding in real time during a live cycle. | DL3 | LO3, LO4 |
| Model comparison table — llama3.2:3b vs gemma4:e4b across three runs each: JSON validity, correct selection, and response time side by side. | DL4 | LO4 |
| Full cycle with LLM — terminal output of the decide_node calling llama3.2:3b, receiving JSON selection, and calculating the order total in Python. | DL4 | LO4 |
| Dashboard KPI overview — five metrics including autonomy rate, showing system health at a glance after multiple completed cycles. | DL5 | LO5 |
| Audit log three consecutive runs — WHAT/WHY/NEXT entries from three separate cycles in the readable log view, confirming consistent logging. | DL5 | LO5 |
| Scheduler two-cycle output — terminal log showing two automated cycles completing on a schedule with no manual trigger between them. | DL5 | LO5 |
| Invoice verification on demand — Purchase Orders page showing the Verify Now button, invoice selection, and G4/G5 gate firing inline. | DL5 | LO5 |
| Price history database entries — table showing unit prices recorded per supplier per cycle, enabling rolling average G3 spike detection. | DL5 | LO5 |
| Dynamic reliability scores — supplier table showing reliability scores that have changed from their seeded values due to delivery outcomes. | DL5 | LO5 |

---

*Evidence Capture Guide — Betsy Autonomous Procurement Agent — GenAI Semester 2026*
