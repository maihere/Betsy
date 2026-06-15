━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 6 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is a fully implemented and running autonomous procurement
agent. The 6-node workflow is built, all gates are functional,
and the Streamlit dashboard is live. The system is in use and
being observed across multiple cycles.

Why this decision needs to be made now:
During testing and operation, Gate G3 (price spike detection)
was firing incorrectly — flagging orders as price spikes when
no real price increase had occurred. This was causing false
alerts that interrupted the autonomous cycle unnecessarily and
required the manager to approve decisions that should have
been routine. A system that fires too many false alarms loses
the manager's trust and defeats the purpose of automation.
The root cause had to be found and the design changed.

Where this fits:
DL5 established the monitoring mechanisms. This decision log
documents the first significant design change that resulted
from observing the system in operation — from monitoring
identifying a problem to managing it by changing the design.
This is DL6, following directly from DL5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

Why is the price spike gate firing on orders where the supplier
price has not actually changed — and how do we make the
detection reliable for suppliers who have no recorded price
history yet?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[ ] Analysing   [ ] Advising   [ ] Designing
[ ] Realising   [X] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
G3 must not fire for a supplier that has no previous price
recorded — a new supplier with their first recorded order
should never trigger a spike alert. Confirmed by running
the agent against a part whose only available supplier is
new to the system, and observing that G3 does not fire.

Criterion 2:
G3 must still fire when a supplier's price genuinely
increases by more than 15% compared to their recent
pricing pattern. Confirmed by testing with a supplier
whose recorded prices were €75, €75, €75, and whose
current price is €95 — a genuine 26.7% spike that
should still trigger the gate.

Criterion 3:
The change must not require any modifications to the
BetsyState schema, the gate routing logic, or the
existing tests. It must be a data-layer improvement
only — contained within the database and the Decide node.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

The G3 price spike check was redesigned in two stages.

Stage 1 (initial fix): A `price_history` table was added to
record each supplier's price per cycle. G3 was updated to
use a rolling average of the last three recorded prices as
its baseline, falling back to `last_price` if no history
existed. For suppliers with no history at all, the check
was skipped rather than defaulting to zero.

Stage 2 (follow-up fix, Sprint 6): During continued
monitoring, a second problem emerged: `record_price_history()`
was being called before `get_price_average()` in the same
function. This meant the current price was always included
in its own baseline — making the spike percentage 0% on
every run after the first. The fix reversed the baseline
priority: `last_price` from the supplier record is now the
primary baseline (it is always populated from the CSV and
represents an externally-curated reference point). The
`price_history` rolling average is used only when
`last_price` is absent. The history write was also moved
to after the G3 check so previous-cycle prices form the
baseline, not the current cycle's price. Both bugs are
documented in Bug_Log.md (Bug 2 and Bug 7).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Lab + Field + Showroom:
I used the Lab strategy to diagnose the problem — running
the agent against specific data scenarios, reading the
audit log to trace exactly what values the Decide node
was using when G3 fired incorrectly, and isolating the
calculation that produced the false alarm. I then used
the Field strategy to evaluate what the right behaviour
should be in a real procurement context — what information
a procurement manager would actually have available when
judging whether a price change is unusual.

After the fix was deployed, I used the Showroom strategy
to verify the improvement was real and visible: I
integrated LangSmith tracing into the agent so that every
node execution — including the G3 check inside the Decide
node — produces a named, timestamped trace visible in the
LangSmith dashboard. This makes the fix transparent: rather
than trusting the audit log alone, any observer can watch
the Decide node run in real time and see the G3 check
either fire or skip, with the exact values that triggered
the decision. The Showroom strategy here means
demonstrating the improvement to an audience rather than
just asserting that the fix worked.

What I found:

From the Lab diagnosis:
The original G3 check compared the current unit price
against the `last_price` field stored in the `suppliers`
table. The `last_price` field is seeded from the initial
CSV data and updated only when a new order is confirmed.

