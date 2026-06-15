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

I built Betsy: an autonomous procurement agent that handles
routine purchasing on its own, and stops completely when
something genuinely needs a human opinion. By the end of the
project, Betsy was running on its own schedule, making
purchasing decisions, and producing a clear record of
everything it had ever done. The full picture of who Jenny
is, what her working life looks like, and why this problem
is worth solving is in @00_Business_Analysis.docx — the
document that grounded every decision that followed it.
(LO1 Analysing)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sprint 1 — Finding the Foundation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The first question was not how to build Betsy. It was whether
the tools available could actually do what Betsy needed at
all. I had read about three frameworks for building AI agents
and all three looked like they might work. But there was one
thing I was not willing to assume: that when the system hit
something risky, it could genuinely stop — not send a message
and carry on, but freeze completely, hold its position, and
wait for a human decision before doing anything else.
Reading about it was not enough. I needed to see it.

So before writing a single line of production code, I built
a small test. Same task, same data, same risk condition, all
three frameworks. @Decision_Log_1.docx — Framework Selection
is the record of that experiment — what I was testing for,
what each framework produced, and the reasoning behind the
choice I made. (LO1 Analysing) @criteria_table.png is the
side-by-side output of that test — three frameworks, one
task, and a clear picture of which ones stopped and which
ones did not. (LO1 Analysing) @AutoGen.png shows one
running straight through to the end as if nothing had
happened. It is the evidence that the problem is real, not
hypothetical. (LO1 Analysing) @CrewAI.png shows the other
doing the same — confirming this was not a one-off. (LO1
Analysing) And then @LangGraph gate.png shows the one that
worked: pausing at exactly the point I asked, holding
position, and resuming from the same checkpoint after I gave
the go-ahead. That is the moment the whole project became
possible. (LO1 Analysing)

The difference was not a configuration issue. It was
architectural. Two frameworks are built to reason to a
conclusion and return an answer. LangGraph is built to stop
in the middle and wait. That finding changed what Sprint 1
could produce next — because the pause mechanism was now
confirmed real, the stopping conditions could be designed
purely around what the business needed, with no technical
constraint shaping the answer.

With the framework confirmed, the next question felt harder
in a different way. Less technical, more like a judgment
call I was making on Jenny's behalf. Where exactly should
Betsy stop, and why? Every condition had to be justified. I
spent time in the procurement literature — how organisations
manage purchasing risk in practice, where the boundary
between routine and risky sits, and what the cost of a
wrong autonomous decision actually looks like. Then I brought
those findings back to Jenny's real context to check whether
they matched what she actually dealt with day to day.

@Decision_Log_2.docx — Gate Design is the record of that
recommendation — the justification for every stopping
condition, and the reasoning behind whether each one freezes
the workflow completely or sends a notification and waits.
(LO2 Advising) @test_gate(1).png and @test_gate(2).png are
the test outputs — proof that all six conditions fire
correctly from real supplier and invoice data, and stay
quiet when they should. This is what moves the design from
a proposal to something I could stand behind. (LO1 Analysing,
LO2 Advising) @reasoning log entry.png shows one complete
example of what the system writes when a condition fires —
the exact data it saw, the rule it applied, the action it
took — written so anyone could read it without needing to
understand the code. (LO2 Advising, LO6 Professional
Standard)

Running those gate tests against real inventory data also
produced a number I had not had before: how often the
conditions would actually fire in practice. That percentage
became the target the Sprint 2 architecture had to meet.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sprint 2 — Building on What Was Confirmed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
took a few rounds. The final structure was six steps —
Monitor, Evaluate, Decide, Order, Track, Verify — each with
one job, and a shared memory that carries all information
from one step to the next. One design decision ran through
everything: how much to trust the AI. My answer was to
trust it with the explanation, not the numbers. The scoring
formula runs in plain arithmetic — every calculation visible
and repeatable. The model receives the result and writes
two sentences about why that supplier was chosen. It does
not do the maths.

Before building the full system, I built a skeleton — a
lightweight version of the six-step structure running against
real data to confirm the design held before anything depended
on it. The skeleton ran all six steps, a condition triggered,
the workflow paused, and it resumed correctly from the saved
point.

@DL3.docx — Workflow Architecture is the full design record
— the step structure, the shared memory schema, the scoring
formula and the academic research it draws from, and the
results of that first skeleton test. (LO3 Designing)
@full 6-node output.png is the output from that skeleton run
— the moment the design stopped being a diagram on paper and
became something real. (LO3 Designing) @SAW scoring table.png
shows the scoring formula working live in the finished
dashboard — every supplier's score visible and broken into
its parts, nothing hidden from the person reading it. (LO3
Designing, LO6 Professional Standard) @threshold.png shows
the inventory monitoring step running on real parts data,
the first step of the full system doing its job as designed.
(LO3 Designing)

With the design confirmed, I ran a direct model comparison.
Rather than choosing on paper, I gave both local options the
actual task they would perform inside the workflow: return a
valid selection from a scored list. Both answered correctly
every time. One averaged four seconds per call. The other
averaged over thirty. When accuracy is equal, that is a
clear answer. @DL4.docx — Model Selection is the record of
that test and the decision it produced. (LO2 Advising, LO4
Realising) @model chose.png shows the raw comparison output
— two models, same task, and the number that made the choice
obvious. (LO4 Realising)

