━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agile Sprint Overview — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PURPOSE OF THIS DOCUMENT
─────────────────────────
This document makes the iterative, sprint-based working
process visible. The Decision Logs (DL1–DL6) are the
detailed evidence. This overview shows how those decisions
connect across sprints, what feedback drove each iteration,
and where the DOT research methods appear. It exists to
answer the question: "Was this built iteratively, or was
it planned upfront and executed once?"

The answer is: iteratively. The sprint structure below
shows four cycles of plan → build/test → observe → revise.
Each cycle produced a decision log. Each decision log
changed what the next cycle started with.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SPRINT MAP
──────────

Sprint 1 — Analyse: Can this be built?
  Goal: Understand the problem and prove a framework can
        do what the project needs (genuine pause + resume).
  DL produced: DL1 (Framework Selection)
  DOT method: Library + Lab (DL1, section 5)
    Library — reviewed AutoGen, CrewAI, and LangGraph docs
              to understand what each framework claims
    Lab     — ran identical test scenarios on all three
              frameworks; only LangGraph passed
  Finding that drove the next sprint:
    AutoGen and CrewAI both failed the interrupt() test.
    LangGraph passed all three criteria. The Lab test made
    the choice certain rather than opinion-based.
  What changed going into Sprint 2:
    The framework was locked. All subsequent design work
    could assume LangGraph's state model and interrupt()
    behaviour without re-examining the choice.

─────────────────────────────────────────────────────────────

Sprint 2 — Advise + Design: What should it do and how?
  Goal: Define the approval gates and design the workflow
        that those gates live inside.
  DLs produced: DL2 (Gate Design), DL3 (Architecture)
  DOT methods:
    DL2: Library + Field (DL2, section 5)
      Library — researched tail-spend thresholds, invoice
                error rates, and automation boundary best
                practice in procurement literature
      Field   — evaluated gate conditions against Jenny's
                real working context: what she checks daily,
                what decisions she cannot delegate
    DL3: Workshop + Lab (DL3, section 5)
      Workshop — built a skeleton version of the 6-node
                 graph to explore what structure gave each
                 node one clear responsibility
      Lab      — ran the skeleton against real inventory.csv
                 data to confirm gates fired at correct points
  Finding that drove the next sprint:
    The skeleton proof (DL3) confirmed the 6-node architecture
    works: data flows correctly, gates fire, interrupt()
    pauses the graph at the right step. The design was stable
    enough to build the full system on top of.
  What changed going into Sprint 3:
    The architecture was locked. DL4 (model selection) sits
    inside the Decide node — it could not be decided until
    the node's role was defined in DL3.

─────────────────────────────────────────────────────────────

Sprint 3 — Realise: Build, test, find problems, fix them
  Goal: Implement the full system — all 6 nodes, all 6 gates,
        dashboard, CLI — and observe what breaks.
  DL produced: DL4 (Model Selection)
  DOT method: Lab + Showroom (DL4, section 5)
    Lab      — ran llama3.2:3b and gemma4:e4b against the
               same JSON selection task multiple times;
               measured accuracy and response time
    Showroom — validated the selection choice against the
               project's own criteria (speed + accuracy)
               and against what the academic literature says
               about local LLMs for structured output tasks
  Build findings recorded in Bug Log:
    Bug 1 — LLM returned prose instead of JSON
            Fix: explicit schema in prompt + format="json"
    Bug 2 — G3 gate (price spike) fired on null prices,
            treating missing data as a zero-price baseline
            Fix: null guard added; but full redesign deferred
                 to DL6 after monitoring revealed the pattern
    Bug 3 — G6 stale-data gate fired immediately on first
            run because initial data had no timestamp
            Fix: inventory.csv pre-seeded with timestamps
    Bug 4 — SQLite locked during concurrent dashboard + CLI
            Fix: WAL journal mode enabled in database.py
    Bug 5 — Checkpointer path conflict between MemorySaver
            and SqliteSaver
            Fix: two separate graph builders in graph.py
  Finding that drove the next sprint:
    The system ran end-to-end. But building it revealed
    problems that only appeared under real use — not in the
    skeleton design. The null-price G3 bug in particular
    was not a simple fix; it required a design change to
    how prices are tracked over time.
  What changed going into Sprint 4:
    The full system was running. The next question shifted
    from "does it work?" to "does it keep working correctly?"
    This required a dedicated monitoring and management phase.

─────────────────────────────────────────────────────────────

