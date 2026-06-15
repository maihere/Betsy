━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Portfolio Collection — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1 — COLLECTION NARRATIVE
──────────────────────────────────

What was built and why:

Betsy is an autonomous procurement agent built for a small
manufacturing company where a single person (Jenny) handles
all purchasing manually. The problem: Jenny checks 20 parts
daily, scores suppliers, sends purchase orders, and verifies
invoices — all done by hand, all subject to human error, all
creating a bottleneck when she is unavailable. The project
question was whether this work could be delegated to an
autonomous agent that acts on routine decisions without human
involvement, while still pausing for Jenny on decisions that
carry financial or compliance risk.

The system that was built — Betsy — monitors inventory on a
4-hour cycle, scores approved suppliers using a weighted
formula, selects the best supplier for each low-stock part,
places purchase orders, tracks deliveries, and verifies
invoices against purchase order records. Six gates (G1–G6)
define the boundary between what Betsy handles alone and what
requires Jenny's explicit approval before the workflow
continues. The full business analysis and stakeholder context
is documented in: Documents/00_Business_Analysis.md.
The competitive landscape and technology context is documented
in: Documents/Research_Landscape_Comparison.md.

Sprint progression — how this was built iteratively:

The project was built across five sprints. Each sprint
produced a decision log and changed what the next sprint
started with. This is not a retrospective description of the
work as iterative — the git commit history, the bug log, and
the decision log dates show the sequence.

Sprint 1 (Analysing): The first question was whether any
framework could genuinely pause a workflow mid-execution and
wait for a human response — not simulate it, but freeze
completely. Three frameworks were tested on identical
scenarios (LangGraph, AutoGen, CrewAI). Only LangGraph passed.
This eliminated two options and locked the foundation.
Decision log: DL1_Framework_Selection.md.

Sprint 2 (Advising + Designing): With the framework confirmed,
the gate conditions were designed — where the boundary between
autonomous action and human approval sits, and why those
thresholds are defensible rather than arbitrary. The
architecture was designed next: six nodes, each with one
responsibility, with a skeleton proof run against real
inventory data before the full system was built.
Decision logs: DL2_Gate_Design.md, DL3_Architecture.md.

Sprint 3 (Realising): The full system was built — all six
nodes, all six gates, the Streamlit dashboard, and the CLI.
Building it revealed five problems that did not appear in the
skeleton. All five are documented in Bug_Log.md with the root
cause and fix for each. The model selection (DL4) was resolved
during this sprint — llama3.2:3b was chosen over gemma4:e4b
after a direct comparison test (identical accuracy, 8.6×
faster). Decision log: DL4_Model_Selection.md.

Sprint 4 (Managing): With the system running, the question
shifted to: how do you know it is working correctly over time?
Three monitoring mechanisms were designed and measured against
what Jenny actually needs (DL5). Running the system under
monitoring revealed three problems: G3 false alarms on new
suppliers, reliability scores that never updated, and no way
to verify a suspicious invoice without running a full cycle.
All three produced code changes (DL5, section 7). The G3
problem was significant enough to warrant its own decision
log: DL6_G3_Price_Redesign.md.

Sprint 5 (Managing continues): Monitoring also revealed that
observability relied on manually reading the dashboard. A gap
for autonomous operation beyond a demonstration context.
LangSmith was integrated to capture every LangGraph node
execution as a structured trace — inputs, outputs, latency —
visible in the LangSmith web dashboard without opening the
Streamlit interface. The autonomous approval rate was added
as a fifth KPI tile on the dashboard, calculated live from
the audit_log table. Documented in: Agile_Sprint_Overview.md
(Sprint 5 section) and DL5, DL6 (section 7).

Managing & Controlling loop:

The teacher feedback (Week 16) identified that Managing &
Controlling was not explicit at portfolio level. The work was
always there — DL5 and DL6 document four code changes that
resulted directly from monitoring. The loop that drove those
changes is:

  Monitor (audit log, dashboard, notifications)
    → Find problem (G3 false alarm from null price)
    → Diagnose (Lab: traced values in audit log)
    → Design change (price_history table, rolling average)
    → Re-test (G3 fires on genuine spike, skips for new supplier)
    → Continue monitoring (two more gaps found, two more fixes)
    → Sprint 5: LangSmith added for real-time traceability

The full loop is visualised in: Agile_Sprint_Overview.md
(THE MANAGING & CONTROLLING LOOP diagram).
The outputs of the loop are documented in: DL5, section 7
(WHAT WAS BUILT AS A RESULT OF MANAGING) — four concrete
code changes, each with the observation that triggered it,
the files changed, and the evidence that it worked.

Growth and personal leadership:

