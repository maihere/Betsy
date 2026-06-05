# Betsy — Autonomous Procurement Agent

Professional Research Project. LangGraph + ReAct + SQLite. Ollama local LLM.

## Project structure

```
Betsy/
│
├── app.py                  ← DASHBOARD  (streamlit run app.py → localhost:8501)
├── start_betsy.py          ← CLI        (python start_betsy.py --run / --schedule)
│
├── betsy/                  ← THE AGENT  (core library — both above import from here)
│   ├── state.py            ← BetsyState TypedDict — one run's shared memory
│   ├── database.py         ← SQLite: suppliers, purchase_orders, invoices, audit_log
│   ├── nodes.py            ← 6 nodes: Monitor→Evaluate→Decide→Order→Track→Verify
│   ├── graph.py            ← LangGraph wiring, routing, interrupt(), SqliteSaver
│   ├── prompts.py          ← LLM prompt: select supplier + explain why (no arithmetic)
│   ├── notifications.py    ← HOTL/HITL alerts → terminal + betsy_notifications.log
│   └── scheduler.py        ← APScheduler: runs a full cycle every 4 hours
│
├── agents/                 ← DL1 evidence: framework comparison
│   ├── shared_data.py      ← same test order for all 3 frameworks
│   ├── langgraph_agent.py  ← LangGraph: C1/C2/C3 all pass
│   ├── autogen_agent.py    ← AutoGen: C1/C2/C3 all fail
│   ├── crewai_agent.py     ← CrewAI: C1/C2/C3 all fail
│   └── run_all.py          ← runs all 3, prints comparison table
│
├── data/                   ← datasets read every monitoring cycle
│   ├── inventory.csv       ← 20 parts: stock levels, thresholds, timestamps
│   ├── suppliers.csv       ← approved suppliers: price, delivery, reliability
│   ├── purchase_orders.csv ← historical POs (verify_node G4 lookup)
│   └── invoices.csv        ← pending invoices — INV-TEST-001 triggers G4
│
├── run_dl3.py              ← DL3 proof: runs graph, G1 fires, shows reasoning log
├── test_gates.py           ← DL2 proof: all 6 gates fire from CSV data
├── test_model_choice.py    ← model proof: llama3.2:3b vs gemma4:e4b comparison
│
├── Documents/              ← Decision Logs 1–4, Design Document, Research Document
├── .env                    ← APPROVAL_THRESHOLD, PRICE_SPIKE_PCT, LLM_MODEL, etc.
└── requirements.txt        ← all Python dependencies
```

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.ai) running locally with `llama3.2:3b` pulled
- All dependencies: `pip install -r requirements.txt`

```powershell
ollama pull llama3.2:3b
pip install -r requirements.txt
```

## Running Betsy

### Option A — Streamlit dashboard (recommended)
```powershell
streamlit run app.py
```
Opens at **http://localhost:8501**. Use the **Run Agent** page to start a cycle, watch
each node execute live, and click **Approve / Reject** when a gate fires.
This is the primary interface. No terminal commands needed once started.

### Option B — Terminal, one cycle
```powershell
python start_betsy.py --run
```
Reads real `inventory.csv`, scores suppliers, selects best, checks all 6 gates.
Pauses and asks for your decision in the terminal when a gate fires.

### Option C — Automated schedule (runs by itself every 4 hours)
```powershell
python start_betsy.py --schedule
# Override interval (hours):
python start_betsy.py --schedule --interval=1
```
Runs a full monitoring cycle automatically on a repeating APScheduler loop.
Press Ctrl+C to stop. **The terminal window must stay open.**

For fully automatic background operation (no open terminal), register with Windows Task Scheduler:
```powershell
# Run once every 4 hours, starting now
schtasks /create /tn "BetsyMonitor" /tr "python C:\path\to\start_betsy.py --run" /sc HOURLY /mo 4
```

### Check current state
```powershell
python start_betsy.py --status
```
Shows open purchase orders, recent audit log, pending invoices from betsy.db.

### Demo scenarios (force-trigger specific gates)
```powershell
python start_betsy.py --demo g1   # G1: PART-001, 40 units × €247 = €9,880 > €300
python start_betsy.py --demo g3   # G3: PART-017, ViennaMach +26.7% price spike (qty=3, total=€285)
python start_betsy.py --demo g4   # G4: INV-TEST-001 €6,200 vs PO-2025-005 €5,775
```

