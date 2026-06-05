━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PORTFOLIO COLLECTION
Betsy — Autonomous Procurement Agent
GenAI Semester — Professional Research Project
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COLLECTION DESCRIPTION
──────────────────────

What this project is and why GenAI:

Betsy is an autonomous procurement agent built for a manufacturing
business where one procurement manager was spending over 30 hours a
week on tasks that follow consistent, rule-bound patterns: checking
which parts need ordering, comparing suppliers, placing purchase
orders, and verifying invoices. A simpler automated tool could handle
the repetitive parts, but it could not distinguish routine from
exceptional — it could not pause at a suspicious invoice and wait for
a human response before continuing. GenAI makes this distinction
possible: Betsy selects the best supplier using a weighted scoring
formula, writes a plain-language explanation of its reasoning, and
when a defined risk condition is triggered, freezes completely and
waits for the manager's approval before taking any further action.
The AI is not making autonomous financial decisions — it is handling
routine decisions autonomously and escalating the ones that require
human judgment.

What was built:
• A six-node automated workflow running on a 4-hour schedule:
  monitoring stock, scoring and selecting suppliers, placing orders,
  tracking deliveries, and verifying invoices without manual input
• Six approval gates that pause the workflow when risk thresholds
  are met, with nothing proceeding until the manager approves or rejects
• A Streamlit dashboard with live KPIs, a run-and-approve interface,
  and a full audit trail of every autonomous decision
• Dynamic learning mechanisms: reliability scores update from delivery
  outcomes; a price history table enables rolling average spike detection

What was left out and why:
Real ERP integration, live supplier APIs, and email notifications were
excluded to keep the focus on demonstrating the autonomous decision
and oversight mechanism. The prototype reads from CSV files and a
local SQLite database, which is sufficient to prove every research
decision documented in the six decision logs.

────────────────────────────────────────────────────────────

The research story:

The project started by investigating which agent framework should
power Betsy's workflow. Three frameworks were available — LangGraph,
AutoGen, and CrewAI — and the initial assumption was that they were
broadly comparable tools for building autonomous agents. To test
this, all three were given the same procurement task and evaluated
against four criteria that Betsy required: running without a human
trigger, pausing genuinely at an approval gate, recording a per-step
reasoning log, and preserving state across restarts. @framework_comparison
shows the result: LangGraph passed all four criteria, while AutoGen
and CrewAI both failed on the most critical one — neither could
genuinely pause mid-workflow. @autogen_failure and @crewai_failure
show both frameworks running straight through the approval gate to
completion, treating it as just another step. @langgraph_gate shows
LangGraph doing what the others could not: stopping at the gate,
waiting, and resuming from the exact same position after a response
was sent. This is evidence for LO1 Analysing because the
investigation was systematic — same task, same input, objective
pass/fail criteria — and produced a clear, data-backed reason to
choose one framework over the others.

With the framework confirmed, the next question was where the
boundaries of autonomy should sit. This required mapping every way
an autonomous procurement agent could cause financial or compliance
harm and designing a gate for each one. Research into tail-spend
practice, invoice fraud prevention, and price escalation policies
produced the thresholds: €300 as the routine-order boundary, 15% as
the price spike threshold, zero tolerance on any invoice discrepancy,
and 4 hours as the stale-data cutoff. Each gate was then tested
against real supplier and invoice data. @gate_test_g1_g2_g3 shows
gates G1, G2, and G3 firing on the exact conditions they were
designed for, with their plain-language WHAT/WHY/NEXT reasoning
entries visible. @gate_test_g4_g5_g6 shows the same for G4, G5,
and G6. @gate_reasoning_log shows a single gate entry in full,
demonstrating that the reason for every gate decision is recorded
in plain language at the moment it fires. This is evidence for
LO2 Advising because the gate design was a recommendation to a
named stakeholder — the procurement manager — with a defensible
justification for every threshold, supported by test output showing
all six conditions confirmed from real data.