The Growth_Reflection_LO7.md document traces how the approach
to decision-making changed across the six decision logs. In
DL1, the assumption was that agent frameworks were broadly
comparable and a reading-based judgment would be sufficient.
The comparison test broke that assumption: two of three
frameworks could not do the most important thing the project
required, regardless of configuration. By DL6, the pattern
had reversed — no design decision was made without first
observing what the system actually did. The shift from
"reasoning about what should work" to "observing what
actually happens" is the thread that connects DL1 to DL6
and is the most direct evidence of professional growth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 2 — DECISION LOG SUMMARIES
────────────────────────────────────

DL1 — Framework Selection
  Research question: Which AI workflow framework can genuinely
    pause mid-process and wait for a human decision?
  Decision: LangGraph — only framework that passed all 4
    criteria (interrupt(), SqliteSaver, shared log, scheduler).
  Key finding: AutoGen and CrewAI cannot pause mid-workflow.
    This is architectural, not a configuration issue.
  DOT method: Library + Lab
  Evidence: agents/run_all.py comparison output;
    image evidence/criteria_table.png;
    image evidence/LangGraph gate.png
  File: Documents/DL1_Framework_Selection.md

DL2 — Gate Design
  Research question: Where is the right boundary between
    autonomous action and human approval — and what
    thresholds make that boundary defensible?
  Decision: Six gates (G1–G6) with explicit thresholds:
    €300 spend (G1), no supplier (G2), 15% price spike (G3),
    invoice mismatch (G4), duplicate invoice (G5),
    4h stale data (G6).
  Key finding: €300 aligns with tail-spend literature.
    95% autonomous rate is achievable against real CSV data.
  DOT method: Library + Field
  Evidence: test_gates.py output;
    image evidence/test_gate(1).png;
    image evidence/test_gate(2).png;
    image evidence/threshold.png
  File: Documents/DL2_Gate_Design.md

DL3 — Architecture
  Research question: How should the workflow be structured so
    each step has one clear responsibility and the reasoning
    log is readable by a non-technical manager?
  Decision: Six-node linear graph (Monitor→Evaluate→Decide→
    Order→Track→Verify), BetsyState TypedDict, SAW scoring
    formula (reliability×0.40, price×0.35, delivery×0.25).
  Key finding: Skeleton proof confirmed architecture before
    full build. WHAT/WHY/NEXT log readable without code.
  DOT method: Workshop + Lab
  Evidence: run_dl3.py --design output;
    image evidence/full 6-node output.png;
    image evidence/SAW scoring table.png;
    image evidence/reasoning log entry.png;
    image evidence/start_betsy_architecture.png
  File: Documents/DL3_Architecture.md

DL4 — Model Selection
  Research question: Which local LLM produces reliable JSON
    output for supplier selection consistently and quickly?
  Decision: llama3.2:3b — identical accuracy to gemma4:e4b,
    8.6× faster (4.0s vs 34.3s average).
  Key finding: Both models selected correctly. Speed was the
    differentiator — gemma4:e4b was unusable in demos.
  DOT method: Lab + Showroom
  Evidence: test_model_choice.py output;
    image evidence/model chose.png
  File: Documents/DL4_Model_Selection.md

DL5 — Managing & Monitoring
  Research question: How do we know Betsy is making good
    decisions over time — and what do we observe, measure,
    and act on to keep it aligned with its design?
  Decision: Three monitoring mechanisms (dashboard, audit log,
    notifications file) plus four code changes that resulted
    from what monitoring revealed: G3 rolling average fix,
    dynamic reliability scoring, invoice-only routing,
    LangSmith trace integration.
  Key finding: Monitoring is only valuable if it produces
    action. DL5 section 7 documents all four code changes
    triggered by monitoring.
  DOT method: Lab + Field
  Evidence: image evidence/Dashboard.png;
    image evidence/audit log.png;
    image evidence/Orders & Invoices.png;
    image evidence/reliable score update.png;
    image evidence/have verify invoice.png;
    LangSmith project betsy-procurement (traces)
  File: Documents/DL5_Managing_Monitoring.md

DL6 — G3 Price Spike Redesign
  Research question: Why is G3 firing on orders where the
    price has not changed — and how to make spike detection
    reliable for suppliers with no price history?
  Decision: Replace single last_price comparison with a
    rolling average of the last three recorded prices from
    a new price_history table. Skip the check entirely if
    no history exists.
  Key finding: The bug was a silent null assumption — NULL
    treated as 0, making any price an infinite percentage
    increase. The audit log revealed this without rerunning
    the code.
  DOT method: Lab + Field + Showroom
  Evidence: image evidence/update price for new supplier.png;
    betsy/database.py (record_price_history, get_price_average);
    betsy/nodes.py (updated G3 check in decide_node);
    Bug_Log.md (Bug 2);
    LangSmith trace showing G3 skip/fire path
  File: Documents/DL6_G3_Price_Redesign.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 3 — EVIDENCE INDEX
