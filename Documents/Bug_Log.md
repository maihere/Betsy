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