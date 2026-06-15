━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Portfolio Collection Description — v2 (separate LO table)
Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project

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

The project ran across three sprints. Each sprint produced
findings that changed what the next sprint started with.
The clearest sign of that is a decision made in Sprint 3
that required going back and redesigning gate logic that had
first been written in Sprint 1.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint 1 — Finding the foundation

The first question was not how to build Betsy. It was whether
the tools available could actually do what Betsy needed at
all. I had read about three frameworks for building AI agents
and all three looked like they might work. But there was one
thing I was not willing to assume: that when the system hit
something risky, it could genuinely stop — not send a message
and carry on, but freeze completely, hold its position, and
wait for a human decision before doing anything else. Reading
about it was not enough. I needed to see it.

So before writing a single line of production code, I built
a small test. Same task, same data, same risk condition, all
three frameworks. @Decision_Log_1.docx — Framework Selection
is the record of that experiment: what I was testing for,
what each framework produced, and how the choice was made.
@criteria_table.png is the side-by-side result — all three
running the same procurement task, and what each one did the
moment the risk condition fired. @AutoGen.png shows one
running straight through to the end as if nothing had
happened. @CrewAI.png shows the other doing the same. And
then @LangGraph gate.png shows the one that worked: pausing
at exactly the point I asked, holding position, and resuming
from the same checkpoint after I gave the go-ahead.

The difference was not a configuration issue. It was
architectural. Two frameworks are built to reason to a
conclusion and return an answer. LangGraph is built to stop
in the middle and wait. That finding changed what Sprint 1
could produce next — because the pause mechanism was now
confirmed real, the gate conditions could be designed purely
around what the business needed, with no technical constraint
shaping the answer.

With the framework confirmed, the next question felt harder
in a different way. Less technical, more like a judgment call
I was making on Jenny's behalf. Where exactly should Betsy
stop, and why? Every condition had to be justified. I spent
time in the procurement literature — how organisations manage
purchasing risk in practice, where the routine-to-risky
boundary sits, what the cost of a wrong autonomous decision
looks like. Then I brought those findings back to Jenny's
real context to check whether they matched what she actually
dealt with day to day.

@Decision_Log_2.docx — Gate Design is the record of that
recommendation: the justification for every condition and
the reasoning behind whether each one freezes the workflow
completely or notifies without stopping. @test_gate(1).png
and @test_gate(2).png show all six conditions firing
correctly from real supplier and invoice data, and staying
quiet when they should not trigger. @reasoning log entry.png
shows one complete example — the exact data the gate saw,
the rule it applied, and the outcome — written so anyone
could read it without needing to understand the code.

Running those gate tests against real inventory data also
produced a number I had not had before: how often the gates
would fire in practice. That percentage became the target
the Sprint 2 architecture had to meet.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint 2 — Building on what was confirmed

Starting Sprint 2 felt different. The uncertainty of the
first sprint — not knowing if the approach was even possible
— had been replaced by a different challenge. Now I had to
design something that made sense as a workflow, and then
build it. I made a deliberate choice to design before I
built, and to test the design before I committed to it fully.
Sprint 1 had already shown that documentation and actual
behaviour can differ. I was not going to skip that lesson
when it came to my own design.

I worked out how many steps the workflow needed and what
each one was responsible for. My goal was to reach a point
where every step could be described in one sentence. That
took a few rounds. The final structure was six nodes —
Monitor, Evaluate, Decide, Order, Track, Verify — each with
one job, and a shared state that carries all information
from one step to the next. One design decision ran through
everything: how much to trust the LLM. My answer was to
trust it with the explanation, not the numbers. The scoring
formula runs in plain arithmetic — every calculation visible
and repeatable. The model receives the result and writes two
sentences about why that supplier was chosen. It does not
do the maths.

Before building the full system, I built a skeleton — a
lightweight version of the six-node structure running against
real data to confirm the design held before anything depended
on it. The skeleton ran all six steps, a gate triggered, the
graph paused, and it resumed correctly from the saved
checkpoint.

@DL3.docx — Workflow Architecture is the full design record:
the node structure, the shared state schema, the scoring
formula and the academic research behind it, and the skeleton
proof that confirmed the design before production code was
written. @full 6-node output.png shows that first test run
in full. @SAW scoring table.png shows the scoring formula
working live in the finished dashboard — every supplier score
visible and broken into its components, nothing hidden.
@threshold.png shows the inventory monitoring step running
on real parts data.

With the architecture locked, I ran a direct model
comparison. Rather than choosing on paper, I gave both local
options the actual task they would perform inside Betsy:
return a valid JSON object selecting the highest-scored
supplier from a list. Both answered correctly every time.
One averaged four seconds per call. The other averaged over
thirty. When accuracy is equal, that is a clear answer.
@DL4.docx — Model Selection documents the test and the
decision. @model chose.png shows the raw output.