Sprint 4 — Manage: Observe, measure, and improve
  Goal: Define how to know the system is healthy over time,
        measure whether success criteria are being met, and
        act on what monitoring reveals.
  DLs produced: DL5 (Monitoring Design), DL6 (G3 Redesign)
  DOT methods:
    DL5: Lab + Field (DL5, section 5)
      Lab   — ran multiple monitoring cycles; read audit log,
              database, and notifications file after each run
              to understand what information was available
              and what was missing
      Field — evaluated that information against what Jenny
              needs: daily health check, auditability of any
              decision, evidence for her manager
    DL6: Lab + Field (DL6, section 5)
      Lab   — reproduced the false G3 trigger; traced the
              root cause to the null-price baseline;
              designed and tested the rolling average fix
      Field — validated the fix against Jenny's real need:
              G3 should only fire when a supplier's price
              has genuinely increased relative to what was
              paid historically

  ┌──────────────────────────────────────────────────────┐
  │ THE MANAGING & CONTROLLING LOOP (Sprint 4)           │
  │                                                      │
  │  Monitor runs →                                      │
  │    Audit log shows G3 firing incorrectly         ↓  │
  │  Investigate root cause →                            │
  │    Null price treated as zero baseline           ↓  │
  │  Design change →                                     │
  │    price_history table + rolling average (DL6)   ↓  │
  │  Re-test →                                           │
  │    G3 no longer fires on new suppliers           ↓  │
  │  Additional monitoring reveals two more gaps →       │
  │    Static reliability scores never update        ↓  │
  │    No way to verify invoice without full cycle   ↓  │
  │  Two more design changes →                           │
  │    Dynamic scoring in track/verify nodes         ↓  │
  │    Invoice-only routing + Verify Now button      ↓  │
  │  All three changes documented in DL5, section 7 ↓  │
  │  System improved. Monitoring continues.              │
  └──────────────────────────────────────────────────────┘

  This loop is not described as a final phase that comes
  after building. It is a cycle that runs while the system
  is in operation — observe, find a problem, diagnose,
  change the design, re-test, continue observing.

  Evidence that the loop ran:
    DL5, section 7 (WHAT WAS BUILT AS A RESULT OF MANAGING)
    DL6_G3_Price_Redesign.md
    Bug_Log.md — five build-phase problems, all diagnosed
                 and fixed with visible before/after changes
    Git commit history — managing-phase commits appear after
    implementation commits, not before; the order proves
    iteration happened in sequence, not as a plan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOT METHOD QUICK REFERENCE
────────────────────────────
Every Decision Log documents the DOT research method in
section 5 under "Research method." The table below is a
quick reference for the assessor.

DL   LO stage    DOT methods used    Where to find it
───  ──────────  ──────────────────  ─────────────────────
DL1  Analysing   Library + Lab       DL1, section 5
DL2  Advising    Library + Field     DL2, section 5
DL3  Designing   Workshop + Lab      DL3, section 5
DL4  Realising   Lab + Showroom      DL4, section 5
DL5  Managing    Lab + Field         DL5, section 5
DL6  Managing    Lab + Field         DL6, section 5

Each entry in section 5 explains:
  - Which DOT strategy was used
  - What was done as part of that strategy (specific actions)
  - What was found (evidence from that strategy)
  - How the finding informed the decision

The DOT methods were not applied retrospectively. The
research activities described in each DL section 5 — the
framework tests (Lab, DL1), the Jenny interviews (Field,
DL2), the skeleton build (Workshop, DL3) — are what
produced the evidence the decision is based on.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANAGING & CONTROLLING: SPRINT 5 — LANGSMITH INTEGRATION
──────────────────────────────────────────────────────────
Previous state (Sprint 4):
The monitoring infrastructure was the Streamlit dashboard,
the WHAT/WHY/NEXT audit log, and the notifications file.
These provided visibility into what Betsy decides and when,
but the monitoring was read manually — a human opens the
dashboard and reads the log.

Identified gap (Sprint 4):
For autonomous operation beyond a demonstration context,
the monitoring should be observable without requiring
manual dashboard checks. The current setup had no alerting
for anomalies (unexpected gate silence, scoring drift,
scheduler failure) unless the dashboard was open.

Sprint 5 — implemented:
LangSmith integration for LangGraph trace monitoring.
LangSmith captures every LangGraph node execution as a
structured trace — inputs, outputs, latency, errors — and
surfaces this in a web dashboard without requiring the
agent to write its own log.

What was built:
  - langsmith added to requirements.txt
  - LANGSMITH_TRACING, LANGSMITH_API_KEY, LANGSMITH_PROJECT
    added to .env (project: betsy-procurement)
  - load_dotenv() added to app.py and start_betsy.py so
    environment variables are loaded before LangGraph starts
  - @traceable(run_type="llm", name="supplier-selection-llm")
    added to the _invoke_llm helper in betsy/nodes.py —
    the LLM call inside Decide is now a named span in the
    LangSmith trace, separating it from the node wrapper
  - All 6 nodes wrapped in try/except — on any unhandled
    exception, the node writes an error-state WHAT/WHY/NEXT
    entry before halting, so the audit log always has an
    entry for every node that ran

What this provides:
  - Every procurement cycle produces a trace in LangSmith
    showing each of the 6 nodes with inputs, outputs, and
    latency — without requiring manual audit log reading
  - The LLM supplier-selection call is visible as a separate
    span with its prompt and raw response, making the AI
    decision transparent to any reviewer
  - Error conditions are now caught and logged rather than
    silently swallowed — the audit log has no gaps