────────────────────────────

DOCUMENTS
─────────
00_Business_Analysis.md
  What it shows: Stakeholder context (Jenny), problem definition,
    business case for autonomous procurement agent.
  Links to: DL1–DL6 (project foundation), LO1

Research_Landscape_Comparison.md
  What it shows: Academic and industry context for autonomous
    agents in procurement; positions Betsy in the field.
  Links to: DL1 (Library phase), DL2 (tail-spend literature), LO1

DL1_Framework_Selection.md
  What it shows: Three-framework comparison test with criteria,
    results, and reasoning. LangGraph chosen.
  Links to: LO1 (Analysing)

DL2_Gate_Design.md
  What it shows: Gate conditions G1–G6, threshold justifications,
    HITL/HOTL classification, 95% autonomous rate target.
  Links to: LO2 (Advising)

DL3_Architecture.md
  What it shows: 6-node graph design, BetsyState schema, SAW
    scoring formula, skeleton proof evidence.
  Links to: LO3 (Designing)

DL4_Model_Selection.md
  What it shows: LLM comparison test (llama3.2:3b vs gemma4:e4b),
    accuracy + speed measurements, selection rationale.
  Links to: LO4 (Realising)

DL5_Managing_Monitoring.md
  What it shows: Monitoring design decision, three monitoring
    mechanisms, four code changes from observation, LangSmith
    integration, approval rate KPI.
  Links to: LO5 (Managing)

DL6_G3_Price_Redesign.md
  What it shows: G3 false alarm bug, root cause diagnosis via
    audit log, rolling average redesign, LangSmith confirmation.
  Links to: LO5 (Managing)

Agile_Sprint_Overview.md
  What it shows: Sprint map (5 sprints), DOT method quick
    reference, Managing & Controlling loop diagram, Sprint 5
    LangSmith implementation, why this is not waterfall.
  Links to: LO1–LO5 (shows iterative process across all stages)

Design_Document.md
  What it shows: Formal system design — data model, node
    specifications, gate routing logic, state schema.
  Links to: DL3 (Designing), LO3

Architecture_Diagram.md
  What it shows: C4 diagram and flow diagram for the system.
  Links to: DL3 (Designing), LO3

Skeleton_Design.md
  What it shows: Early skeleton design before full build —
    shows design iteration happened before implementation.
  Links to: DL3 (Workshop strategy), LO3

Bug_Log.md
  What it shows: Seven bugs documented with symptom, root cause,
    and fix — five from the build phase (LO4) and two from the
    managing phase (LO5). Real failures, not sanitised.
    Bug 6: LLM failure caused silent skip of all gates.
    Bug 7: G3 baseline contaminated by same-cycle price write.
  Links to: DL4–DL6 (build and managing), LO4, LO5

Ethics_and_Responsibility.md
  What it shows: Ethical analysis of autonomous procurement —
    human oversight design, auditability, bias in supplier scoring.
  Links to: LO6

Growth_Reflection_LO7.md
  What it shows: Personal leadership reflection — how approach
    changed from DL1 (reading-based judgment) to DL6
    (observation-first). Explicit before/after framing.
  Links to: LO7

IMAGE EVIDENCE
──────────────
image evidence/criteria_table.png
  DL1 — Framework comparison results table (C1–C4 pass/fail).

image evidence/LangGraph gate.png
  DL1 — interrupt() firing at HITL gate, graph pausing.

image evidence/AutoGen.png
  DL1 — AutoGen running past the gate without pausing.

image evidence/CrewAI.png
  DL1 — CrewAI running past the gate without pausing.

image evidence/test_gate(1).png
  DL2 — Gate test output showing G1 and G2 firing correctly.

image evidence/test_gate(2).png
  DL2 — Gate test output showing G3, G4, G5, G6 firing correctly.

image evidence/threshold.png
  DL2 — Threshold evidence showing €300 / 15% / 4h values.

image evidence/SAW scoring table.png
  DL3 — SAW formula scoring table with supplier scores visible.

image evidence/reasoning log entry.png
  DL3 — WHAT/WHY/NEXT log entry in plain-language format.

image evidence/full 6-node output.png
  DL3 — Full 6-node graph run output showing all nodes executing.

image evidence/start_betsy_architecture.png
  DL3 — Architecture diagram showing full system structure.

image evidence/model chose.png
  DL4 — Model comparison table: llama3.2:3b vs gemma4:e4b,
    accuracy and latency results.

image evidence/Dashboard.png
  DL5 — Dashboard KPI overview: 5 metric tiles including
    autonomous approval rate, pipeline strip, inventory table.

image evidence/audit log.png
  DL5 — Decision History page showing 234 WHAT/WHY/NEXT entries.

