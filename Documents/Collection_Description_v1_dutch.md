━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Portfolio Collection Description — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

There is a certain kind of job that looks manageable from the
outside but quietly eats through weeks. Jenny, a procurement
manager at a manufacturing company, had one of those. Every
Monday she checked which parts were running low, compared
prices across approved suppliers, placed purchase orders,
chased late deliveries, and verified that incoming invoices
matched what had been ordered. She was good at it. But none
of it required the kind of judgment she was there to provide
— it was just rules, applied carefully, over and over again.

I built Betsy: an autonomous procurement agent that monitors
inventory on a 4-hour cycle, scores approved suppliers using
a weighted formula, selects the best option, places purchase
orders, tracks deliveries, and verifies invoices against what
was ordered. Six gates define the boundary between what Betsy
handles alone and what stops completely and waits for Jenny's
decision before anything else happens. The full stakeholder
context and business case is in @00_Business_Analysis.docx.

The project ran across three iterations. Each iteration
produced decisions that fed directly into the next. The most
visible sign that this was iterative rather than sequential
is DL6: a decision made in Iteratie 3 that went back and
redesigned logic that had first been designed in Iteratie 1.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Iteratie 1 — Framework kiezen en grenzen bepalen

The first question before writing any production code was
whether the available tools could genuinely do what Betsy
needed. I had read documentation for three frameworks
(LangGraph, AutoGen, CrewAI) and all three looked plausible.
The non-negotiable requirement was that when a risky order
was detected, the system had to stop completely and wait —
not send a message and continue, but genuinely freeze. I
built a controlled comparison test: same task, same data,
same risk condition, all three frameworks. The result was
unambiguous.

@Decision_Log_1.docx — Framework Selection documents the
test design, what each framework produced, and how the
choice was made. @criteria_table.png shows the side-by-side
output. @AutoGen.png and @CrewAI.png show both frameworks
running straight past the risk condition without pausing.
@LangGraph gate.png shows LangGraph pausing at the exact
point requested, holding position, and resuming from the
same checkpoint after approval. The difference was
architectural: two frameworks are designed to reason to a
conclusion; LangGraph is designed to stop in the middle.

With the framework confirmed, I researched where the boundary
between autonomous action and human approval should sit.
This involved reading procurement risk management literature
(tail-spend thresholds, invoice error rates, automation
boundaries) and evaluating those findings against Jenny's
real working context — what she checks daily, what she
cannot delegate, what would concern her about an autonomous
system making decisions on her behalf.

@Decision_Log_2.docx — Gate Design records the justification
for each of the six conditions and the reasoning behind
whether each one freezes the workflow (HITL) or notifies
without stopping (HOTL). @test_gate(1).png and
@test_gate(2).png show all six firing correctly from real
supplier and invoice data, and staying quiet when they
should not trigger. @reasoning log entry.png shows one
complete example: the exact data the gate saw, the rule it
applied, and the outcome — written so anyone can read it
without technical knowledge.

WHAT THIS FINDING CHANGED:
The Lab test did not just confirm LangGraph. It changed what
the next iteration could be based on. Because interrupt()
was confirmed to work completely, the gate design in
Iteratie 1 had no technical constraints — only the right
answer for Jenny. The gate test against real data then
produced the 95% autonomous rate target that the Iteratie 2
architecture had to meet. Neither could have existed without
the other.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Iteratie 2 — Ontwerpen, bouwen en het eerste probleem vinden

Before writing production code, I designed the workflow and
tested the design on a small scale first. The goal was a
structure where every node had one responsibility and could
be described in one sentence. I used the Workshop strategy
to explore the design: building an early skeleton version
of the six-node structure to confirm which responsibilities
belonged to which step and where the shared state needed to
carry what data.

One design decision ran through everything: how much to
trust the LLM. My answer was to trust it with the
explanation, not the numbers. The supplier scoring formula
runs in arithmetic — every calculation visible and
repeatable. The model receives the result and writes two
sentences about the choice. It does not do the maths.
I then used the Lab strategy to test the design against real
inventory data before committing to the full build.

