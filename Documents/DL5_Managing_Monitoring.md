━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 5 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is a fully implemented autonomous procurement agent.
The framework is chosen (DL1), the gates are designed (DL2),
the architecture is built (DL3), the model is selected
(DL4), and the full system runs end-to-end with a Streamlit
dashboard and CLI interface.

Why this decision needs to be made now:
Building the system is not the same as knowing it is working
correctly over time. An autonomous agent that makes
purchasing decisions on a 4-hour cycle can cause real
financial harm if it silently drifts — if gate conditions
stop firing when they should, if the audit log stops
recording, if the scheduler stops running. The question of
how to know the system is healthy is not answered by the
build itself. It requires a deliberate monitoring design.

Additionally, the assignment requires demonstrating success
criteria: Betsy must prevent at least two stockout
scenarios, catch at least one invoice error, and maintain a
95%+ autonomous approval rate. None of these can be claimed
without a way to measure and show them.

Where this fits:
DL1–DL4 cover the analysis, design, and build phases. DL5
covers the managing phase — how Betsy is observed, measured,
and improved after it is running. This is the last decision
log in the project and the one that completes the LO1–LO5
span.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

How do we know Betsy is making good decisions over time —
and what do we observe, measure, and act on to keep the
system aligned with what it was designed to do?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[ ] Analysing   [ ] Advising   [ ] Designing
[ ] Realising   [X] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
The system must provide a way to see, at a glance, whether
it has been running as intended — cycles completed,
gates fired, orders placed — without needing to read the
raw database. A dashboard that surfaces these indicators
in one view is the measure. Confirmed by opening the
dashboard and being able to answer "is Betsy working?"
in under 30 seconds.

Criterion 2:
The three assignment success criteria must be measurable
from the system's own data:
(a) At least 2 stockout scenarios prevented — visible as
    orders placed before a part reached zero stock
(b) At least 1 invoice error caught — visible as a G4 or
    G5 gate trigger in the audit log
(c) 95%+ autonomous approval rate — measurable as the
    ratio of cycles that completed without a gate firing
    to total cycles run
All three must be readable directly from the database or
dashboard, not reconstructed from memory.

Criterion 3:
When something goes wrong — a gate that should have fired
did not, a supplier score that seems wrong, a notification
that was not received — there must be enough information in
the audit log to diagnose the problem without running the
system again. Confirmed by being able to answer "why did
Betsy choose this supplier on this run?" from the audit
log alone.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

Three monitoring mechanisms were implemented: (1) a
Streamlit dashboard with live KPIs and audit log, (2) a
structured WHAT/WHY/NEXT audit log written by every node
to the database, and (3) a notifications log file that
records every HOTL and HITL alert as a permanent, readable
record. Together these provide the visibility needed to
confirm system health, measure the success criteria, and
diagnose problems.

One gap identified during this review: the 95%+ autonomous
approval rate is not yet calculated as a dashboard KPI.
This needs to be added. The data to calculate it exists
in the database — it is a reporting gap, not a data gap.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Lab + Field:
I used the Lab strategy to run multiple monitoring cycles
and observe what the system actually produces — reading the
audit log, the database tables, and the notifications file
after each run to understand what information is available
and what is missing. I then used the Field strategy to
evaluate that information against what Jenny would actually
need to trust the system and act on its outputs — what she
would look for in a daily check, what she would need to
investigate a problem, and what she would need to show her
manager that the system is working.

What I found:

From running multiple cycles and reading the outputs:

The audit log produced by the WHAT/WHY/NEXT format is
detailed enough to reconstruct every decision. Each node
records what it found (WHAT), why that finding led to its
action (WHY), and what it passed to the next step (NEXT).
After reading the log from three separate runs, the full
decision path from inventory check to purchase order was
clear without needing to inspect the code.

The Streamlit dashboard surfaces the key indicators on the
main page: number of parts currently below reorder
threshold, number of open purchase orders, the last gate
that fired, and the total number of audit log entries.
These four numbers answer the question "is Betsy working?"
in seconds.

The notifications log file records every HOTL and HITL
alert as a permanent text file entry with a timestamp.
This means that even if the dashboard is not open when a
gate fires, there is a permanent record of the alert that
survives restarts and can be reviewed at any time.

The scheduler output shows each cycle's start time and
completion status. Two automated cycles were observed
running without manual trigger, writing new audit log
entries and purchase order records to the database.

From the Field evaluation (what Jenny needs):

Jenny needs three things from a monitoring perspective:
First, a daily glance that tells her whether Betsy ran
successfully and whether anything needs her attention.
The dashboard provides this in its first page.

