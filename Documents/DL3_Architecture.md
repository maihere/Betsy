━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 3 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is an autonomous procurement agent built on LangGraph
(DL1). Six gates define when it must pause for human
approval and when it can act alone (DL2). Now the workflow
itself needs to be designed: how many steps, what each step
does, what data flows between them, and how the reasoning
log is structured.

Why this decision needs to be made now:
The framework and the gates are chosen, but there is no
structure yet. Without a defined workflow, the gates have
nowhere to be placed and the data from one step has no way
to reach the next step. Every line of code that follows
depends on the architecture being correct. A wrong design
here means nodes with overlapping responsibilities, data
getting lost between steps, or gates firing at the wrong
point in the process.

Where this fits:
DL2 defined what the gates are and when they fire. DL3
designs the workflow that the gates live inside. DL4 (model
selection) then sits inside the Decide node — the node this
design defines. The architecture locks in before the model
is chosen.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

How should the workflow be structured so that each step has
one clear responsibility, the right data is available at
each gate, the reasoning log captures every decision in
plain language, and the whole thing can be inspected and
debugged by someone who did not build it?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[ ] Analysing   [ ] Advising   [X] Designing
[ ] Realising   [ ] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
Each node must map to exactly one business process phase.
No node should do two different things. A node that both
evaluates suppliers and decides the order quantity is doing
two jobs — it is harder to debug, harder to test, and harder
to explain. Confirmed by being able to describe each node
in one sentence without using "and."

Criterion 2:
The scoring formula for supplier selection must be
deterministic — the same inputs must always produce the
same output. It must not depend on an LLM for any
calculation. Confirmed by running the formula three times
with the same input and getting the same result each time.

Criterion 3:
The reasoning log must be readable by a non-technical
procurement manager. After a full cycle, Jenny should be
able to open the audit log and understand what Betsy did
and why at every step, without needing to read code.
Confirmed by showing the log output to someone unfamiliar
with the system and asking them to explain what happened.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

A six-node linear graph was designed: Monitor → Evaluate →
Decide → Order → Track → Verify. A single shared state
dictionary carries all data between nodes. The supplier
scoring formula is implemented in pure Python. The LLM is
used only for confirming the selection and generating a
plain-language explanation. Every node writes a WHAT/WHY/NEXT
entry to a shared, append-only reasoning log.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Workshop + Lab:
I used the Workshop strategy to design the architecture —
building a skeleton version of the workflow to explore what
structure made each responsibility clear and where the data
needed to flow. Different node arrangements were tried and
the one that gave each node a single, unambiguous job was
kept. I then used the Lab strategy to test the skeleton —
running it against real inventory data to verify that data
flowed correctly between nodes, the gates fired at the right
points, and the reasoning log captured entries from every
step.

What I found:

From the Workshop design phase:
The procurement process has a natural sequential structure:
you cannot score suppliers until you know which parts need
ordering, you cannot decide the order until suppliers are
scored, you cannot place the order until the decision is
made. This means the workflow is linear, not branching —
each node feeds exactly one next node under normal
conditions, with gate-triggered pauses as the only branches.

The shared state dictionary was chosen over message-passing
between nodes because LangGraph's state model is designed
for exactly this pattern: all nodes read from and write to
a single TypedDict. This makes it easy to see at any point
in the run exactly what data is available and what has
already been set.

The six nodes map directly to the six business phases
identified in the as-is process analysis:
- Monitor: check what needs ordering (replaces Jenny's
  manual spreadsheet check)
- Evaluate: score available suppliers (replaces Jenny's
  ad-hoc comparison)
