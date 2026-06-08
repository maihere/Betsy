# Betsy — Autonomous Procurement Agent

Betsy is a research project exploring autonomous procurement: an agent that monitors
inventory, evaluates suppliers, decides when and what to reorder, places purchase
orders, tracks deliveries, and reconciles invoices — pausing for human approval
whenever a decision crosses a defined risk threshold.

Built with **LangGraph** (ReAct-style graph), **SQLite**, and a **local LLM via Ollama**
(`llama3.2:3b`). The LLM is used only for supplier selection and explaining its
reasoning in plain language — never for arithmetic or gate decisions, which are
deterministic.

## How it works

```
Monitor reads inventory.csv
  └── Parts below reorder threshold found
      └── Evaluate scores approved suppliers (reliability×0.40 + price×0.35 + delivery×0.25)
          └── Decide (LLM) selects top supplier, calculates order total
              ├── G1 fires if order total > €300     → pauses for approval
              ├── G2 fires if no approved supplier   → pauses for approval
              └── G3 fires if price spike > 15%      → pauses for approval
                  └── [approved] Order writes the PO to the database
                      └── Track Delivery flags overdue open orders
                          └── Verify reconciles pending invoices (G4/G5 if mismatch/duplicate)
```

### Gates

| Gate | Node | Condition | Type | Action |
|------|------|-----------|------|--------|
| G1 | Decide | order value > €300 | Human-in-the-loop | Graph pauses, waits for approve/reject |
| G2 | Evaluate | no approved supplier | Human-in-the-loop | Graph pauses, waits for approve/reject |
| G3 | Decide | price spike > 15% | Human-in-the-loop | Graph pauses, waits for approve/reject |
| G4 | Verify | invoice ≠ purchase order total | Human-in-the-loop | Payment held pending review |
| G5 | Verify | duplicate invoice detected | Human-in-the-loop | Payment held pending review |
| G6 | Monitor | inventory data older than 4 hours | Human-on-the-loop | Notifies only, no order placed |

**Human-in-the-loop (HITL)**: the graph genuinely freezes via `interrupt()`. Nothing
downstream runs until a human sends an approve or reject decision.

**Human-on-the-loop (HOTL)**: Betsy acts (or holds off) and notifies the human, who can
override within a defined window.

## Project structure

```
Betsy/
├── app.py                  ← Streamlit dashboard  (streamlit run app.py)
├── start_betsy.py          ← CLI entry point      (python start_betsy.py --run / --schedule)
│
├── betsy/                  ← the agent (core library)
│   ├── state.py            ← BetsyState — shared memory for one run
│   ├── database.py         ← SQLite: suppliers, purchase orders, invoices, audit log
│   ├── nodes.py            ← Monitor → Evaluate → Decide → Order → Track → Verify
│   ├── graph.py            ← LangGraph wiring, routing, interrupt(), checkpointing
│   ├── prompts.py          ← LLM prompt: select supplier + explain why
│   ├── notifications.py    ← HOTL/HITL alerts (terminal + log file)
│   └── scheduler.py        ← APScheduler — runs a full cycle every 4 hours
│
├── agents/                 ← framework comparison evidence (LangGraph vs AutoGen vs CrewAI)
├── data/                   ← inventory, suppliers, purchase orders, invoices (CSV)
├── Documents/              ← decision logs, design document, research, portfolio
│
├── run_dl3.py              ← graph design + reasoning log demo
├── test_gates.py           ← proves all 6 gates fire from CSV data
├── test_model_choice.py    ← model comparison (llama3.2:3b vs gemma)
│
├── .env                    ← APPROVAL_THRESHOLD, PRICE_SPIKE_PCT, LLM_MODEL, etc.
└── requirements.txt
```

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.ai) running locally with `llama3.2:3b` pulled

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
each node execute live, and approve or reject when a gate fires.

### Option B — Terminal, single cycle
```powershell
python start_betsy.py --run
```
Reads `inventory.csv`, scores suppliers, selects the best, checks all 6 gates, and
pauses in the terminal for a decision when a gate fires.

### Option C — Automated schedule
```powershell
python start_betsy.py --schedule
# Override interval (hours):
python start_betsy.py --schedule --interval=1
```
Runs a full monitoring cycle automatically on a repeating loop. The terminal window
must stay open. For background operation without an open terminal, register the
`--run` command with Windows Task Scheduler.

### Check current state
```powershell
python start_betsy.py --status
```
Shows open purchase orders, recent audit log entries, and pending invoices.

### Demo scenarios (force-trigger specific gates)
```powershell
python start_betsy.py --demo g1   # G1: order total > €300
python start_betsy.py --demo g3   # G3: supplier price spike > 15%
python start_betsy.py --demo g4   # G4: invoice total mismatched against its PO
```

## Configuration (.env)

```
OLLAMA_BASE_URL=http://localhost:11434
MONITOR_INTERVAL_HOURS=4   # must be <= 4 to match the G6 stale-data threshold
LLM_MODEL=llama3.2:3b
APPROVAL_THRESHOLD=300     # G1 (euros)
PRICE_SPIKE_PCT=0.15       # G3 (fraction — 0.15 = 15%)
STALE_DATA_HOURS=4         # G6 (hours)
```

## Evidence scripts

```powershell
python agents/run_all.py          # framework comparison (LangGraph vs AutoGen vs CrewAI)
python test_gates.py              # all 6 gate conditions fire from CSV data
python run_dl3.py --design        # graph structure + scoring formula
python test_model_choice.py       # model selection comparison
```

## Documentation

The `Documents/` folder contains the full project record: business analysis,
architecture diagram, decision logs (DL1–DL6) covering framework selection, gate
design, graph architecture, model selection, monitoring, and the G3 redesign, plus
the design document, ethics & responsibility statement, and portfolio collection.