The architecture decision required designing the structure of the
workflow: how many steps, what each step does, how data flows
between them, and how the system's reasoning is captured so any
past decision can be explained later. A skeleton version of the
workflow was built and tested against real inventory data before
any production code was written. @graph_run_output shows the graph
running through the 6-node sequence, a gate firing, the interrupt()
mechanism pausing the workflow, and the reasoning log being saved —
confirming the design was correct before the full build began.
@saw_scoring_dashboard shows the SAW supplier scoring formula working
live in the dashboard — every supplier's reliability, price, and
delivery components visible alongside the final weighted score.
@stock_levels_dashboard shows the monitoring step correctly
identifying low-stock parts against their reorder thresholds.
@production_cli shows the full Monitor→Evaluate→Decide→Order→Verify
pipeline confirmed in the production entry point alongside the
SqliteSaver checkpointer and HITL/HOTL mechanisms — confirming the
designed architecture was implemented correctly end-to-end. This is
evidence for LO3 Designing because the architecture was validated
by a skeleton proof before production code was written and confirmed
working again in the live system.

The model selection required testing which local AI model should
handle supplier selection. Two models were run on identical tasks
three times each. @model_comparison shows the result: both models
selected the correct supplier and returned valid responses on every
run — identical accuracy — but one averaged 2.6 seconds and the
other averaged 30.2 seconds. @production_cli confirms the selected
model is integrated into the operational pipeline: the Decide step
in the Monitor→Evaluate→Decide→Order→Verify cycle is where
llama3.2:3b runs on every cycle. @betsy_repository shows the full
codebase built from this decision — the working implementation with
its commit history showing each stage of the build. This is evidence
for LO4 Realising because the model was tested inside the actual
workflow under production conditions and the result is a working
system, not a prototype.

The managing phase revealed that building a working system is not the
same as knowing it will continue to work correctly. Three problems
were identified by observing the system across multiple cycles — not
by reading code. The first was a false alarm in the price spike gate:
it was triggering for new suppliers who had never had an order placed
with them, because the system was treating a missing previous price
as zero and calculating an infinite percentage increase.
@g3_fix_output shows the fix working in both cases: an established
supplier with a genuine 26.7% spike correctly fires the gate; a new
supplier with no price history is correctly skipped rather than
triggering a false alarm. The second problem was that supplier
reliability scores never changed from their initial values regardless
of delivery performance. @reliability_scoring shows the fix working:
AccuParts Corp's score dropping from 85 to 82 after a delayed
delivery and recovering to 84 after a clean invoice match, with the
rules from the code printed alongside the result. The third problem
was that checking a suspicious invoice required running the full
4-hour ordering cycle. @invoice_routing_change shows the code change
that fixed this — the routing function before and after, with a
plain-language explanation of what changed and why. @dashboard_kpis
shows the monitoring dashboard that made all three problems visible:
8 low-stock parts, 16 orders awaiting delivery, last gate fired, and
232 logged decisions in one view. @decision_history shows 234 audit
log entries in readable format — this is the tool that allowed each
problem to be diagnosed from its output rather than from code
inspection. @orders_invoices shows the result of the third fix: a
manager can now verify a suspicious invoice directly from the Orders
page without waiting for the next scheduled cycle. This is evidence
for LO5 Managing across DL5 and DL6, because each problem was
identified from ongoing observation and each one produced a
documented code change that improved the system's behaviour.

Growth and what changed:
The biggest shift across this project was from assuming that
frameworks and tools work as described in documentation to testing
every assumption against real data before committing to it — and
from treating a working build as the end goal to recognising that
operation reveals problems that design cannot anticipate. The full
reflection is written in @growth_reflection and linked to LO7.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DECISION LOGS
─────────────

[DL1] Which agent framework should power Betsy's workflow?          LO1
      Decision:    LangGraph selected over AutoGen and CrewAI.
      Key finding: AutoGen and CrewAI cannot genuinely pause
                   mid-workflow — they run to completion. Only
                   LangGraph has a built-in mechanism to freeze
                   the graph and resume from the exact same state.
      Evidence:    @framework_comparison  @langgraph_gate
                   @autogen_failure  @crewai_failure