The problem occurred in two scenarios:
1. A supplier had `last_price = NULL` (no previous order
   ever recorded). The Python comparison treated NULL as
   zero, making any price look like an infinite percentage
   increase. G3 fired even though no price change had
   occurred — the supplier simply had no history.
2. A supplier had only one previous price recorded. A
   single data point is not a reliable baseline — it could
   itself have been an anomaly or a promotional price.
   Comparing against one previous price made G3 sensitive
   to normal single-order variation.

Reading the audit log confirmed both scenarios. The WHAT
entry showed G3 firing with a reason like "price €45.00
vs last price €0 — infinite% increase" — which made the
problem immediately visible without rerunning the code.

This validated the audit log design from DL3: the log
had enough information to diagnose the problem without
any additional instrumentation.

From the Field evaluation:
In real procurement practice, a price spike alert is
meaningful only when there is an established pricing
pattern to compare against. A new supplier's first
order has no baseline — the current price IS the baseline.
Flagging it as a spike would require the manager to
approve every first order from any new supplier, which
is burdensome and misleading.

A rolling average of recent prices is a more robust
baseline than a single previous price because it smooths
out one-off promotions or rounding differences and
reflects the supplier's actual pricing pattern over time.

Evidence:
The bug log entry for this problem (Bug 2 in
Bug_Log.md) — documenting the symptom, the audit log
output that revealed the root cause, and the fix applied.

The code change in the database layer — two new functions:
one to record the price observed on each order cycle for
each supplier, and one to retrieve the rolling average
of the last three recorded prices for a given supplier
and part.

The code change in the Decide node — the G3 check now
queries the price history first and only falls back to
the `last_price` field if no history exists. If neither
exists, the check is skipped entirely rather than
defaulting to zero.

What this means:
The original design had a silent assumption: that
`last_price` would always be a valid non-zero number.
This was true in the seeded CSV data but broke for
new suppliers added after deployment. The system was
making a decision (fire G3 or not) based on data that
did not exist, and defaulting to a behaviour that was
worse than doing nothing.

The redesign makes the assumption explicit: G3 only
fires when there is enough pricing history to establish
a meaningful baseline. "Enough" is defined as at least
one previous recorded price.

So I decided:
Because the Lab diagnosis confirmed the root cause was
a null-value assumption in the G3 calculation, and because
the Field evaluation confirmed that a rolling average is
a more reliable baseline than a single previous price,
the redesign adds a price history table and changes the
G3 check to use it. The fix is contained in two files
and does not change any other part of the system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — Running the agent against a part whose
only supplier is new to the system (no price_history
entries) no longer triggers G3. The check is skipped
and the order proceeds autonomously. The audit log
entry confirms: "No price history found for supplier —
G3 check skipped."

Criterion 2: ✅ — The G3 test scenario (ViennaMach,
€75→€95 = 26.7% increase) fires correctly because
ViennaMach has `last_price = 75.0` in the supplier record
(seeded from suppliers.csv). This is the primary baseline
used by the redesigned check. Current price is €95, spike
is 26.7% — gate fires. Confirmed to fire consistently
across multiple consecutive runs, including sessions where
price_history has been reset — because the baseline comes
from the supplier record, not from accumulated history.

Criterion 3: ✅ — No changes to BetsyState, no changes
to routing functions, no changes to existing tests. The
price_history table is additive. The only files changed
were betsy/database.py (two new functions and one new
table) and betsy/nodes.py (updated G3 check logic and
one new function call to record the price on each cycle).

Assumptions I am making:
The rolling average of the last three recorded prices
is a sufficient baseline. If a supplier changes their
pricing genuinely and consistently over three consecutive
cycles, the rolling average will adapt and G3 will
eventually stop firing for the new price level. This
is the intended behaviour — the gate is designed to
catch sudden changes, not sustained trends.