### Do I need to run both the terminal AND the dashboard?

| What you want | Command |
|---|---|
| Just see the workflow | `streamlit run app.py` then use Run Agent page |
| Terminal-only, one run | `python start_betsy.py --run` |
| Automatic runs + dashboard | Two terminals: one for `--schedule`, one for `streamlit run app.py` |
| Fully automatic (no terminal) | Windows Task Scheduler (see above) + `streamlit run app.py` separately |

The scheduler and the dashboard are independent. The scheduler writes to `betsy.db`.
The dashboard reads from `betsy.db`. They do not need to run at the same time.

## Decision flow (what happens in --run)

```
Monitor reads inventory.csv
  └── 8 parts below reorder threshold found
      └── Evaluate scores approved suppliers (reliability×0.40 + price×0.35 + delivery×0.25)
          └── Decide (LLM) selects top supplier, calculates order total
              ├── G1 fires if total > €300    → HITL interrupt(), user approves/rejects
              ├── G2 fires if no supplier     → HITL interrupt()
              ├── G3 fires if price +>15%     → HITL interrupt()
              └── [approved] → Order writes PO to betsy.db
                  └── Track Delivery checks open POs for overdue
                      └── Verify reconciles pending invoice (G4/G5 if mismatch/duplicate)
```

## Gate reference

| Gate | Node | Condition | Type | Action |
|------|------|-----------|------|--------|
| G1 | Decide | order_value > €300 | HITL | interrupt(), graph pauses |
| G2 | Evaluate | no approved supplier | HITL | interrupt(), graph pauses |
| G3 | Decide | price spike > 15% | HITL | interrupt(), graph pauses |
| G4 | Verify | invoice ≠ PO total | HITL | interrupt(), payment held |
| G5 | Verify | duplicate invoice | HITL | interrupt(), payment held |
| G6 | Monitor | data > 4h old | HOTL | notify only, no order placed |

**HITL** = Human-in-the-Loop: graph is genuinely frozen via `interrupt()`. Nothing after it runs until you send `approve` or `reject`.

**HOTL** = Human-on-the-Loop: Betsy acts (or halts ordering) and notifies you. You can override within 1 hour.

## Evidence scripts (Decision Log proof)

```powershell
# DL1: framework comparison
python agents/run_all.py

# DL2: gate conditions
python test_gates.py

# DL3: graph structure + scoring formula (no LLM)
python run_dl3.py --design

# DL3: skeleton proof (full run, G1 fires from real CSV)
python graph_test.py

# Model selection
python test_model_choice.py
```

## Key files

| File | Purpose |
|------|---------|
| `betsy/state.py` | BetsyState TypedDict — all fields, one per node |
| `betsy/nodes.py` | All 6 nodes with WHAT/WHY/NEXT reasoning_log |
| `betsy/graph.py` | build_graph() (MemorySaver) + build_persistent_graph() (SqliteSaver) |
| `betsy/database.py` | init_db(), seed_suppliers(), save_purchase_order(), flush_reasoning_log() |
| `betsy.db` | SQLite: suppliers, purchase_orders, invoices, audit_log |
| `data/betsy_state.db` | LangGraph checkpointer — graph state for resume after interrupt() |
| `betsy_notifications.log` | HOTL/HITL alert history |

## Configuration (.env)

```
OLLAMA_BASE_URL=http://localhost:11434
MONITOR_INTERVAL_HOURS=4   # must be <= 4 to match G6 stale-data threshold
LLM_MODEL=llama3.2:3b
APPROVAL_THRESHOLD=300     # G1 (euros)
PRICE_SPIKE_PCT=0.15       # G3 (15%)
STALE_DATA_HOURS=4         # G6 (hours)
```

## Architecture decisions (Decision Log references) 

- **DL1** — LangGraph chosen over AutoGen/CrewAI: only framework with native interrupt(), state dict, and no platform setup.
- **DL2** — Six gates G1–G6 with HITL/HOTL/Full Autonomy mapping. €300 tail-spend boundary. 15% price spike. 4h stale data.
- **DL3** — 6-node graph design, BetsyState schema, SAW scoring formula (Fishburn 1967, Dickson 1966).
- **Model** — llama3.2:3b selected over gemma4:e4b: identical accuracy on JSON selection task, 8.6× faster (4.0s vs 34.3s). LLM trusted only for supplier selection + reasoning text, never for arithmetic.