@DL3.docx — Workflow Architecture is the full design record:
the node structure, the state schema, the scoring formula
and the research behind it, and the skeleton proof that
confirmed the design before production code was written.
@full 6-node output.png shows that first test: all six
steps running, a gate triggering, the workflow pausing and
resuming from the same point. @SAW scoring table.png shows
the scoring formula working live in the finished dashboard —
every supplier score visible and broken into its components.
@threshold.png shows the inventory check running on real
parts data.

With the architecture locked, I ran a direct model
comparison. Rather than choosing on paper, I gave both local
options the actual task they would perform inside Betsy.
@DL4.docx — Model Selection documents that test and the
decision. @model chose.png shows the result: both models
answered correctly every time, but one averaged four seconds
per call while the other averaged over thirty. When accuracy
is equal, that is a clear answer.

Building the full system produced five problems that had not
appeared in the skeleton. @Bug_Log.docx documents all five
with the symptom, root cause, and fix for each. One did not
get fully resolved in this iteration: Gate G3 was treating
a missing previous price as zero, making any real price look
like an enormous increase. A partial fix was added, but the
full scale only became visible under real operating
conditions. Full resolution waited for Iteratie 3.

@start_betsy_architecture.png shows the complete production
system: all components connected, persistent state active,
and both types of human oversight working.

WHAT THIS FINDING CHANGED:
The skeleton proof confirmed the architecture — but it also
made the model question answerable. The architecture defined
the LLM's role precisely: confirm a selection from a scored
list and explain it. Until that role was defined, the model
could not be evaluated fairly. The skeleton locked the
design, which made the model comparison possible.
The G3 bug found during the full build was not a small fix
— it revealed that a design assumption from Iteratie 1 was
wrong under real conditions. That sent Iteratie 3 back into
the gate logic to redesign it completely.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Iteratie 3 — Observeren, bijsturen en opnieuw ontwerpen

With the full system running, the work shifted to watching
it — reading the audit log after every cycle, checking
dashboard numbers, asking whether what I was seeing matched
what the system should be doing. Three problems surfaced.
None of them were found by reading code. All three were
found by reading what the system had written about its own
decisions.

The first was the G3 false alarm. The audit log showed the
Decide node flagging new suppliers as price spikes — the
entry read "price €45.00 vs last price €0.00 — infinite%
increase." The partial null guard from Iteratie 2 had not
been enough. The underlying design assumption in DL2 — that
a previous price would always exist — was wrong for any
supplier added after the initial data was seeded. This
required going back to the gate logic designed in Iteratie 1
and rebuilding it: a new price_history table now records the
actual observed price on each cycle per supplier, and G3
compares against the rolling average of the last three
recorded prices.

@DL6.docx — G3 Redesign documents the full investigation:
the audit log entry that revealed the problem, the root
cause, the redesign decision, and two rounds of testing to
confirm both cases worked. This DL exists because Iteratie 3
monitoring revealed that an Iteratie 1 design decision
needed to be revised. @update price for new supplier.png
shows the fix: a genuine 26.7% spike caught correctly, and
a new supplier passing through without a false alarm.

The other two problems were found the same way. Supplier
reliability scores never updated — a supplier with a history
of late deliveries scored identically to one who had never
missed a deadline. And verifying a suspicious invoice
required running the entire four-hour cycle from the start.
Both were fixed: Track Delivery now applies a reliability
penalty (−3 points) when a delivery is overdue, and Verify
applies a bonus (+2 points) when an invoice matches cleanly;
graph routing was updated so an invoice check can be
triggered directly without a full cycle.

@DL5.docx — Monitoring and Managing documents all three
problems, their causes, and the code changes they produced.
The full set of outcomes is in DL5 section 7: four code
changes that resulted directly from observing the running
system. @Dashboard.png shows the dashboard used for daily
health checks — five KPI tiles including the autonomous
approval rate, calculated live from the audit log. @audit
log.png shows the full decision history view: the tool that
made diagnosing all three problems possible without
rerunning any code. @reliable score update.png shows the
dynamic scoring fix: AccuParts Corp dropping from 85.0 to
82.0 after a late delivery and recovering to 84.0 after a
clean invoice match. @have verify invoice.png shows the
routing change with a before-and-after explanation. @Orders
& Invoices.png shows the live Verify Now button on the
orders dashboard.

