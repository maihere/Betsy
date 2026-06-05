━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 1 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is an autonomous procurement agent for a small
manufacturing company. It monitors inventory, scores suppliers,
places purchase orders, and verifies invoices — running on a
repeating cycle without human involvement for routine decisions.

Why this decision needs to be made now:
The project cannot be built at all without choosing a framework.
Every design decision that follows — how the workflow is
structured, how human approval works, how the audit log is
built — depends on what the chosen framework can actually do.
Choosing the wrong framework at this stage means rebuilding
everything from scratch later.

Where this fits:
This is the first decision in the project. It has no predecessor.
Every subsequent decision — how to define the approval gates
(DL2), how to structure the workflow nodes (DL3), which model
to use (DL4) — builds directly on this choice. If LangGraph
cannot do what is needed, none of those decisions can proceed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

Which AI workflow framework gives Betsy the ability to pause
mid-process and wait for a human decision before continuing —
and how do I know for certain it can do this before building
the whole system on top of it?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[X] Analysing   [ ] Advising   [ ] Designing
[ ] Realising   [ ] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
The framework must be able to pause the workflow at a specific
step and wait for a human response before continuing — not
simulate a pause, but genuinely freeze. Confirmed by running
a test where the workflow reaches the approval point and does
not proceed until an "approve" or "reject" message is sent.

Criterion 2:
The paused state must survive a process restart. If the
machine reboots while waiting for approval, the workflow must
resume from the same point when the process starts again —
not restart from the beginning. Confirmed by stopping the
process while paused and restarting it.

Criterion 3:
Every step of the workflow must be able to write to a shared
log that accumulates all entries across the full run. No step
should be able to overwrite another step's entries. Confirmed
by reading the log after a complete run and checking that all
steps are represented in order.

Criterion 4:
The framework must support a repeating autonomous cycle that
fires on a schedule without any manual trigger. Confirmed by
observing two consecutive cycles start automatically.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

LangGraph was selected as the workflow framework for Betsy
because it is the only framework among the three tested that
natively supports pausing mid-workflow, preserving state
across restarts, and accumulating a per-step reasoning log.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Library + Lab:
I used the Library strategy first — I read the documentation
and published architecture descriptions for all three
frameworks to understand what each one is designed to do and
where its boundaries are. I then used the Lab strategy — I
built a working implementation of the same procurement task
in all three frameworks and ran them side by side, recording
exactly what each one did when the workflow reached the
approval gate.

What I found:

From the documentation research:
AutoGen is built for conversational agents — multiple AI
agents that talk to each other and produce a final answer.
It is designed to run to completion. There is no documented
mechanism for pausing mid-conversation and waiting for a
human input before the next step.

CrewAI is built for task delegation — you define roles and
assign tasks to each role, and the crew executes them in
sequence or in parallel. The execution model is one-shot:
it starts, runs through all tasks, and returns a result.
There is no mechanism for pausing between tasks.

LangGraph is built for stateful workflow graphs — you define
nodes (steps) and edges (routing rules), and the graph
traverses them. It has a built-in interrupt() function that
genuinely pauses the graph at any node and a SqliteSaver
checkpointer that writes the full graph state to a database
file. The graph can be resumed from any saved checkpoint.

From the live comparison test:
All three frameworks were given the same procurement task:
score three suppliers, select the best one, check if the
order value exceeds the approval threshold, and pause for
human approval if it does.

LangGraph paused correctly at the approval gate and did
not proceed until the approval message was sent. The graph
state was written to the checkpoint database. When the
process was stopped and restarted, the graph resumed from
the pause point. The reasoning log accumulated entries from
every step in order.

AutoGen ran straight through to completion without pausing.
The approval gate was treated as a step in the conversation,
not as a genuine pause point. There was no state persistence
between runs.

CrewAI ran through all tasks in sequence without pausing.
The gate condition was evaluated but the workflow continued
regardless. No state persistence.

Evidence:
A side-by-side comparison table showing which framework
passed or failed each of the four criteria — produced by
running all three on the same task and recording the output.
The table shows LangGraph passing all four criteria and
AutoGen and CrewAI failing all four.

What this means:
AutoGen and CrewAI are the right tools for a different type
of problem — agents that reason through a question and return
an answer. They are not the right tools for a workflow that
needs to stop in the middle and wait for a human. This is not
a limitation of quality; it is a fundamental architectural
difference. Choosing either would have meant building a
workaround (polling, callbacks, external state management)
that would be fragile and academically indefensible.

LangGraph's interrupt() is purpose-built for exactly the
problem Betsy needs to solve: a workflow that acts
autonomously most of the time but pauses for human judgment
at specific, defined risk points.

So I decided:
Because the comparison test showed that only LangGraph can
genuinely pause and resume mid-workflow, and because
Criterion 1 (genuine pause, not simulated) was the
non-negotiable requirement for a trustworthy procurement
agent, LangGraph was the only defensible choice. AutoGen and
CrewAI would have required building a fake version of the
capability that LangGraph provides natively.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — LangGraph interrupt() froze the workflow
at the approval gate. The workflow did not continue until
the approval message was sent. AutoGen and CrewAI both ran
straight through.

Criterion 2: ✅ — SqliteSaver preserved the full graph
state when the process was stopped. On restart, the workflow
resumed from the pause point without losing any information
about which step it had reached or what data it had collected.

Criterion 3: ✅ — The Annotated[list, add] pattern in the
state definition meant every node appended its log entries
to the shared list. No node could overwrite another's
entries. After a full run, the log contained entries from
all six nodes in order.

Criterion 4: ✅ — APScheduler ran two consecutive cycles
automatically on the 4-hour interval without any manual
trigger between them.

Assumptions I am making:
LangGraph's interrupt() and SqliteSaver will continue to
behave as documented in future versions of the library. If
the API changes significantly, the pause-and-resume
mechanism could break without warning. This is an acceptable
risk for a prototype but would require monitoring in a
production system.

The SQLite checkpoint file is stored locally. If the file is
corrupted or deleted, the paused state is lost. For the
prototype scale this is acceptable — production would require
a more robust checkpoint store.

What surprised me:
AutoGen and CrewAI are both widely recommended as autonomous
agent frameworks, and the course materials presented all
three as comparable options. The comparison test showed they
are not comparable for this use case at all — they solve a
fundamentally different problem. I expected to find trade-offs
between the three frameworks. Instead I found that two of
the three cannot do the most important thing Betsy needs.
The decision was much clearer than I expected because the
criteria made the gap visible immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:
Side-by-side framework comparison table — three frameworks,
same task, four criteria, pass/fail recorded for each. The
output shows LangGraph passing all four and AutoGen and
CrewAI failing all four. Three runs each, consistent results.

Next LO stage: Moving to Advising

What I can now do that I could not before:
I can now design the approval gates (DL2) with confidence
that the framework can honor them. The gate design no longer
needs to work around technical limitations — I know the
pause-and-resume mechanism is real, tested, and persistent.
This means the gate thresholds can be defined based purely
on the business risk, not on what the framework can support.

How I will know this worked:
When the gate design is implemented and a real high-value
order triggers the approval gate, the system should pause
completely and wait for Jenny's response. If the gate fires
and the workflow pauses — and resumes correctly after
approval — this decision was right. If the pause mechanism
requires workarounds or behaves inconsistently, the framework
assumption was wrong and needs to be revisited.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