[DL2] When should Betsy act autonomously and when must it           LO2
      stop and ask a human?
      Decision:    Six gates (G1–G6) with specific thresholds
                   and a HITL/HOTL classification for each.
      Key finding: HITL and HOTL answer different questions.
                   HITL is for decisions that cannot safely proceed
                   without a human response. HOTL is for conditions
                   where Betsy must stop but there is nothing to approve.
      Evidence:    @gate_test_g1_g2_g3  @gate_test_g4_g5_g6
                   @gate_reasoning_log

[DL3] How should the workflow be structured so each step has        LO3
      one clear responsibility, data flows correctly, and
      every decision is explainable?
      Decision:    Six-node sequential graph, shared state
                   dictionary, SAW scoring in pure Python,
                   WHAT/WHY/NEXT reasoning log per node.
      Key finding: The linear structure keeps gate placement
                   unambiguous. The skeleton proof confirmed the
                   design before any production code was written.
      Evidence:    @graph_run_output  @saw_scoring_dashboard
                   @stock_levels_dashboard  @production_cli

[DL4] Which local AI model should handle supplier selection         LO4
      and reasoning generation?
      Decision:    llama3.2:3b selected over gemma4:e4b.
      Key finding: Identical accuracy across every run. One model
                   averaged 2.6 seconds, the other 30.2 seconds —
                   eleven times slower with no quality benefit for
                   this specific task.
      Evidence:    @model_comparison  @production_cli
                   @betsy_repository

[DL5] How do we know Betsy is making good decisions over            LO5
      time — and what do we do when it is not?
      Decision:    Three monitoring mechanisms (dashboard, audit
                   log, notifications) plus three code changes
                   made directly from what monitoring revealed.
      Key finding: The audit log was the most valuable tool in
                   the project — not for reporting, but for
                   diagnosing problems that only appeared in
                   real operation.
      Evidence:    @dashboard_kpis  @decision_history
                   @orders_invoices  @reliability_scoring
                   @invoice_routing_change

[DL6] Why is the price spike gate firing on new suppliers when      LO5
      no price increase has actually occurred?
      Decision:    G3 redesigned to use a rolling average from a
                   price history table. New suppliers with no
                   history skip the check entirely.
      Key finding: The bug was not in the gate logic — it was a
                   silent assumption that a missing price meant
                   zero, which only appeared with data the test
                   scenarios had never covered.
      Evidence:    @g3_fix_output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EVIDENCE INDEX
──────────────

@framework_comparison
Description: Three agent frameworks given the same procurement
             task — a criteria table showing pass/fail for C1
             (runs without trigger), C2 (genuine HITL pause),
             and C3 (per-step reasoning log). LangGraph passes
             all three. AutoGen and CrewAI fail on C2 and C3.
             The "What This Means for Betsy" section below the
             table explains the architectural difference.
Supports:    DL1
Tags to:     LO1

@langgraph_gate
Description: LangGraph workflow pausing at the approval gate
             mid-run — interrupt() executing, the gate details
             and order total shown, and the graph resuming after
             the approval response was sent. C2 and C3 confirmed
             in a single terminal output.
Supports:    DL1
Tags to:     LO1

@autogen_failure
Description: AutoGen running the same task to completion without
             pausing at the approval gate. The gate condition was
             evaluated but the workflow continued regardless.
             No per-step log produced.
Supports:    DL1
Tags to:     LO1

@crewai_failure
Description: CrewAI running the same task to completion without
             pausing. Same failure pattern as AutoGen — no genuine
             pause mechanism and no per-step reasoning log.
Supports:    DL1
Tags to:     LO1

@gate_test_g1_g2_g3
Description: Gates G1 (order value €9,880 exceeds €300 threshold),
             G2 (unapproved supplier FastParts GmbH blocked), and
             G3 (ViennaMach price spike +26.7%) firing from real
             data. Each gate shows its WHAT/WHY/NEXT reasoning
             entry and the no-fire case confirming it does not
             trigger when the condition is not met.
