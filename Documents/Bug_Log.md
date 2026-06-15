# Bug Log — Betsy Autonomous Procurement Agent
## Problems Encountered During Build, Root Causes, and Fixes

This log documents real problems that occurred during the implementation of Betsy.
It is evidence for LO4 (Realising) — showing the visible building process including
what broke, why, and how it was resolved.

---

## Bug 1 — LLM returned prose instead of JSON

**What happened:**
The `decide_node` called `llama3.2:3b` and asked it to select a supplier. In early
runs, the model sometimes returned a paragraph of text explaining its reasoning
instead of the required JSON object. The `json.loads()` call failed, and the node
crashed before selecting a supplier or checking the gates.

**Symptom:**
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```
The node then fell back to `candidates[0]` (first supplier by reliability) without
any reasoning text being recorded — the audit log showed an empty reasoning field.

**Root cause:**
The original prompt said "respond with JSON" without specifying the exact structure.
`llama3.2:3b` interpreted this loosely and sometimes produced natural language first,
then JSON, or JSON embedded inside a sentence.

**Fix:**
The prompt was made explicit: the model receives the supplier table pre-formatted,
is told to return **only** a JSON object with two specific keys (`selected_supplier_id`
and `reasoning`), and is warned not to include any other text. The model was also
called with `format="json"` in the `ChatOllama` constructor to enforce JSON mode.

**Fix applied in:** `betsy/prompts.py` (prompt rewrite) + `betsy/nodes.py` (ChatOllama format parameter)

**What it taught:**
LLMs need explicit output format instructions, not just hints. "Respond with JSON"
is not the same as providing the exact schema and field names the node expects to parse.
This shaped the decision in DL4 to trust the LLM only for text generation, with all
arithmetic handled by Python before the prompt is even sent.

---

## Bug 2 — G3 price spike fired on new suppliers with no price history

**What happened:**
When the agent ran for the first time against a supplier that had no previous
order in the database, the `last_price` field was `None`. The G3 check in
`decide_node` used `if last_price and float(last_price) > 0` as its guard —
but `None` passed this check and caused a `TypeError` when the division ran.

More subtly: when `last_price` was stored as `0.0` (from an uninitialised CSV row),
the guard `float(last_price) > 0` correctly skipped the check. But some suppliers
had `last_price = None` in the database after seeding, which caused the crash.

**Symptom:**
```
TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'
```
The full run crashed at the G3 check and no PO was created.

**Root cause:**
The G3 guard assumed `last_price` would always be a number if present. The CSV
seed data had blank `last_price` values for newly-added suppliers, which SQLite
stored as `None` rather than `0.0`.

**Fix:**
Added an explicit `None` check: `if last_price is not None and float(last_price) > 0`.
Also updated the G3 logic to use the rolling average from `price_history` table
(3 most recent prices) as the baseline, with `last_price` as a fallback only.
This means a brand-new supplier with no history skips the G3 check entirely on
their first order — which is the correct behaviour.

**Fix applied in:** `betsy/nodes.py` (decide_node G3 section) + `betsy/database.py` (get_price_average)

**What it taught:**
Guard conditions must account for `None` explicitly in Python — truthiness checks
(`if last_price`) pass for `0.0` but fail differently for `None` vs empty string.
Always verify what the database actually stores for uninitialised fields.

---

## Bug 3 — Stale inventory timestamps blocked every run

**What happened:**
The inventory.csv file was written with timestamps from the original data creation
date (2026-06-04). Every subsequent run triggered G6 (data more than 4 hours old)
because the file timestamps were never updated between test runs.

This caused every demo and test run to halt at the Monitor node with:
```
WHAT: inventory data is stale (27.7h old). NEXT: G6 HOTL flag raised — halting.
```
No other nodes ran. No suppliers were scored. No gates past G6 could be tested.

**Symptom:**
All runs ended at Node 1 regardless of which scenario was being tested.

**Root cause:**
The inventory.csv was treated as static test data. But the `monitor_node` reads
the `data_timestamp` column and compares it to the current system time. Static
test data goes stale immediately after the first run.

**Fix:**
Added a utility that refreshes all `data_timestamp` values in inventory.csv to
the current UTC time before running tests. Also added a note to the Evidence
Capture Guide: "run the timestamp refresh command before any evidence capture
session." The demo scenarios that inject `low_stock_items` directly bypass the
G6 check by design — so they are not affected.

**Fix applied:** Python script to update inventory.csv timestamps + documented in Evidence Capture Guide

**What it taught:**
Static test data that contains timestamps has a built-in expiry. Any test that
depends on freshness checks must either refresh the data before running or bypass
the check explicitly. This informed the decision to make the demo scenarios inject
their own state rather than depending on the CSV.

---

## Bug 4 — Dashboard gate approval did not resume the correct graph thread

**What happened:**
When running the Streamlit dashboard, clicking Approve on a gate panel sometimes
resumed a different graph thread than the one that was paused. This happened when
the user started a new run on the Run Agent page before the previous run's approval
was resolved.

The symptom was that the new run's graph state would be resumed with the old run's
approval response, causing the graph to jump to a wrong node or produce a PO with
mismatched data.

**Root cause:**
`st.session_state.thread_id` was overwritten when a new run was started. The
approval flow used `st.session_state.pending_gate["config"]` to resume — but if
the session state had been overwritten, the config pointed to the new thread, not
the paused one.

**Fix:**
The pending gate config is now stored separately in `st.session_state.pending_gate`
and is cleared only after the approval flow completes. A guard was added: if a
run is in `waiting_approval` state, the Start New Run button is disabled, preventing
the user from starting a new run while a gate is pending.

**Fix applied in:** `app.py` (Run Agent page — disabled state on Start New Run button + separate gate config storage)

**What it taught:**
Streamlit's session state is shared across all page interactions. Any state that
must persist across reruns (like a paused graph config) must be stored under a
dedicated key and never overwritten by unrelated actions. Disabling UI elements
during a pending state is a safety mechanism, not just a UX choice.

---

## Bug 5 — Duplicate POs created on every test run

**What happened:**
Running `python run_dl3.py` multiple times created a new purchase order in
`betsy.db` on each run, even when the run was a test or a demonstration.
After several test sessions, the database contained 10+ identical POs for
PART-001, all showing `confirmed` status.

This inflated the open PO count on the dashboard and made the delivery tracking
node report false overdue counts (POs from earlier test runs had expected_by
dates in the past).

**Root cause:**
`run_dl3.py` and the demo scripts use `build_graph()` with a `MemorySaver`
checkpointer for isolation — but `order_node` always calls `save_purchase_order()`
which writes to the persistent `betsy.db` regardless of which checkpointer is
used. There was no test/demo flag to suppress the database write.

**Fix:**
The demo scenarios (`--demo g1/g3/g4/g5`) now auto-approve or auto-reject
through the gate without placing real POs in the database for gate-only tests.
The `run_dl3.py` proof script still writes a PO (this is intentional — it proves
the full workflow including the database write). The `--status` command was
updated to show a truncated list of recent POs rather than all POs, reducing
confusion from test data accumulation.

**Fix applied in:** `start_betsy.py` (auto-reject default) + `betsy/database.py` (INSERT OR IGNORE on POs)

**What it taught:**
Evidence scripts and production code share the same database. Test runs need to
either use an isolated database or be designed so that partial runs (auto-rejected
at a gate) do not write permanent records. The audit log and price history are
append-only by design — the PO table needed the same consideration.

---

## Bug 6 — LLM failure caused silent skip of all gates in decide_node

**What happened:**
When Ollama was not running (or unreachable), the entire `decide_node` was wrapped
in a single `try/except`. The LLM call raised a `ConnectError`, which was caught
by the outer exception handler. The node returned `{"decision": "skip"}` immediately,
before any gate checks (G1 or G3) could run. The graph routed straight to END.

From the outside this looked like: Start Check → run completes instantly → no gates
fire → no order placed → no log. The user had no way to know the agent had failed
rather than found nothing to do.

**Symptom:**
Clicking "Start Check" in the dashboard completed without any gate panel appearing,
regardless of which demo scenario was selected (G1, G3, G4). G5 still worked because
it routes directly from monitor to verify, bypassing decide_node entirely.

**Root cause:**
The outer `try/except` in `decide_node` treated an LLM connection failure as a
reason to abandon the entire node — including the gate logic that does not depend
on the LLM at all. Prices, quantities, and gate thresholds all come from the database
and inventory CSV; the LLM is only needed for supplier selection text and reasoning.

**Fix:**
The LLM call was moved into its own isolated `try/except` block. If Ollama is
unavailable or returns garbage, `decide_node` falls back to `candidates[0]` (the
top-scored supplier from `evaluate_node`) with a fallback reasoning string. The
rest of the node — G1 and G3 checks, order value calculation, gate routing —
runs normally regardless of LLM availability.

**Fix applied in:** `betsy/nodes.py` (decide_node — LLM call isolated from gate logic)

**What it taught:**
A node that wraps LLM calls in a broad exception handler can silently swallow failures
that should be visible. The LLM is responsible for one thing (supplier selection text);
all financial gate logic must be protected from LLM failure. Separating the two
responsibilities at the exception-handling level enforces this boundary in code.

---

## Bug 7 — G3 baseline contaminated by same-cycle price_history write

**What happened:**
The G3 price spike check uses a rolling average of recorded prices as its baseline.
`record_price_history()` was called immediately before `get_price_average()` in
`decide_node`. On the first run with an empty `price_history` table, this was fine:
the average returned `None`, and the fallback used `last_price` as the baseline.

But on any subsequent run, `record_price_history()` had already inserted the
current price into the table. `get_price_average()` then returned an average that
included the current price itself. The baseline equalled the current price, so
the spike percentage was always 0% — G3 never fired again.

**Symptom:**
The G3 demo (ViennaMach, €75 → €95 = +26.7%) fired correctly on the very first
run after a database reset. On every subsequent run in the same session, G3 did
not fire, and the order proceeded autonomously even though the price was genuinely
26.7% above the known baseline.

**Root cause:**
`record_price_history()` records the current price so the history accumulates
over time. But calling it before reading the average meant the current price was
always part of its own baseline — making the comparison circular. The order of
operations was: write current price → read average (includes current price) → compare
current price to average that already contains it → spike = 0%.

**Fix:**
Two changes applied together:
1. `record_price_history()` moved to after the G3 block, so the average read
   by `get_price_average()` contains only prices from previous cycles.
2. G3 baseline priority changed: `last_price` from the supplier record is now
   used as the primary baseline (it is always set from the initial CSV and
   reflects the last known price). The `price_history` rolling average is used
   only when `last_price` is not available. This makes the G3 demo reliable
   regardless of how many cycles have run — ViennaMach always has
   `last_price = 75.0`, so the 26.7% spike is always detectable.

**Fix applied in:** `betsy/nodes.py` (decide_node — G3 block reordered, baseline
priority changed to prefer `last_price` over rolling average)

**What it taught:**
Write-then-read within the same function creates a self-referential baseline that
corrupts the comparison. Any rolling average used for anomaly detection must be
read before the current value is appended to the history. Also: the `last_price`
field in the supplier record is more reliable than a freshly-written history table
as a spike baseline because it represents an externally-curated reference point,
not data produced by the same run that is being evaluated.

---