Second, an explanation she can give to a manager or
auditor for any specific autonomous decision. The audit
log provides this — every purchase order has a reasoning
trail in the database that identifies which supplier was
chosen, what the scores were, and why that choice was
made.

Third, evidence that the system is meeting the goals she
agreed to when adopting it: fewer stockouts, caught invoice
errors, mostly autonomous operation. The database contains
all the data needed to calculate these metrics, but the
autonomous approval rate is not yet surfaced as a KPI
in the dashboard.

Evidence:
Scheduler output — terminal log showing two consecutive
automated cycles running on the 4-hour interval, with
database entries created by each cycle.

Audit log sample — the Decision History page showing 234
logged entries with WHAT/WHY/NEXT reasoning in the
readable log view, confirming the audit trail is
accumulating correctly across runs.

![Decision History page — 234 audit log entries, WHAT/WHY/NEXT entries visible, readable log toggle shown](<../image evidence/audit log.png>)

Dashboard screenshot — the main KPI page showing 8
low-stock parts, 16 orders awaiting delivery, G1 as the
last gate fired, and 232 decisions logged. The "What Betsy
Did Last Cycle" pipeline strip shows each of the 6 nodes
with their status. Inventory Health table visible below.

![Dashboard KPI overview — 8 low stock, 16 orders awaiting, G1 last gate, 232 decisions logged, cycle pipeline strip](<../image evidence/Dashboard.png>)

Orders and invoices page — the Purchase Orders dashboard
showing open POs with delivery status and the pending
invoices section with the Verify Now button, confirming
the on-demand invoice check is accessible without running
a full cycle.

![Orders & Invoices page — PO table with delivery status, pending invoices section, Verify Now button](<../image evidence/Orders & Invoices.png>)

Git commit history — the git log confirms the build happened
in stages: initial implementation commits followed by the
managing-phase commit "DL1-DL6 documentation: evidence links,
code refs, skeleton design, G3 redesign" which marks the point
where monitoring feedback was acted on and the code was changed.

What this means:
The monitoring infrastructure that was built as part of
the implementation is sufficient to observe system health
and reconstruct any past decision. The main gap is
reporting — specifically, the 95%+ autonomous approval
rate needs to be surfaced explicitly as a dashboard KPI
so the assignment success criterion can be demonstrated
directly, not just inferred from the data.

So I decided:
The three monitoring mechanisms (dashboard, audit log,
notifications file) collectively meet the criteria for
managing an autonomous agent. Adding the approval rate
KPI closes the remaining reporting gap. The system as
implemented is observable, auditable, and aligned with
what Jenny needs to trust it in daily operation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — Opening the dashboard and reading the
four main KPIs takes under 10 seconds. The question "is
Betsy working?" can be answered immediately from the first
page without navigating to the audit log or database.

Criterion 2: 🟡 — Stockout prevention and invoice error
catching are measurable from the database. The autonomous
approval rate is calculable from the data but is not yet
shown as a dashboard KPI. This is a known gap that needs
one additional metric added to the dashboard.

Criterion 3: ✅ — The WHAT/WHY/NEXT audit log contains
enough information to diagnose any decision. Testing this
by reading the log after a gate fired incorrectly in
development (a price spike gate that fired on data where
the previous price was missing, treated as zero) allowed
the problem to be identified and fixed without rerunning
the system.

Assumptions I am making:
The audit log is only as good as what the nodes write into
it. If a node fails silently — if it encounters an error
and exits without writing its WHAT/WHY/NEXT entry — the log
will have a gap that is hard to spot. The current
implementation does not have explicit error-state logging
for silent failures. This is a monitoring blind spot.

The scheduler runs as a background process in the same
terminal session. If the terminal window is closed, the
scheduler stops. For true autonomous operation beyond a
demonstration context, the scheduler would need to be
registered with Windows Task Scheduler or a similar
system-level process manager.

What surprised me:
The value of the audit log only became clear when something
went wrong. During development, a gate fired on a run where
it should not have — the price spike gate triggered because
the previous price for a new supplier was null, and the
calculation treated null as zero, making any price look
like an infinite percentage increase. Without the
WHAT/WHY/NEXT log recording exactly what data the Decide
node saw and what calculation it ran, this bug would have
been very hard to find. The log was originally designed for
reporting and transparency — it turned out to be the most
useful debugging tool in the project.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:
Scheduler output — two automated cycles running without
manual trigger, showing the 4-hour interval working
correctly and database entries created per cycle.

Audit log sample — three full run entries in WHAT/WHY/NEXT
format, readable without code knowledge, showing consistent
decision logging across multiple cycles.