- Decide: choose the supplier and calculate the order
  (replaces Jenny's gut-feel selection, with LLM to explain)
- Order: create and record the purchase order (replaces
  Jenny's manual PO creation)
- Track: check whether previous orders have arrived
  (replaces Jenny's manual delivery follow-up)
- Verify: match incoming invoices against POs
  (replaces Jenny's manual invoice checking)

The scoring formula — Simple Additive Weighting from
Fishburn (1967) — uses three criteria from Dickson's (1966)
supplier selection research: reliability (weighted at 40%),
price (35%), and delivery speed (25%). Reliability is
weighted highest because a late delivery that stops the
production line costs far more than the difference between
the cheapest and most expensive supplier.

Crucially, the LLM does not calculate this formula. Python
calculates it. The LLM receives the pre-calculated scores
and is asked to confirm the selection and write a two-
sentence explanation. This is not about trusting or
distrusting the LLM — it is about the right tool for each
job. Arithmetic is deterministic. LLMs are probabilistic.
The financial decision must be deterministic.

From the Lab test:
The skeleton was run against the real inventory.csv file.
The Monitor node correctly identified parts below their
reorder threshold. The Evaluate node scored suppliers and
the scores matched the manual calculation. The Decide node
called the LLM and received a valid selection. The gate
condition (order value above €300) fired correctly and the
graph paused. After sending the approval, the Order node
ran and the purchase order was written to the database.
The reasoning log contained entries from every node in
order.

Evidence:
Skeleton proof output — full terminal log showing the graph
running through the 6-node sequence, the WHAT/WHY/NEXT
reasoning entries visible, a gate firing, interrupt()
executing, the graph resuming after approval, and the
reasoning log saved to betsy.db.

![Full graph run — Monitor fires G6 (stale data 6.8h), interrupt() pauses, resumes on approval, reasoning log entries saved to betsy.db](<../image evidence/full 6-node output .png>)

Architecture diagram — six nodes connected in sequence with
gate branches shown at the correct positions. Produced
during the Workshop design phase.

SAW scoring formula confirmed in the live dashboard — the
Suppliers page showing all approved suppliers with their
reliability, price, and delivery values and the calculated
SAW score. The score breakdown table below confirms each
of the three weighted components (reliability 40% + price
35% + delivery 25%).

![Suppliers page — SAW scores per supplier with score breakdown by component (reliability/price/delivery)](<../image evidence/SAW scoring table.png>)

Inventory monitoring confirmed live — the Stock Levels
dashboard page showing 8 low-stock parts highlighted in
red and the Stock vs Threshold bar chart comparing current
stock against reorder threshold for all 20 parts. This is
the visual output of the Monitor node working correctly.

![Stock Levels page — 8 low-stock parts highlighted, Stock vs Threshold bar chart for all 20 parts](<../image evidence/threshold.png>)

What this means:
The six-node sequential design gives each node a single
responsibility, which makes the system predictable,
testable, and explainable. The shared state dictionary
means data is never lost between nodes — every field is
available at every step. The SAW formula being in Python
means the financial decision is always reproducible and
auditable. The WHAT/WHY/NEXT log format means any decision
can be explained in plain language after the fact.

So I decided:
Because the skeleton proof confirmed the data flow works
correctly and the gates fire at the right positions, and
because the one-node-one-responsibility design passed the
plain language test (every node can be described in one
sentence), this architecture is the foundation for the full
implementation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — Each of the six nodes can be described
in one sentence without using "and." Monitor checks stock.
Evaluate scores suppliers. Decide selects and checks gates.
Order writes the PO. Track checks delivery. Verify matches
invoices. None of the nodes overlap in responsibility.

Criterion 2: ✅ — The SAW formula is pure Python. Running
it three times with identical inputs (same supplier prices,
same reliability scores, same delivery days) produced
identical outputs all three times. No LLM involvement in
the calculation.

Criterion 3: ✅ — The reasoning log was shown to a person
unfamiliar with the system. They were able to describe what
Betsy had done at each step using only the log entries.
The WHAT/WHY/NEXT format made the sequence of decisions
clear without requiring any code knowledge.

Assumptions I am making:
The SAW scoring weights (reliability 40%, price 35%,
delivery 25%) are calibrated for a manufacturing context
where production line availability is the top priority. A
different business context — for example, one where cost
reduction is the primary goal — would justify different
weights. The weights should be reviewed if the business
context changes.

The LLM is used as a reasoning formatter, not a decision
maker. This assumption holds as long as the Python scoring
formula is correct. If there is a bug in the formula, the
LLM cannot catch it — it will confirm whatever score it
is given.

What surprised me:
The most valuable design decision turned out to be the
simplest one: keeping the workflow linear. An early design
considered a branching structure where the Monitor node
could route to different evaluation paths depending on
urgency level. This was abandoned because it made the gate
placement ambiguous and the reasoning log harder to follow.
The simpler sequential design was easier to test, easier to
explain, and easier to place gates in correctly. Complexity
was removed, not added, as the design matured.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:

Skeleton_Design.md — the complete original design document
capturing the BetsyState schema with field-by-field
justifications, the full 6-node graph topology with routing
functions, the SAW formula with normalisation logic, and the
WHAT/WHY/NEXT log format with worked examples. This document
was produced during the Workshop phase before full
implementation began.

betsy/state.py — the BetsyState TypedDict in code. Every
field in the schema maps to a business concern documented
in the design. The Annotated[list, add] pattern for
reasoning_log is the key design choice: it is the mechanism
that allows all six nodes to contribute to a shared audit
trail without overwriting each other.

betsy/graph.py — the 6 routing functions (_after_monitor,
_after_evaluate, _after_decide, _after_human_approval,
_after_order, _after_verify) that encode every branching
decision in the system. Reading these functions answers the
question "when does Betsy ask a human?" completely and
explicitly.

betsy/nodes.py — the implementation of all 6 nodes. Each
node function maps to the responsibility defined in the
design: one node, one business process phase, one set of
state fields read and written.

Skeleton proof terminal output — a full run from Monitor to
the G1 pause using run_dl3.py, showing real inventory data
from the CSV, real SAW scores calculated by Python, the
LLM selection confirmed by llama3.2:3b, and the WHAT/WHY/NEXT
entries from each node. Three consistent runs confirming the
design holds.

SAW scoring worked example — for PART-001 (Bearing Assembly),
three candidate suppliers scored on reliability, price, and
delivery, with the final SAW score and winning supplier shown.

Prior design document — Design_Document_DL3_v2 (Updated).docx
in the Documents folder contains the earlier design work
produced before the full implementation, including the initial
node responsibilities, state field planning, and gate position
mapping. This pre-dates the current implementation and shows
the design thinking that preceded the build.

Architecture_Diagram.md — Mermaid flowcharts showing the
6-node topology, gate positions, HITL/HOTL classification,
and the BetsyState field flow between nodes. Produced as a
visual reference alongside the text-based design document.

Next LO stage: Moving to Realising

What I can now do that I could not before:
I can now write the full implementation. Every node has a
defined responsibility and a defined set of fields it reads
and writes in the state dictionary. The LLM prompt can be
written knowing exactly what inputs it will receive. The
gates can be coded at the correct positions. There are no
open architectural questions remaining.

How I will know this worked:
When the full system runs end-to-end — not just the skeleton
but the complete Streamlit dashboard and all six gates
firing from their demo scenarios — and the audit log is
readable to a non-technical person who can describe every
decision correctly, the architecture decision was right.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
