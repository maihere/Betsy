━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PORTFOLIO COLLECTION
Betsy — Autonomous Procurement Agent
GenAI Semester — Professional Research Project
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


═══════════════════════════════════════════════════════════════
COLLECTION DESCRIPTION
═══════════════════════════════════════════════════════════════

THE PROBLEM
───────────

A manufacturing business had one procurement manager — Jenny —
spending over 30 hours a week on tasks that followed consistent,
rule-bound patterns: checking which parts were running low,
comparing supplier prices and reliability scores, placing purchase
orders, following up on late deliveries, and verifying that
incoming invoices matched what was ordered.

None of these tasks required specialist judgment. But each one
still needed a human to do it, because no existing tool could
distinguish routine from exceptional. A system that could
autonomously handle the routine — and genuinely pause and wait
for a human when something looked wrong — would free Jenny to
focus on the exceptions that actually needed her.

That is what Betsy is: an autonomous procurement agent that
handles routine purchasing decisions on its own, and freezes
mid-workflow when a defined risk condition is triggered — not
just flagging a problem, but stopping completely until a human
approves or rejects before anything further happens.

The project ran across three sprints. Each sprint produced one
or two Decision Logs, a set of evidence artifacts, and a
demonstrated capability. Together they trace the full journey
from a research question to a monitored, improving system
running in production.