Supports:    DL2
Tags to:     LO2

@gate_test_g4_g5_g6
Description: Gates G4 (invoice €6,200 vs PO €5,775 — mismatch
             of €425), G5 (duplicate invoice INV-2025-006 matches
             INV-2025-001), and G6 (inventory data 8,959 hours
             old — stale) firing from real data with WHAT/WHY/NEXT
             reasoning entries. No-fire cases confirmed for each.
Supports:    DL2
Tags to:     LO2

@gate_reasoning_log
Description: A single gate reasoning entry shown in full — G5
             duplicate invoice — with the exact data the gate
             acted on, the DL2 rule it applied, and the action
             taken (payment held, workflow paused). Demonstrates
             that every gate decision is recorded in plain language
             at the moment it fires.
Supports:    DL2
Tags to:     LO2, LO6

@graph_run_output
Description: Full graph run terminal output showing all six nodes
             executing in sequence. G6 fires (stale data 6.8 hours),
             interrupt() pauses the workflow, the human approves,
             the graph resumes, and the reasoning log is saved to
             the database. Confirms the designed node sequence,
             gate mechanism, and audit trail all work together.
Supports:    DL3
Tags to:     LO3

@saw_scoring_dashboard
Description: Suppliers dashboard showing all approved suppliers
             with their reliability, price, and delivery values
             and the final SAW score for each. The score breakdown
             table below confirms the three weighted components
             (reliability 40%, price 35%, delivery 25%) are applied
             correctly. Demonstrates the scoring formula is
             transparent and deterministic.
Supports:    DL3
Tags to:     LO3, LO6

@stock_levels_dashboard
Description: Stock Levels dashboard showing 8 low-stock parts
             highlighted in red against their reorder thresholds,
             with the Stock vs Threshold bar chart for all 20
             parts. Confirms the Monitor node correctly identifies
             which parts need ordering from the live inventory data.
Supports:    DL3
Tags to:     LO3

@production_cli
Description: CLI startup output showing the full
             Monitor→Evaluate→Decide→Order→Verify pipeline,
             the four run modes (--run, --schedule, --status,
             --demo), build_persistent_graph() with SqliteSaver
             checkpointer, and HITL/HOTL behaviour. Confirms the
             designed architecture is implemented correctly in the
             production entry point. The Decide step is where
             llama3.2:3b runs on every cycle.
Supports:    DL3, DL4
Tags to:     LO3, LO4

@model_comparison
Description: Side-by-side model comparison — llama3.2:3b vs
             gemma4:e4b across three runs each. Both models:
             valid response every run, correct supplier selected
             every run. Response times: 2.6 seconds vs 30.2
             seconds. The decision rationale below the table
             explains why identical accuracy made speed the
             deciding factor.
Supports:    DL4
Tags to:     LO4

@betsy_repository
Description: GitHub repository at github.com/maihere/Betsy
             containing the full working codebase — all six nodes,
             the graph wiring, the database layer, the dashboard,
             and the CLI entry point. The commit history shows
             the build happening in identifiable stages from initial
             setup through to the managing-phase additions.
             Confirms the system was actually built incrementally
             over time and is version-controlled.
Supports:    DL3, DL4, DL5
Tags to:     LO3, LO4, LO5

@dashboard_kpis
Description: Dashboard KPI overview showing 8 low-stock parts,
             16 orders awaiting delivery, G1 as the last gate
             fired, and 232 decisions logged. The "What Betsy Did
             Last Cycle" pipeline strip shows each of the 6 nodes
             with their status. Confirms the monitoring overview
             answers "is Betsy working?" in under 30 seconds.
Supports:    DL5
Tags to:     LO5

@decision_history
Description: Decision History page showing 234 audit log entries
             in the readable WHAT/WHY/NEXT format. The search and
             filter controls are visible. This is the tool that
             allowed all three managing-phase problems to be
             diagnosed from their output rather than from reading
             code — demonstrating the audit trail is functioning
             as a real diagnostic tool, not just a reporting feature.