Evidence: LangSmith project betsy-procurement showing
cycle traces with the 6-node sequence and the
supplier-selection-llm span nested inside the Decide node.

This completes the Managing & Controlling loop for Sprint 5:
gap identified (Sprint 4) → solution designed → implemented
and tested → traces confirmed in LangSmith dashboard.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANAGING & CONTROLLING: SPRINT 6 — GATE RELIABILITY FIXES
───────────────────────────────────────────────────────────
Previous state (Sprint 5):
LangSmith integration gave real-time trace visibility.
The dashboard was running. All six gates were wired and
the demo scenarios (G1–G5) were documented in the CLI
and the Streamlit interface.

Identified gap (Sprint 5 → Sprint 6):
Two problems emerged when checking whether the demo
scenarios could actually be triggered from the dashboard:

  Problem 1 — When Ollama was not running, clicking
  "Start Check" completed silently. No gates fired, no
  error appeared. The root cause: decide_node wrapped
  the LLM call AND the gate logic in a single try/except.
  An Ollama connection error triggered the outer handler,
  which returned "skip" before G1 or G3 could be checked.
  This made G1, G3, and G4 demos non-functional whenever
  the local model was unavailable.

  Problem 2 — The G3 demo (ViennaMach price spike) fired
  correctly on the first run after a database reset, but
  not on any subsequent run in the same session. The root
  cause: record_price_history() was called before
  get_price_average() inside decide_node. The current
  price was being included in its own baseline average —
  making spike_pct = 0% on every run after the first.

Sprint 6 — implemented:

  Fix 1: The LLM call in decide_node was moved into its
  own isolated try/except. If Ollama is unreachable, the
  node falls back to candidates[0] (the top-scored
  supplier from evaluate_node) with a logged fallback
  message. All gate checks — G1 and G3 — run on real
  prices and quantities from the database regardless of
  LLM availability. G1, G3, and G4 demos now work without
  Ollama running.

  Fix 2: record_price_history() was moved to after the
  G3 block so the rolling average only contains prices
  from previous cycles. Additionally, the G3 baseline
  priority was changed: last_price from the supplier
  record is now the primary baseline. The price_history
  average is used only when last_price is absent. This
  makes the G3 demo fire consistently across multiple
  runs, regardless of price_history state.

What was built:
  - betsy/nodes.py (decide_node): LLM call isolated in
    its own try/except; G3 baseline uses last_price first;
    record_price_history() moved to after G3 check.

Bugs documented: Bug_Log.md, Bug 6 and Bug 7.
DL updated: DL6 section 4 (Stage 2 note) and section 6
  Criterion 2 (last_price as primary baseline).

What this confirms:
  The managing loop is not a phase that ends. Sprint 6
  ran because using the system (opening the dashboard,
  running demos) revealed two more gaps — gaps that did
  not appear in the skeleton test or the initial build
  but only under real operating conditions. Observe →
  find problem → diagnose → fix → re-test. The loop
  continued, and the system is more reliable as a result.

DOT method: Lab + Field
  Lab   — ran each demo scenario (G1, G3, G4) from the
          dashboard with Ollama offline to reproduce the
          silent-skip failure; traced the exact line where
          the LLM exception was caught and gates were
          skipped; ran G3 demo repeatedly to observe the
          baseline contamination pattern.
  Field — evaluated against what a user would experience:
          clicking "Start Check" and seeing no result is
          indistinguishable from "agent found nothing to
          do" — a gate that silently fails is worse than
          a visible error because the user assumes the
          system is healthy when it is not.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHY THIS IS NOT WATERFALL
──────────────────────────
A waterfall project produces each phase once, in sequence,
with no feedback loops between phases:
  Requirements → Design → Build → Test → Deploy

Betsy was not built this way. The evidence:

1. Sprint 1 finding changed Sprint 2 scope.
   The Lab test in DL1 (all three frameworks tested) was not
   planned at the start of the project. The Library phase
   suggested LangGraph might work. The Lab test confirmed it
   and ruled out the other two. If AutoGen had passed, the
   gate design in DL2 would have been different.

2. Sprint 2 design was validated before full build.
   The skeleton proof in DL3 was not part of the original
   plan — it was added because building the full system on
   an untested architecture would have been risky. The
   Workshop + Lab sequence (design first, test the design,
   then build) is an iterative pattern, not a waterfall
   sequence.

3. Sprint 3 build produced findings that required Sprint 4
   design changes.
   The G3 null-price bug, the static reliability scores,
   and the missing on-demand invoice check were not known
   before building. They were found by running the system.
   Sprint 4 (DL5 + DL6) exists because Sprint 3 revealed
   problems that Sprint 3 could not fully solve.

4. Sprint 4 produced code changes, not just observations.
   Managing & Controlling is not a reporting phase at the
   end of the project. DL5 section 7 documents three
   concrete code changes that were made as a direct result
   of monitoring. DL6 documents a complete redesign of the
   G3 detection logic. The system after Sprint 4 is
   measurably different from the system at the end of
   Sprint 3 — three new database functions, two updated
   node behaviours, and new graph routing logic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
