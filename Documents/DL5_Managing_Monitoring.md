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

Audit log sample — three consecutive run entries in the
WHAT/WHY/NEXT format, showing the reasoning from Monitor
through to Order for each cycle. Demonstrates that the log
is readable and consistent across runs.

Dashboard screenshot — the main KPI page showing current
low-stock count, open purchase orders, last gate fired,
and total audit entries. Shows what Jenny sees when she
opens the system.

Database state — purchase orders table with multiple
entries including gate information, showing the system
has been running and recording decisions.

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
(a) the approval rate KPI is added to the dashboard and
    reads above 95% across a run of at least five cycles,
(b) at least two stockout prevention events are visible
    in the purchase order history, and
(c) at least one invoice discrepancy is recorded in the
    audit log as a G4 or G5 gate trigger.
These are the three assignment success criteria. All three
are measurable from the database. The portfolio will
include the evidence for each.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT STILL NEEDS TO BE BUILT
─────────────────────────────
Based on this managing review, three improvements are
needed to close the gaps identified in the GAP analysis
(Stage 0) and this DL:

1. Approval rate KPI on the dashboard
   The data exists in the purchase_orders table. Add a
   metric showing: (orders placed without a gate firing) /
   (total cycles run) as a percentage. Target: 95%+.

2. Dynamic reliability scoring
   After each delivery, the actual outcome (on time / late)
   should update the supplier's reliability score in the
   database. The SAW formula currently uses static scores.
   Updating them from delivery history closes the
   "learning from past decisions" requirement from the
   assignment brief.

3. Price history table
   Store the unit price recorded each cycle per supplier.
   The G3 spike check then compares against a rolling
   average of the last three recorded prices, not just the
   single previous price. This closes the "pricing trends
   memory" requirement.

These three additions are the difference between the
current prototype and a system that fully meets every
part of the assignment brief.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