GitHub repository (full codebase, all six nodes, commit history
showing each sprint's additions):
@betsy_repository → LO3 Designing, LO4 Realising, LO5 Managing


───────────────────────────────────────────────────────────────
SPRINT 1 — Research and Decision: What should Betsy be built on,
           and where must it stop and ask a human?
           LO1 Analysing · LO2 Advising
───────────────────────────────────────────────────────────────

The first question Sprint 1 had to answer was not "how do we
build Betsy?" — it was "can we build Betsy at all with the tools
available?"

Three agent frameworks were available: LangGraph, AutoGen, and
CrewAI. All three claimed to support autonomous agents. The
project required one specific capability that the documentation
did not address directly: the ability to genuinely pause
mid-workflow and wait for a human response before continuing.
Not flag a problem and carry on. Not skip to the next step.
Stop completely, preserve state, and resume from exactly the
same position after a decision was received.

Rather than choosing a framework based on documentation or
popularity, a controlled test was designed: all three frameworks
were given the exact same procurement task and evaluated against
four objective criteria. The result was not a matter of degree —
two of the three frameworks failed on the most critical
criterion entirely. AutoGen and CrewAI do not have a pause
mechanism. They are architecturally built for a different
pattern: reason to a conclusion, return an answer. Betsy needed
something different, and only LangGraph could provide it.

@framework_comparison shows the pass/fail table across all four
criteria for all three frameworks — the complete evidence for
DL1 and LO1 Analysing. @langgraph_gate shows LangGraph doing
what the others could not: pausing at the gate, waiting, and
resuming from the same position after approval. @autogen_failure
and @crewai_failure show both AutoGen and CrewAI running
straight through the gate to completion — no pause, no wait.

With the framework confirmed, Sprint 1's second question was
harder: where exactly should autonomy end? Every way an
autonomous procurement agent could cause financial or compliance
harm had to be mapped and a gate designed for each one. This
was not a technical question — it was a recommendation to Jenny,
requiring a defensible justification for every threshold.

Research into tail-spend practice, invoice fraud prevention, and
price escalation policy produced the boundaries: €300 as the
routine-order ceiling, 15% as the price spike threshold, zero
tolerance on any invoice discrepancy, and 4 hours as the
stale-data cutoff. Each gate was then given a classification:
HITL (the workflow genuinely freezes) or HOTL (Betsy halts
ordering and notifies, but no approval gate is needed). All six
gates were tested against real supplier and invoice data to
confirm they fired on the right conditions and did not fire on
the wrong ones.

@gate_test_g1_g2_g3 shows gates G1, G2, and G3 firing from real
data with their reasoning entries. @gate_test_g4_g5_g6 shows
G4, G5, and G6 doing the same. @gate_reasoning_log shows a
single gate entry in full — the exact data the gate acted on,
the rule it applied, the action taken — demonstrating that every
gate decision is recorded in plain language at the moment it
fires. This is the evidence for DL2 and LO2 Advising: a
structured recommendation with tested, data-backed thresholds.

Sprint 1 produced two confirmed decisions — framework and gate
design — and a tested, documented justification for each one
before a single line of production code was written.

Decision Logs from this sprint:
  DL1 → LO1 Analysing
  DL2 → LO2 Advising

Evidence from Sprint 1:
  @framework_comparison   @langgraph_gate
  @autogen_failure        @crewai_failure
  @gate_test_g1_g2_g3     @gate_test_g4_g5_g6
  @gate_reasoning_log


───────────────────────────────────────────────────────────────
SPRINT 2 — Design and Build: How should the workflow be
           structured, and which AI model should run inside it?
           LO3 Designing · LO4 Realising
───────────────────────────────────────────────────────────────

Sprint 2 had a framework and six gates. What it did not have yet
was a structure: how many steps, what each step does, how data
flows between them, and what the system's reasoning looks like
after a run.

The architecture decision came first, before any production code
was written. A skeleton version of the workflow was designed
in a Workshop phase — different node arrangements were tried
until every node could be described in one sentence without
using the word "and." The result was a six-node sequential
graph: Monitor → Evaluate → Decide → Order → Track → Verify.
Each node maps to one phase of the procurement process Jenny
was doing manually. A single shared state dictionary carries
all data between nodes, so nothing is lost between steps. Every
node writes a WHAT/WHY/NEXT entry to an append-only audit log,
so any past decision can be explained in plain language after
the fact.

One design choice required particular care: the supplier scoring
formula. The SAW (Simple Additive Weighting) formula — from
Fishburn (1967) and Dickson's (1966) supplier selection
research — calculates a weighted score from reliability (40%),
price (35%), and delivery speed (25%). This formula runs in
pure Python. The LLM does not calculate it. The LLM receives the
pre-calculated scores and is asked to confirm the selection and
write a two-sentence explanation. Financial decisions must be
deterministic; LLMs are probabilistic. The right tool for each
job.

The skeleton was tested against real inventory data before
production code was written. @graph_run_output shows the full
proof: all six nodes running in sequence, a gate firing,
interrupt() pausing the workflow, the approval received, the
graph resuming, and the reasoning log saved to the database.
The design was confirmed before the build began.

@saw_scoring_dashboard shows the SAW formula working live in the
dashboard — every supplier's score components visible alongside
the final weighted score. @stock_levels_dashboard shows the
Monitor node identifying low-stock parts against their reorder
thresholds in the live system. @production_cli confirms the
full Monitor→Evaluate→Decide→Order→Verify pipeline operational
in the production entry point, with SqliteSaver checkpointer
and both HITL and HOTL mechanisms confirmed. These are the
artifacts for DL3 and LO3 Designing.

With the architecture locked, Sprint 2's second decision was
model selection. The Decide node needed an AI model for one
specific task: read a pre-scored supplier list and return the
selected supplier as valid JSON with a plain-language
explanation. Two local models were available via Ollama:
llama3.2:3b and gemma4:e4b.

Both were given the same task three times each. Both returned
valid JSON every run. Both selected the correct supplier every
run. The only measurable difference was speed: 2.6 seconds
versus 30.2 seconds average. @model_comparison shows the
side-by-side results. A model that takes eleven times longer
to return the same quality output on a simple structured task
is not a better model for that task — it is just slower.
llama3.2:3b was selected.

@production_cli confirms the selected model is integrated into
the operational pipeline — not just a comparison script result.
@betsy_repository shows the full working codebase built from
these decisions, with the commit history showing the build
happening in identifiable stages from initial setup through to
the Sprint 2 completion. These are the artifacts for DL4 and
LO4 Realising.

Sprint 2 ended with a complete, working system: six nodes,
six gates, a live dashboard, persistent state, a local AI model
confirmed in production, and a full audit trail of every
autonomous decision.

Decision Logs from this sprint:
  DL3 → LO3 Designing
  DL4 → LO4 Realising

Evidence from Sprint 2:
  @graph_run_output       @saw_scoring_dashboard
  @stock_levels_dashboard @production_cli
  @model_comparison       @betsy_repository


───────────────────────────────────────────────────────────────
SPRINT 3 — Manage and Improve: How do we know it is working —
           and what do we do when it is not?
           LO5 Managing
───────────────────────────────────────────────────────────────

A working build is not a finished system. A system that makes
autonomous financial decisions on a 4-hour schedule needs to be
observed, not just trusted. Sprint 3 began by treating the
running Betsy as something to investigate — running it across
multiple cycles, reading what the audit log produced, and asking
the question that testing alone cannot answer: does it behave
correctly with data conditions that the test scenarios never
covered?

The answer was: not always.

Three problems were identified from observation, not from code
review.

The first problem: G3, the price spike gate, was firing on new
suppliers who had never had an order placed with them. The
system was treating a missing previous price as zero and
calculating any new price as an infinite percentage increase.
The audit log showed exactly what data the gate had used — and
tracing it back revealed a null-value assumption that had never
been explicitly made, only implied. The fix: a price_history
table was added to store prices per supplier per cycle, and G3
now uses a rolling average as its baseline. New suppliers with
no history are skipped rather than triggering a false alarm.
@g3_fix_output shows both cases working correctly after the fix.

The second problem: supplier reliability scores never changed.
The SAW formula used the initial CSV values regardless of
delivery history. A supplier who was consistently late and a
supplier who was consistently on time had identical reliability
scores after any number of cycles. The fix: track_delivery_node
now applies a −3 point penalty when a PO is marked delayed, and
verify_node applies a +2 point bonus when an invoice matches
cleanly. @reliability_scoring shows the fix in action —
AccuParts Corp dropping from 85 to 82 after a delayed delivery,
then recovering to 84 after a clean invoice match.

The third problem: verifying a suspicious invoice required
running a full 4-hour procurement cycle. There was no way to
check a specific invoice on demand. The fix: the graph routing
was updated so that a state with an invoice but no low-stock
items skips directly to the verification step. A "Verify Now"
button was added to the Orders page. @invoice_routing_change
shows the routing code before and after, with the plain-language
explanation of what changed and why. @orders_invoices shows the
button operational in the live dashboard.

All three problems were identified because the monitoring
infrastructure worked. @dashboard_kpis shows the monitoring
overview — 8 low-stock parts, 16 orders awaiting delivery, last
gate fired, and 232 decisions logged — the four numbers that
answer "is Betsy working?" in under 30 seconds. @decision_history
shows 234 audit log entries in the readable WHAT/WHY/NEXT format
that made all three problems diagnosable from their output
rather than from code inspection.

Sprint 3 demonstrated what managing an autonomous agent actually
means: not just building monitoring tools, but using them to
identify real problems and producing documented code changes
that improve the system's behaviour. DL5 covers the monitoring
design and the three fixes. DL6 covers the G3 price redesign
in full.

Decision Logs from this sprint:
  DL5 → LO5 Managing
  DL6 → LO5 Managing (continued)

Evidence from Sprint 3:
  @dashboard_kpis         @decision_history
  @orders_invoices        @reliability_scoring
  @invoice_routing_change @g3_fix_output


───────────────────────────────────────────────────────────────
ACROSS ALL SPRINTS — Professional Conduct and Personal Growth
                     LO6 Professional · LO7 Personal Leadership
───────────────────────────────────────────────────────────────

Every Decision Log follows the same DOT research framework
structure. Section 5 of each DL names the research strategy
used (Library, Field, Lab, Workshop, or Showroom) and explains
why that strategy was appropriate for that stage. No decision
was made from reasoning alone — every threshold, every design
choice, every model selection was confirmed by a test, a
demonstration, or an observed outcome. This is the LO6
Professional evidence: consistent, named methodology applied
across all five LO stages.

The ethical design of the system is itself a professional
decision. Every HITL gate ensures that no autonomous financial
or compliance decision proceeds without a human in the loop.
The scoring formula is fully transparent — every weight is
visible, every component is justified by published research.
The audit trail means every decision can be explained after the
fact by anyone, including someone who did not build the system.

The growth from Sprint 1 to Sprint 3 is documented in
@growth_reflection. The core shift: in Sprint 1, the assumption
was that agent frameworks were broadly interchangeable and the
choice would be a matter of convenience. The controlled test
broke that assumption entirely. By Sprint 3, no assumption
about how the system behaved was made without first observing
what it actually did. The G3 bug was found not by reviewing
code but by reading an audit log entry and tracing the problem
back from the observed behaviour. The shift from reasoning
first to observing first is the most significant development
across this project.


═══════════════════════════════════════════════════════════════
EVIDENCE INDEX
═══════════════════════════════════════════════════════════════

Each evidence item below has an @name for direct platform
linking, a description of what it shows and why it counts as
evidence, the Decision Log it supports, and the Learning
Outcome it demonstrates.

─────────────────────────────
SPRINT 1 EVIDENCE
─────────────────────────────

@framework_comparison
Description: Pass/fail criteria table — three agent frameworks
             (LangGraph, AutoGen, CrewAI) tested on the same
             procurement task against four criteria: runs without
             a trigger, genuinely pauses at a gate, per-step
             reasoning log, and state preserved across restarts.
             LangGraph passes all four. AutoGen and CrewAI both
             fail on the two most critical criteria. The "What
             This Means for Betsy" explanation below the table
             shows why the failure is architectural, not
             configurable.
Supports:    DL1
Tags to:     LO1 Analysing

@langgraph_gate
Description: LangGraph mid-run terminal output showing interrupt()
             executing at the approval gate, the gate details and
             order total displayed, the workflow frozen — and then
             resuming from the same position after the approval
             was sent. Confirms C2 (genuine pause) and C3
             (per-step reasoning log) both satisfied.
Supports:    DL1
Tags to:     LO1 Analysing

@autogen_failure
Description: AutoGen running the same procurement task to
             completion without pausing at the approval gate.
             The gate condition was met but the workflow
             continued to the end. No per-step reasoning log
             produced. Confirms C2 and C3 both failed.
Supports:    DL1
Tags to:     LO1 Analysing

@crewai_failure
Description: CrewAI running the same task to completion with
             the same failure pattern as AutoGen — no pause, no
             reasoning log. Confirms the failure is not specific
             to one framework but is a shared architectural
             limitation of both alternatives.
Supports:    DL1
Tags to:     LO1 Analysing

@gate_test_g1_g2_g3
Description: Terminal output showing gates G1 (order value
             €9,880 exceeds the €300 threshold), G2 (unapproved
             supplier FastParts GmbH blocked), and G3 (ViennaMach
             price spike +26.7%) each firing from real supplier
             and order data. WHAT/WHY/NEXT reasoning entries
             visible for each. No-fire cases included confirming
             gates do not trigger when conditions are not met.
Supports:    DL2
Tags to:     LO2 Advising

@gate_test_g4_g5_g6
Description: Terminal output showing gates G4 (invoice €6,200
             vs PO €5,775 — mismatch of €425), G5 (duplicate
             invoice INV-2025-006 matches INV-2025-001), and G6
             (inventory data 8,959 hours old — stale) each firing
             from real data. WHAT/WHY/NEXT entries and no-fire
             cases for all three.
Supports:    DL2
Tags to:     LO2 Advising

@gate_reasoning_log
Description: A single complete gate reasoning entry shown in
             full — G5 duplicate invoice — with the exact data
             values the gate acted on, the DL2 rule it applied
             (zero tolerance on duplicate invoices), and the
             action taken (payment held, workflow paused).
             Demonstrates the plain-language audit trail that
             makes every gate decision explainable after the fact.
Supports:    DL2
Tags to:     LO2 Advising, LO6 Professional

─────────────────────────────
SPRINT 2 EVIDENCE
─────────────────────────────

@graph_run_output
Description: Full skeleton proof terminal output — all six nodes
             running in sequence, WHAT/WHY/NEXT reasoning entries
             from each node visible, G6 stale-data gate firing
             (6.8 hours old), interrupt() pausing the graph, the
             human approval received, graph resuming, and the
             reasoning log saved to betsy.db. Confirms the
             designed 6-node architecture works end-to-end before
             production code was written.
Supports:    DL3
Tags to:     LO3 Designing

@saw_scoring_dashboard
Description: Suppliers dashboard page showing all approved
             suppliers with their reliability, price, and delivery
             values and the final SAW score for each. Score
             breakdown table below confirms the three weighted
             components (reliability 40%, price 35%, delivery 25%)
             are applied correctly. The formula is transparent —
             every weight and every component is visible in the
             dashboard.
Supports:    DL3
Tags to:     LO3 Designing, LO6 Professional

@stock_levels_dashboard
Description: Stock Levels dashboard page showing 8 low-stock
             parts highlighted in red against their reorder
             thresholds, with the Stock vs Threshold bar chart
             for all 20 parts. This is the live output of the
             Monitor node — confirms the first node in the
             workflow is correctly identifying which parts need
             ordering from real inventory data.
Supports:    DL3
Tags to:     LO3 Designing

@production_cli
Description: CLI startup output confirming the full
             Monitor→Evaluate→Decide→Order→Verify pipeline is
             operational in the production entry point. Shows
             the four run modes, build_persistent_graph() with
             SqliteSaver checkpointer for state persistence, and
             HITL/HOTL behaviour. The Decide step is where
             llama3.2:3b runs on every cycle. This is the
             Showroom evidence that the designed architecture was
             implemented correctly end-to-end.
Supports:    DL3, DL4
Tags to:     LO3 Designing, LO4 Realising

@model_comparison
Description: Side-by-side model comparison — llama3.2:3b vs
             gemma4:e4b across three runs each. Results: both
             models returned valid JSON every run, both selected
             the correct supplier every run (identical accuracy).
             Average response time: 2.6 seconds vs 30.2 seconds.
             The decision rationale explains why identical
             accuracy made speed the deciding factor — the task
             is structured and constrained, not a deep reasoning
             problem.
Supports:    DL4
Tags to:     LO4 Realising

@betsy_repository
Description: GitHub repository at github.com/maihere/Betsy —
             the full working codebase including all six nodes,
             graph wiring, database layer, Streamlit dashboard,
             CLI entry point, and evidence scripts. The commit
             history shows the build happening in stages: Sprint 1
             research scripts, Sprint 2 implementation, Sprint 3
             managing-phase additions. Confirms the system was
             built incrementally over time and is version-controlled.
Supports:    DL3, DL4, DL5
Tags to:     LO3 Designing, LO4 Realising, LO5 Managing

─────────────────────────────
SPRINT 3 EVIDENCE
─────────────────────────────

@dashboard_kpis
Description: Dashboard KPI overview — 8 low-stock parts, 16
             orders awaiting delivery, G1 as the last gate fired,
             232 decisions logged, and the "What Betsy Did Last
             Cycle" pipeline strip showing all 6 node statuses.
             This is the monitoring overview that answers "is
             Betsy working?" in under 30 seconds — the primary
             tool for Sprint 3 observation.
Supports:    DL5
Tags to:     LO5 Managing

@decision_history
Description: Decision History page showing 234 audit log entries
             in the WHAT/WHY/NEXT format with search and filter
             controls visible. This is the tool that made all
             three Sprint 3 problems diagnosable from output
             rather than from code inspection — demonstrating
             the audit trail functions as a real diagnostic tool,
             not just a reporting feature.
Supports:    DL5
Tags to:     LO5 Managing

@orders_invoices
Description: Orders and Invoices dashboard page — PO table with
             delivery status filtering, pending invoices section,
             and the Verify Now button. Confirms that the
             on-demand invoice verification fix is operational:
             a manager can check a suspicious invoice immediately
             without waiting for the next 4-hour procurement cycle.
Supports:    DL5
Tags to:     LO5 Managing

@reliability_scoring
Description: Terminal output demonstrating dynamic reliability
             scoring in action: AccuParts Corp at 85.0, dropping
             to 82.0 after a delayed delivery (track_delivery_node,
             −3.0 rule), recovering to 84.0 after a clean invoice
             match (verify_node, +2.0 rule). The code rules are
             printed alongside the results. Confirms supplier
             scores now reflect actual delivery performance over
             time, not just the initial CSV values.
Supports:    DL5
Tags to:     LO5 Managing

@invoice_routing_change
Description: The _after_monitor routing function shown in full
             before and after the fix, with a plain-language
             explanation of what changed and why. Before: invoice
             verification required a full ordering cycle. After:
             the graph skips directly to verification when an
             invoice is provided but no ordering work is needed.
             Shows how a managing-phase observation produced a
             specific, documented code change.
Supports:    DL5
Tags to:     LO5 Managing

@g3_fix_output
Description: Terminal output showing the G3 price spike fix
             working in both cases that mattered. ViennaMach GmbH
             with three recorded prices of €75 and a current
             price of €95: rolling average €75, spike 26.7%,
             gate fires correctly. New supplier with no price
             history: baseline is None, G3 check skipped, no
             false alarm. Documents the original bug (null treated
             as zero → infinite percentage increase) and confirms
             both the fix and the edge case it handled.
Supports:    DL6
Tags to:     LO5 Managing

─────────────────────────────
ACROSS ALL SPRINTS
─────────────────────────────

@growth_reflection
Description: Growth Reflection for LO7 Personal Leadership —
             how DL1 was approached (assumption: frameworks are
             interchangeable), what broke that assumption (the
             controlled test showing an architectural difference,
             not a degree of convenience), how the approach changed
             by DL6 (observe first, decide second), and the
             specific development area identified (test data that
             is too carefully prepared misses the edge cases that
             appear in real operation).
Supports:    All sprints
Tags to:     LO7 Personal Leadership


═══════════════════════════════════════════════════════════════
LEARNING OUTCOME COVERAGE
═══════════════════════════════════════════════════════════════

LO1 Analysing        Sprint 1 · DL1
  Three frameworks tested against four objective criteria on
  identical tasks. Data-backed evidence that only one framework
  had the architectural capability the project required.
  Evidence: @framework_comparison  @langgraph_gate
            @autogen_failure  @crewai_failure

LO2 Advising         Sprint 1 · DL2
  Six-gate autonomy boundary design recommended to a named
  stakeholder with a defensible threshold for every gate,
  confirmed by test output showing all six conditions firing
  from real data.
  Evidence: @gate_test_g1_g2_g3  @gate_test_g4_g5_g6
            @gate_reasoning_log

LO3 Designing        Sprint 2 · DL3
  Six-node workflow architecture validated by a skeleton proof
  before production code was written, confirmed working again
  in the live dashboard and production CLI.
  Evidence: @graph_run_output  @saw_scoring_dashboard
            @stock_levels_dashboard  @production_cli
            @betsy_repository

LO4 Realising        Sprint 2 · DL4
  AI model selected through a controlled comparison inside the
  actual workflow under production conditions. Result: a working
  versioned codebase showing the build happened in stages.
  Evidence: @model_comparison  @production_cli
            @betsy_repository

LO5 Managing         Sprint 3 · DL5 + DL6
  Three problems identified from ongoing observation of the
  running system. Each produced a documented code change that
  improved behaviour. Audit log used as a real diagnostic tool.
  Evidence: @dashboard_kpis  @decision_history
            @orders_invoices  @reliability_scoring
            @invoice_routing_change  @g3_fix_output
            @betsy_repository

LO6 Professional     All sprints · All DLs
  DOT research methodology (Library, Field, Lab, Workshop,
  Showroom) applied and named explicitly in every Decision Log
  section 5. Ethical oversight designed into the gate system —
  no autonomous financial decision proceeds without a human.
  Scoring formula fully transparent with published justifications.
  Evidence: @gate_reasoning_log  @saw_scoring_dashboard
            (supported by section 5 of each DL)

LO7 Personal         Across all sprints
  Documented growth from "frameworks are interchangeable" (DL1
  assumption) to "observe before deciding" (DL6 practice).
  Specific strength and development area identified with
  concrete examples from the project.
  Evidence: @growth_reflection

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