Dashboard screenshot — the KPI overview page showing system
health indicators. The open gap (approval rate KPI) is
visible as an absent metric.

Bug fix log — the null-price incident documented: what
the audit log showed, what the root cause was, and what
the fix was. Demonstrates the monitoring infrastructure
being used as intended.

Next LO stage: Portfolio compilation

What I can now do that I could not before:
I can now demonstrate that Betsy is not just built but
managed — that there is a mechanism for observing its
behaviour over time, diagnosing problems when they occur,
and improving the system based on what is observed. The
distinction between a prototype that runs once and a system
that is trusted in ongoing operation is exactly this: the
monitoring infrastructure.

How I will know this worked:
The system is working as a managed autonomous agent when:
(a) at least two stockout prevention events are visible
    in the purchase order history (parts ordered before
    stock reached zero),
(b) at least one invoice discrepancy is recorded in the
    audit log as a G4 or G5 gate trigger, and
(c) the managing phase has produced at least one
    documented design change based on what was observed —
    not just monitoring, but acting on what monitoring
    revealed.
All three are measurable from the database and the decision
logs. Evidence for (c) is documented in DL6.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT WAS BUILT AS A RESULT OF MANAGING
────────────────────────────────────────
The monitoring mechanisms identified three problems during
operation. All three were addressed with code changes — this
is what the managing phase produced:

1. G3 false alarms on new suppliers
   Monitoring revealed that G3 (price spike detection) was
   firing incorrectly when a supplier had no previous price
   recorded. The fix: a price_history table was added to
   store prices per cycle, and G3 now uses a rolling average
   as its baseline. New suppliers with no history are
   excluded from the check rather than defaulting to zero.
   Full decision log: DL6_G3_Price_Redesign.md.

2. Static reliability scores
   The scoring formula used fixed reliability scores from
   the initial CSV. Monitoring showed scores never updated
   even when deliveries were late. The fix: track_delivery_node
   now applies a reliability penalty (-3 points) when a PO
   is marked as delayed, and verify_node applies a bonus
   (+2 points) when an invoice matches cleanly. Scores now
   reflect actual delivery performance over time.
   Evidence: betsy/nodes.py (track_delivery_node and
   verify_node) and betsy/database.py
   (update_supplier_reliability function).

3. No on-demand invoice check
   Monitoring revealed that verifying a suspicious invoice
   required running a full 4-hour procurement cycle. The
   fix: the graph routing was updated so that a state with
   an invoice but no low_stock_items skips directly to
   track_delivery and verify. A "Verify Now" button was
   added to the Purchase Orders dashboard page.
   Evidence: betsy/graph.py (_after_monitor function update)
   and app.py (Verify Now section in Orders & Invoices page).

Evidence artifacts for the managing phase:

Bug_Log.md — five documented problems encountered during
operation and testing: what broke, why, what was changed.
This is the visible record of the building and managing
process — real failures, not sanitised retrospective.

betsy/database.py — the price_history table, record_price_
history() and get_price_average() functions. These additions
were made directly because of what monitoring revealed.

betsy/nodes.py — the updated track_delivery_node (reliability
penalty on delay) and the updated G3 check in decide_node
(rolling average with null guard). Before/after visible in
the git commit history.

Dynamic reliability scoring in action — terminal output
showing AccuParts Corp starting at 85.0, dropping to 82.0
after a delayed delivery (track_delivery_node, −3.0 rule),
then recovering to 84.0 after a clean invoice match
(verify_node, +2.0 rule). Net effect: −1.0 from one bad
delivery. Score reflects actual performance, not just the
seeded CSV value.

![Dynamic reliability scoring — AccuParts 85.0 to 82.0 (delay -3) to 84.0 (match +2), net -1.0](<../image evidence/reliable score update .png>)

Invoice-only routing code change — the actual
_after_monitor function from betsy/graph.py showing the
new invoice-only path, with before/after explanation: a
manager can now verify a suspicious invoice immediately
without waiting for the next 4-hour cycle.

![Invoice routing change — _after_monitor code, before/after explanation, Verify Now button context](<../image evidence/have verify invoice.png>)

Git commit history — the sequence of commits shows the
build happening in stages, with managing-phase changes
appearing after the initial implementation commits. The
commit message "Dynamic reliability scoring + price
history + approval rate KPI" marks the point where
monitoring feedback was acted on.
Screenshot captured: git log --oneline output showing
the full commit sequence from initial implementation
through to the managing-phase additions. This is the
visible record that the build happened incrementally over
time and was not produced in a single session.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