image evidence/Orders & Invoices.png
  DL5 — Orders page: PO table with delivery status, Verify Now.

image evidence/reliable score update.png
  DL5 — Dynamic scoring: AccuParts 85.0 → 82.0 (delay) → 84.0.

image evidence/have verify invoice.png
  DL5 — Invoice-only routing: _after_monitor code + Verify Now.

image evidence/update price for new supplier.png
  DL6 — G3 fix: ViennaMach spike fires; new supplier skipped.

CODE ARTIFACTS
──────────────
agents/run_all.py + agents/langgraph_agent.py +
agents/autogen_agent.py + agents/crewai_agent.py
  DL1 — Three-framework comparison scripts. Run: python agents/run_all.py

test_gates.py
  DL2 — All 6 gates firing from CSV data. Run: python test_gates.py

run_dl3.py
  DL3 — Graph structure proof. Run: python run_dl3.py --design

test_model_choice.py
  DL4 — Model comparison. Run: python test_model_choice.py

betsy/nodes.py
  DL3, DL5, DL6 — All 6 nodes with WHAT/WHY/NEXT logging,
    try/except error-state entries, @traceable on _invoke_llm,
    updated G3 rolling average check.

betsy/graph.py
  DL3 — Graph assembly, routing functions, human_approval_node.
    Invoice-only routing (_after_monitor) added in Sprint 4.

betsy/database.py
  DL3, DL5, DL6 — init_db, seed_suppliers, save_purchase_order,
    get_approval_rate, record_price_history, get_price_average,
    update_supplier_reliability, flush_reasoning_log.

betsy/state.py
  DL3 — BetsyState TypedDict definition.

app.py
  DL5 — Streamlit dashboard: 5 KPI tiles, pipeline strip,
    audit log view, orders page, Verify Now button.

start_betsy.py
  DL4, DL5 — CLI entry point: --run, --schedule, --demo, --status.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 4 — LEARNING OUTCOME COVERAGE
────────────────────────────────────────

LO   Stage      Decision Log(s)    One-sentence summary
───  ──────────  ─────────────────  ──────────────────────────────────────────────
LO1  Analysing   DL1                Analysed three frameworks against four criteria
                                    in a controlled Lab test; only LangGraph passed.

LO2  Advising    DL2                Advised on gate thresholds using tail-spend
                                    literature (Library) and Jenny's real context
                                    (Field); justified €300, 15%, 4h, 95% target.

LO3  Designing   DL3                Designed a 6-node graph, BetsyState schema, and
                                    SAW scoring formula; validated with a skeleton
                                    proof (Workshop + Lab) before full build.

LO4  Realising   DL4 + Bug_Log      Realised the full system including LLM model
                                    selection test; documented and fixed 5 build
                                    problems in real operation.

LO5  Managing    DL5 + DL6          Managed the running system: 3 monitoring
                                    mechanisms designed, 4 code changes produced
                                    by observation, G3 fully redesigned, LangSmith
                                    integrated for real-time traceability.

LO6  Ethics      Ethics_and_        Analysed human oversight design, audit
                 Responsibility.md  transparency, and supplier scoring bias as
                                    ethical dimensions of autonomous procurement.

LO7  Leadership  Growth_            Personal leadership reflection: shift from
                 Reflection_LO7.md  reading-based judgment (DL1) to observation-
                                    first decision-making (DL6) documented with
                                    explicit before/after evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 5 — DOT METHOD INDEX
──────────────────────────────

Method     Used in    What it produced
─────────  ─────────  ─────────────────────────────────────────────────
Library    DL1, DL2   Framework documentation review → capability gaps
                      identified before Lab tests. Procurement literature
                      → tail-spend boundary (€300), invoice error rates.

Lab        DL1, DL3,  Framework comparison test (DL1). Skeleton graph run
           DL4, DL5,  against real CSV data (DL3). Model accuracy + latency
           DL6        test (DL4). Monitoring cycle observation (DL5). G3
                      root-cause diagnosis from audit log values (DL6).

Field      DL2, DL5,  Jenny's real working context → gate thresholds that
           DL6        fit her workflow (DL2). What Jenny needs from monitoring
                      vs. what the system provides (DL5). What a procurement
                      manager needs from a price spike alert (DL6).

Workshop   DL3        Built skeleton 6-node graph before full system — tested
                      the design, not just theorised about it. Confirmed
                      architecture before committing to full build.

Showroom   DL4, DL6   Model selection validated against project criteria and
                      academic literature (DL4). LangSmith integration makes
                      the G3 fix observable to any reviewer — not just logged,
                      but transparent in real time (DL6).

Every Decision Log documents its DOT method in section 5.
The Agile_Sprint_Overview.md contains the full quick-reference
table mapping each DL to its methods.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