Building the full system — all six nodes, all six gates,
the database, the dashboard, the automated scheduler —
produced five problems that had not appeared in the skeleton.
All five are in @Bug_Log.docx with the symptom, cause, and
fix for each. One of them did not get fully resolved in this
sprint. Gate G3, which detects suspicious price spikes, was
treating a missing previous price as zero — making any real
price look like an enormous increase. A partial fix was
added, but the full scale of the problem only became visible
when the system ran under real operating conditions. Full
resolution waited for Sprint 3.

@start_betsy_architecture.png shows the complete production
system: all components connected, persistent state active,
and both types of human oversight working.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint 3 — Watching, finding, and going back

There is a version of Sprint 3 where I would have looked at
the running system, seen that it was working, and called it
done. That is not what happened. I watched it run. I read
the log it produced after every cycle, looked at the
dashboard numbers, and asked whether what I was seeing made
sense. Some of it did not.

The first thing I noticed was a stopping condition firing
when it should not have been. The audit log showed exactly
what had happened: the Decide node had no previous price to
compare against for a new supplier, treated that absence as
zero, and flagged any real price as an enormous increase.
The entry read "price €45.00 vs last price €0.00 — infinite%
increase." The partial fix from Sprint 2 had not been enough.
And the original design assumption — that a previous price
would always exist — had been baked into the gate logic
since Sprint 1.

This sent me back. I redesigned the G3 logic completely: a
price history table now records the actual price observed
each cycle, and the gate compares against a rolling average
of the last three recorded prices. If no history exists, the
check is skipped entirely rather than defaulted to zero.
@DL6.docx — G3 Redesign is the full record of that
investigation: what the audit log showed, what caused it,
and what was rebuilt. @update price for new supplier.png
shows both cases working correctly — a genuine 26.7% spike
caught, and a new supplier passing through without a false
alarm. This decision log exists because Sprint 3 monitoring
found a flaw in a Sprint 1 design decision and required
going back to fix it.

The other two problems surfaced the same way — by watching,
not by reading code. Supplier reliability scores were frozen
at their seeded values, which meant a supplier with a history
of late deliveries scored the same as one who had never
missed a deadline. And verifying a suspicious invoice
required running the entire four-hour procurement cycle from
the start, which was not practical. I fixed both. The Track
Delivery node now applies a reliability penalty when a
delivery is overdue. The Verify node applies a bonus when
an invoice matches cleanly. The graph routing was updated so
an invoice can be checked immediately without waiting for
the next full cycle.

@DL5.docx — Monitoring and Managing documents all three
problems, what caused each, and what changed in the code.
@Dashboard.png shows the live dashboard with five KPI tiles
— the fifth showing the autonomous approval rate calculated
from the audit log: cycles completed without any gate
interrupt divided by total cycles run. @audit log.png shows
the full decision history — the tool that made diagnosing
all three problems possible without rerunning any code.
@reliable score update.png shows the dynamic scoring fix:
AccuParts dropping from 85.0 to 82.0 after a late delivery,
then recovering to 84.0 after a clean invoice match.
@have verify invoice.png shows the routing fix with a
before-and-after explanation. @Orders & Invoices.png shows
the Verify Now button working live on the orders page.

Watching the fixed system also showed one more gap. All the
existing visibility relied on someone opening the dashboard
manually. For a system running on an automated schedule, that
meant anomalies would only be caught if someone happened to
be watching. I integrated LangSmith to capture every
LangGraph node execution as a structured trace — inputs,
outputs, latency, and errors — visible in a web dashboard
without opening the local interface. The LLM call inside
the Decide node is a named span in the trace, so the exact
prompt sent and the response returned are directly visible
to any reviewer without reading the code.

[LangSmith screenshot — full cycle trace: all six nodes,
per-node latency, supplier-selection-llm span inside Decide.
Add once captured.]

[LangSmith screenshot — AI span open: prompt + raw response.
Add once captured.]

@Growth_Reflection.docx is the honest account of what
changed across these three sprints — from trusting a
well-tested plan in Sprint 1 to treating the running
system's own output as the primary source of truth in
Sprint 3. (LO7 Personal Leadership)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Learning outcomes — where each LO is shown

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
@Growth_Reflection.docx (explicit before and after: Sprint 1
assumption-based judgment vs Sprint 3 observation-first
reasoning; what broke the assumption and what changed)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agile approach

The three sprints build on each other: foundations confirmed
through testing (1) → architecture designed, skeleton tested,
then built in full (2) → monitoring, observation, and redesign
(3). Each sprint closed with working software and a finding
that changed what the next sprint started with. The most
direct evidence of the iterative process is DL6 — a decision
in Sprint 3 that revised gate logic first written in Sprint 1,
triggered not by reviewing the original design but by reading
what the running system said about its own decisions.
Managing and Controlling ran through all three sprints: Lab
testing in Sprint 1 to verify framework claims before
committing, a skeleton proof in Sprint 2 before building the
full system, and four code changes in Sprint 3 produced
directly from observing the running system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