Supports:    DL5
Tags to:     LO5

@orders_invoices
Description: Orders and Invoices dashboard page showing the PO
             table with delivery status filtering, the pending
             invoices section, and the Verify Now button. Confirms
             that the on-demand invoice verification fix is
             operational — a manager can check a suspicious invoice
             immediately without waiting for the next 4-hour cycle.
Supports:    DL5
Tags to:     LO5

@reliability_scoring
Description: Terminal output showing supplier reliability scoring
             in action: AccuParts Corp starting at 85.0, dropping
             to 82.0 after a delayed delivery (track_delivery_node,
             −3.0 rule), and recovering to 84.0 after a clean
             invoice match (verify_node, +2.0 rule). The code rules
             are printed alongside the results. Confirms scores
             now reflect actual delivery performance, not just
             seeded CSV values.
Supports:    DL5
Tags to:     LO5

@invoice_routing_change
Description: The _after_monitor routing function from the graph
             code shown in full with a before/after explanation.
             Before: verifying an invoice required a full ordering
             cycle. After: the graph skips directly to the
             verification step if an invoice is provided but no
             ordering work is needed. The Verify Now button on the
             dashboard is the user-facing result of this code change.
Supports:    DL5
Tags to:     LO5

@g3_fix_output
Description: Terminal output showing the G3 price spike fix
             working in both cases. ViennaMach GmbH with three
             recorded prices of €75 and a current price of €95:
             rolling average baseline €75, spike 26.7% — gate
             fires correctly. New supplier with no price history:
             baseline is None — G3 check skipped, no false alarm.
             The original bug (null treated as zero → infinite
             spike) is documented in the WHY section.
Supports:    DL6
Tags to:     LO5

@growth_reflection
Description: Separate document — Growth Reflection for LO7
             Personal Leadership. Covers how DL1 was approached,
             what assumption broke (that agent frameworks are
             interchangeable), how the approach changed by DL6
             (observing before deciding, not reasoning before
             testing), and a specific development area identified
             (test data that is too carefully prepared misses
             the edge cases that appear in real operation).
Supports:    All DLs
Tags to:     LO7

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEARNING OUTCOME COVERAGE
──────────────────────────

LO1 Analysing:    DL1 — Systematic comparison of three agent
                  frameworks on identical tasks, with objective
                  pass/fail criteria, produced data-backed evidence
                  that only one framework could do what the project
                  required.

LO2 Advising:     DL2 — A six-gate autonomy boundary design was
                  recommended to the procurement manager with a
                  defensible justification for every threshold,
                  confirmed by test output showing all six
                  conditions firing correctly from real data.

LO3 Designing:    DL3 — A six-node workflow architecture was
                  designed with explicit single responsibilities per
                  node, validated by a skeleton proof before
                  production code was written, and confirmed correct
                  in the live dashboard and production CLI.

LO4 Realising:    DL4 — The AI model was selected through a
                  controlled comparison run inside the actual
                  workflow under production conditions, resulting
                  in a working system with a versioned codebase
                  showing the build happened in stages.

LO5 Managing:     DL5 + DL6 — Three problems identified from
                  ongoing observation of the running system each
                  produced a documented code change; the audit log
                  functioned as a real diagnostic tool, not just
                  a reporting feature.

LO6 Professional: The DOT research framework (Library, Field, Lab,
                  Workshop, Showroom) is applied explicitly in every
                  decision log — section 5 of each DL names the
                  strategies used and explains why they fit that
                  stage. Ethical responsibility is built into the
                  gate design: no autonomous financial or compliance
                  decision proceeds without a human in the loop.
                  The scoring formula is fully transparent — every
                  weight is visible, every component is justified
                  by published research (Dickson 1966, Fishburn 1967).

LO7 Personal:     See @growth_reflection — linked separately in
                  PortFlow under LO7 Personal Leadership.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