Monitoring also revealed a structural gap: the existing
visibility required someone to open the Streamlit dashboard
manually. LangSmith was integrated to capture every LangGraph
node execution as a structured trace — inputs, outputs,
latency, errors — visible in a web dashboard without opening
the local interface. The LLM call inside Decide is a named
span within the trace (supplier-selection-llm), separating
the AI reasoning step from the node wrapper so the prompt
and response are directly inspectable.

[LangSmith screenshot — full cycle trace: six-node sequence
with per-node latency and supplier-selection-llm span inside
Decide. Add once captured.]

[LangSmith screenshot — AI span open: prompt and raw
response. Add once captured.]

@Growth_Reflection.docx documents the personal shift across
these three iterations: from assumption-based judgment in
Iteratie 1 to observation-first decision-making in
Iteratie 3. (LO7 Personal Leadership)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Leeruitkomsten — where each LO is demonstrated

LO1 — Analysing
@Decision_Log_1.docx (three-framework comparison, four
criteria, controlled test output), @criteria_table.png,
@AutoGen.png, @CrewAI.png, @Decision_Log_2.docx (gate
condition analysis, procurement literature review, 95%
autonomous rate measured from real data), @test_gate(1).png,
@test_gate(2).png, @Research_Landscape.docx

LO2 — Advising
@Decision_Log_2.docx (threshold justifications: €300
tail-spend boundary, 15% spike, 4h stale data; HITL/HOTL
classification reasoning), @DL4.docx (model selection
recommendation with measured evidence), @DL6.docx (redesign
recommendation after monitoring revealed the original
assumption was wrong)

LO3 — Designing
@DL3.docx (six-node architecture, BetsyState schema, SAW
scoring formula with academic references), @Skeleton_Design.docx,
@full 6-node output.png, @SAW scoring table.png,
@start_betsy_architecture.png, @Architecture_Diagram.docx,
@DL5.docx (monitoring mechanism design), @DL6.docx
(price_history table design, rolling average redesign)

LO4 — Realising
@DL4.docx (model comparison test, full system delivery),
@model chose.png, @Bug_Log.docx (five build problems
diagnosed and fixed), @start_betsy_architecture.png,
@threshold.png, @Orders & Invoices.png

LO5 — Managing and Controlling
@DL5.docx (three problems found through monitoring, four
code changes produced by observation), @DL6.docx (G3
redesign triggered by what the audit log showed),
@Dashboard.png (five KPI tiles including approval rate),
@audit log.png, @reliable score update.png,
@have verify invoice.png, @update price for new supplier.png,
LangSmith project betsy-procurement (cycle traces)

LO6 — Professional Standard
@reasoning log entry.png (audit log readable without
technical knowledge), @00_Business_Analysis.docx,
@Ethics_and_Responsibility.docx, @Orders & Invoices.png,
@start_betsy_architecture.png

LO7 — Personal Leadership
@Growth_Reflection.docx (explicit before and after:
Iteratie 1 assumption-based judgment vs Iteratie 3
observation-first reasoning; what broke the assumption
and what changed)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agile werkwijze

De drie iteraties bouwen inhoudelijk op elkaar: framework en
gates bevestigd via testen (1) → architectuur ontworpen,
skelet getest, daarna volledig gebouwd (2) → monitoring,
observatie en herontwerp (3). Elke iteratie sloot af met
werkende software. Het meest directe bewijs van het iteratieve
proces is DL6 — een beslissing in Iteratie 3 die de gate-
logica herzag die in Iteratie 1 voor het eerst was geschreven,
getriggerd niet door het originele ontwerp te herzien maar
door te lezen wat het draaiende systeem over zijn eigen
beslissingen schreef.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