Building the full system — all six steps, all six conditions,
the database, the dashboard, and the automated schedule —
produced five problems that had not appeared in the skeleton.
@Bug_Log.docx documents all five: what broke, why it broke,
and what changed to fix it. It is the honest record of what
building something real actually looks like. (LO4 Realising)
One of them did not get fully resolved in this sprint. The
price spike check was treating a missing previous price as
zero — making any real price look like an enormous increase.
A partial fix was added, but the full scale of the problem
only became visible under real operating conditions. Full
resolution waited for Sprint 3.

@start_betsy_architecture.png shows the complete production
system: all components connected, persistent state active,
and both types of human oversight working — the full system
that Sprint 2 delivered. (LO4 Realising, LO3 Designing)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sprint 3 — Watching, Finding, and Going Back
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

There is a version of Sprint 3 where I would have looked at
the running system, seen that it was working, and called it
done. That is not what happened. I watched it run. I read
the log it produced after every cycle, looked at the
dashboard numbers, and asked whether what I was seeing made
sense. Some of it did not.

The first thing I noticed was a stopping condition firing
when it should not have been. The audit log showed exactly
what had happened: the system had no previous price to
compare against for a new supplier, treated that absence as
zero, and flagged any real price as an enormous increase.
The entry read "price €45.00 vs last price €0.00 — infinite%
increase." The partial fix from Sprint 2 had not been enough.
And the original assumption — that a previous price would
always exist — had been baked into the logic since Sprint 1.

This sent me back. I redesigned the price spike check
completely: a price history table now records the actual
price observed each cycle, and the check compares against a
rolling average of the last three recorded prices. If no
history exists, the check is skipped entirely. @DL6.docx —
G3 Redesign is the record of that investigation — the audit
log entry that revealed the problem, the root cause traced
through the data, and the full redesign decision. This
document exists because Sprint 3 monitoring found a flaw in
a Sprint 1 design decision and required going back to fix it.
(LO5 Managing and Controlling) @update price for new
supplier.png shows both cases working correctly — a genuine
price spike caught, and a new supplier passing through without
a false alarm. The fix shown here is what watching the
running system produced. (LO5 Managing and Controlling)

The other two problems surfaced the same way — by watching,
not by reading code. Supplier reliability scores were frozen
at their original values, so a supplier with a history of
late deliveries looked identical in the scoring to one who
had never missed a deadline. And verifying a suspicious
invoice required running the entire four-hour cycle from
the start, which was not practical. I fixed both.

@DL5.docx — Monitoring and Managing documents all three
problems, what caused each, and the code changes they
produced. It is the record of what the managing phase
actually did — not just observation, but action. (LO5
Managing and Controlling) @Dashboard.png shows the live
dashboard used to check the system each cycle — five KPI
tiles now, the fifth showing the percentage of procurement
cycles that completed without needing Jenny's input at all.
(LO5 Managing and Controlling, LO6 Professional Standard)
@audit log.png shows the full decision history in readable
form — the tool that made diagnosing all three problems
possible without touching the code. (LO5 Managing and
Controlling) @reliable score update.png shows the scoring
fix in action: a supplier's reliability dropping after a
late delivery and recovering after a clean invoice match,
the score now reflecting what actually happened. (LO5
Managing and Controlling) @have verify invoice.png shows the
routing fix — the code before and after, with a plain note
on what changed and why it mattered. (LO5 Managing and
Controlling) @Orders & Invoices.png shows that fix working
in the live dashboard: a button that checks an invoice on
demand, without waiting for the next automated cycle. (LO5
Managing and Controlling, LO6 Professional Standard)

Watching the fixed system also showed one more gap. All the
existing visibility relied on someone opening the dashboard
manually. For a system running on its own schedule, that
meant problems would only be noticed if someone happened to
be watching at the right moment. I integrated LangSmith so
that every step of the workflow is captured as a structured
trace — what went in, what came out, how long it took — all
visible in a separate web dashboard, no local access needed.
The AI call inside the Decide step is its own named entry in
that trace, so the exact question sent to the model and the
answer it returned are visible to any reviewer without
reading the code.

[LangSmith screenshot — full cycle trace showing all six
steps with per-step timing and the AI call nested inside
Decide as its own named span. Add once captured.]
(LO5 Managing and Controlling)

[LangSmith screenshot — the AI span open, showing the prompt
sent and the raw response returned. Add once captured.]
(LO5 Managing and Controlling)

@Growth_Reflection.docx is the honest account of what
changed across these three sprints — from trusting a
well-tested plan at the start to letting the running
system's own output be the thing that tells you what to
do next. (LO7 Personal Leadership)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agile approach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The three sprints build on each other: foundations confirmed
through testing (1) → architecture designed, skeleton tested,
then built in full (2) → monitoring, observation, and
redesign (3). Each sprint closed with working software and
a finding that changed what the next sprint started with.
The most direct evidence of the iterative process is DL6 —
a decision in Sprint 3 that revised gate logic first written
in Sprint 1, triggered not by reviewing the original design
but by reading what the running system said about its own
decisions. Managing and Controlling ran through all three
sprints: Lab testing in Sprint 1 to verify framework claims
before committing, a skeleton proof in Sprint 2 before
building the full system, and four code changes in Sprint 3
produced directly from observing the running system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