What surprised me:
The bug was not in the gate threshold or the gate
routing logic — it was in a silent assumption about
data quality. The `last_price` field in the suppliers
table had no null-guard because the original CSV data
always had a value. The production scenario (a new
supplier added after initial seeding) was never tested
explicitly. This is a common class of real-world bug:
edge cases that do not appear in carefully prepared
test data but occur in actual operation.

The audit log was the key to diagnosing this quickly.
Without the WHAT/WHY/NEXT trail showing exactly what
values the Decide node was using, this bug could have
taken hours to trace in the code. The transparency
mechanism paid off on the first real problem it was
needed for.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:
Bug Log entry (Bug 2) — the original symptom, the
audit log output that revealed the root cause ("price
€45.00 vs last price €0 — infinite% increase"), and
the fix applied. This is the primary evidence that the
problem was identified from operational monitoring,
not from code review.

Price history database entries — after running several
cycles, the price_history table contains recorded prices
per supplier per cycle. These entries are visible in the
database and confirm the new data collection mechanism
is working.

Code change in betsy/database.py — two new functions
(record_price_history and get_price_average) and one
new table (price_history). The functions are the
implementation of the design decision.

Code change in betsy/nodes.py — the updated G3 check
in decide_node, showing the before (single last_price
comparison) and after (rolling average with null guard).
This is the most direct evidence of what changed.

Managing phase evidence output — terminal output showing
the G3 rolling average check in action: ViennaMach
€75→€95 (+26.7%) fires the gate correctly because 3
recorded prices exist as a reliable baseline. A new
supplier (SUP-NEW-DEMO) with no price history is skipped
entirely — confirming the null-guard fix works.

![G3 fix — ViennaMach 26.7% spike fires gate; new supplier with no history skipped, not false-alarmed](<../image evidence/update price for new supplier.png>)

LangSmith trace — after integrating LangSmith tracing
into the agent (betsy/nodes.py: `@traceable` decorator on
`_invoke_llm`, `load_dotenv()` added to both entry points),
every procurement cycle produces a named trace in the
`betsy-procurement` LangSmith project. The trace shows
the full Monitor→Evaluate→Decide→Order→Track→Verify
sequence with latency per node and the G3 check result
nested inside the Decide span. The fix can be observed
directly: the `supplier-selection-llm` span shows either
"G3: price history missing — check skipped" or "G3:
rolling average €75.00, current €95.00, spike 26.7% —
gate fires." This is real-time monitoring evidence, not
just retrospective log analysis.

Autonomous approval rate KPI — a fifth metric tile on the
dashboard (added to app.py alongside the fix) shows the
percentage of runs completed without any gate interrupt.
This KPI is calculated live from the audit_log table:
(runs with no gate interrupt / total runs) × 100. As the
G3 false alarm was the primary cause of unnecessary gate
interrupts, the approval rate rising toward the 95% target
is direct evidence that the fix improved the system's
autonomy in practice. The KPI is the measuring instrument;
the LangSmith trace is the diagnostic instrument. Together
they make the managing loop complete: observe → identify
problem → fix → measure improvement.

Next LO stage: Managing continues

What I can now do that I could not before:
The price spike detection is now reliable for both
established and new suppliers. New suppliers added to
the system after initial deployment no longer cause
false G3 alerts. The rolling average means the baseline
adapts to legitimate gradual price changes while still
catching sudden spikes.

How I will know this worked:
Over the next several cycles, G3 should only fire when
a supplier's current price genuinely exceeds their recent
average by more than 15%. The audit log should show
"No price history found — G3 check skipped" for any
new supplier's first order, and the price_history table
should accumulate entries that confirm prices are being
recorded correctly.

LangSmith now gives a second confirmation channel: the
`supplier-selection-llm` span inside the Decide node trace
shows exactly which supplier was selected and what the
G3 check calculated on that run. If G3 fires, the gate
reason is visible in the trace as a labelled span with
its input and output values. If G3 is skipped, the trace
shows the skip path. This makes the fix verifiable from
outside the code, without reading the audit log — useful
when demonstrating correctness to someone who cannot
read Python.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
