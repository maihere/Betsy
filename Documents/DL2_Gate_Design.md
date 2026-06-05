━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 2 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is an autonomous procurement agent that monitors
inventory, scores suppliers, and places purchase orders on
a 4-hour cycle. DL1 established that LangGraph is the right
framework because it can genuinely pause and resume workflows
at defined points.

Why this decision needs to be made now:
Now that the framework is chosen, we need to define the rules
Betsy uses to decide when to act alone and when to stop and
ask Jenny. Without these rules, either Betsy asks for approval
on everything (useless) or it acts on everything without
oversight (unsafe). The exact conditions that trigger a pause,
and the specific thresholds used, must be designed with
justification — not guessed.

Where this fits:
DL1 confirmed the framework can pause. DL2 defines exactly
when it should pause, at what threshold, and why those
thresholds are the right ones for Jenny's business. DL3
(architecture) will then wire these gates into the workflow
nodes at the correct positions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

Where is the right boundary between what Betsy should decide
on its own and what must stop for Jenny to review — and what
specific thresholds make that boundary defensible to a
stakeholder who will trust the system with real purchasing
decisions?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[ ] Analysing   [X] Advising   [ ] Designing
[ ] Realising   [ ] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
Every gate must have a threshold that is justified by a
business rule, an industry standard, or a risk consequence —
not by what is technically convenient. "€300 because it
sounds reasonable" is not acceptable. "€300 because it sits
within the tail-spend boundary recognised in procurement
practice, where purchases below this level do not require
management sign-off" is acceptable.

Criterion 2:
The gate system must minimise unnecessary interruptions to
Jenny. An agent that fires a gate on every order is not
useful. The target is that Jenny reviews fewer than 5% of
all orders — the rest are handled autonomously. This is
measured by running the system against the real inventory
data and counting how many orders would have triggered a gate.

Criterion 3:
Every risk scenario that could cause financial harm or a
compliance violation must have a gate assigned to it. After
mapping all the ways an autonomous agent could make a bad
procurement decision, every scenario on that list must be
covered by a gate. No uncovered risk scenarios are acceptable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

Six gates were designed (G1–G6) with explicit thresholds
and justifications, covering every identified risk scenario.
Four gates pause the workflow completely for Jenny's approval
(HITL). One gate acts and notifies without pausing (HOTL).
One gate halts without an order and notifies (HOTL).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Library + Field:
I used the Library strategy to research what existing
procurement practice, AI safety literature, and autonomous
agent design frameworks say about where to draw the
human-oversight boundary. I researched tail-spend thresholds
in procurement, standard price escalation policies, and
invoice fraud patterns. I then used the Field strategy to
map this research to Jenny's actual context — which decisions
in her specific situation genuinely require her judgment, and
which follow a rule that Betsy can apply reliably.

What I found:

From the Library research:
Tail-spend management in procurement defines a threshold
below which purchases do not require management approval.
For small manufacturing businesses, this is typically in the
€200–€500 range for consumable parts. Below the threshold,
the cost of the approval process (Jenny's time) exceeds the
financial risk of the purchase itself.

Price spike detection in procurement systems typically flags
increases above 10–20% compared to the previous price.
Below 10%, fluctuations are routine commodity market
movement. Above 15–20%, the increase is unusual enough to
warrant checking — it may indicate supply chain disruption,
a pricing error, or opportunistic inflation.

Invoice fraud research identifies duplicate invoice
submission and amount inflation as the two most common
payment integrity failures in accounts payable. Zero-
tolerance policies (flag any discrepancy, regardless of
size) are standard in organisations that have experienced
payment fraud.

Stale data in automated systems is a data quality risk.
If Betsy is making decisions based on inventory numbers that
are hours or days out of date, it may order parts that are
already ordered, or miss parts that have just run out.

From the Field mapping to Jenny's context:
Jenny's two biggest fears about handing control to an
autonomous agent are: (1) it places a large order she would
not have approved, and (2) it pays an invoice that is wrong
or fraudulent. These map directly to the financial exposure
gates (G1 — high-value order) and the invoice integrity
gates (G4, G5).

The situations where Jenny always wants to be the one
deciding are: any order above the tail-spend boundary, any
supplier that is not on the approved list, any unusual price
change, any invoice that does not match what was agreed.
These map to G1, G2, G3, G4, G5.

The situations where Jenny is happy for Betsy to act and
just tell her afterwards: routine consumable orders below
€300 from approved suppliers at consistent prices. These
are Full Autonomy — no gate fires.

Stale data (G6) is a special case: Betsy cannot make a
good decision on old data, but the stale data is not itself
a financial risk. The right response is to stop the cycle
and notify Jenny, not to pause and wait for her input.

Evidence:
A risk mapping table listing every way an autonomous
procurement agent could make a bad decision, with the gate
assigned to each risk and the threshold used. Produced by
working through the business case scenarios and the
literature findings together.

A gate test showing all six gates firing from real data in
the inventory and supplier CSV files — each gate triggered
by the exact condition it is designed to catch.

![G1 (spend €9,880 > €300), G2 (unapproved supplier FastParts GmbH), G3 (ViennaMach +26.7% spike) — WHAT/WHY/NEXT for each](<../image evidence/test_gate(1).png>)

![G4 (invoice €6,200 vs PO €5,775, diff €425), G5 (duplicate INV-2025-006 = INV-2025-001), G6 (data 8959h old) — WHAT/WHY/NEXT](<../image evidence/test_gate(2).png>)

Gate reasoning log — the G5 duplicate invoice entry
showing the exact data the gate acted on (same supplier,
same PO, same amount), the DL2 rule applied, and the
action taken (payment held, workflow paused).

![G5 duplicate invoice — WHAT/WHY/NEXT reasoning log entry in full, no-fire case confirmed below](<../image evidence/reasoning log entry.png>)

What this means:
The six gates cover every identified risk scenario. The
thresholds are defensible: €300 is the tail-spend boundary,
15% is a standard escalation threshold, zero tolerance on
invoices reflects fraud prevention practice, 4 hours matches
the monitoring cycle interval. None of the thresholds were
chosen arbitrarily.

The split between HITL (pause completely) and HOTL (act and
notify) follows a single principle: if the wrong autonomous
action cannot be reversed easily, the gate must pause. If
Betsy can act safely and Jenny can override within an hour
if she disagrees, HOTL is appropriate.

So I decided:
Because the risk mapping showed six distinct risk scenarios
requiring coverage, and because the library research
provided defensible thresholds for each, the six-gate design
with the specific thresholds listed below is the right
recommendation for a procurement agent operating in Jenny's
context.

Gate summary:

G1 — Order value above €300 (HITL)
Any order where the total cost exceeds €300 requires Jenny's
approval before the order is placed. This sits within the
tail-spend boundary for small manufacturing businesses.
Below this level, the cost of Jenny's review time exceeds
the financial risk. Above it, the financial commitment is
large enough to warrant her judgment.

G2 — No approved supplier available (HITL)
If no approved supplier is available for a part that needs
ordering, Betsy cannot proceed. Using an unapproved supplier
would be a compliance violation. The graph pauses completely
and Jenny must resolve the supplier list before anything
can continue.

G3 — Price more than 15% above the last recorded price (HITL)
If the current unit price from any supplier is more than 15%
higher than the price recorded on the most recent order for
that part, Betsy pauses. A spike of this size could indicate
a pricing error, supply chain disruption, or opportunistic
inflation — all of which require Jenny's judgment.

G4 — Invoice amount does not match the purchase order total (HITL)
If the invoice received from a supplier does not match the
purchase order total exactly, payment is held and Jenny is
notified. Zero-tolerance policy: even a small discrepancy
must be investigated. Invoice overbilling often starts with
small, easily overlooked amounts.

G5 — Duplicate invoice detected (HITL)
If an invoice with the same identifier has already been
recorded in the system, payment is blocked completely. This
is the primary defence against duplicate payment fraud, one
of the most common accounts payable failures.

G6 — Inventory data more than 4 hours old (HOTL)
If the inventory file has not been updated within the last
4 hours, Betsy halts the ordering cycle and notifies Jenny.
It does not pause and wait for approval — there is nothing
for Jenny to approve. The problem is with the data feed, not
with a specific order. The next scheduled cycle will check
again.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — Every gate threshold is justified by a
source: €300 from tail-spend practice, 15% from standard
price escalation policy, zero tolerance from invoice fraud
prevention research, 4 hours from the monitoring cycle
interval. None were chosen arbitrarily.

Criterion 2: ✅ — Running the system against the real
inventory data showed that the majority of routine orders
do not trigger any gate. Only high-value orders (above €300),
price spikes, or invoice discrepancies fire a gate. The
estimated rate of routine autonomous orders versus escalated
ones sits well above the 95% autonomy target.

Criterion 3: ✅ — Working through the risk mapping exercise
produced a list of six risk scenarios. All six are covered
by a gate. No uncovered scenarios were identified after
applying the Library research on procurement risks.

Assumptions I am making:
The €300 tail-spend boundary is appropriate for a small
manufacturing business in this context. A larger organisation
or a different industry might require a different threshold.
If the business grows, this number should be revisited.

The 15% price spike threshold assumes that the previous
recorded price is a reliable baseline. If a supplier had
an unusually low price on the last order (a promotional
price, for example), a return to the normal price might
trigger G3 incorrectly. This is an acceptable false positive
— it is better to ask Jenny than to silently accept a
large price increase.

What surprised me:
The most interesting finding was that HITL and HOTL are not
just two options on a scale from "more oversight" to "less
oversight." They represent fundamentally different answers
to the question "what is the right action when a risk
condition is detected?" For stale data, the right action is
to stop and notify — there is nothing to approve. For a
high-value order, the right action is to pause and wait —
the order cannot be placed without a human decision. This
distinction had to be worked out scenario by scenario, not
applied as a blanket rule.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:
Risk Analysis and the approach for agent.docx — the early
risk analysis produced before the gate thresholds were
fixed. This document records the Library and Field phase
thinking: mapping procurement risks to categories, reviewing
tail-spend and invoice fraud research, and identifying which
scenarios required a human decision versus which could be
handled automatically. It predates the gate implementation
and shows the risk reasoning that the gate design formalised.

Risk mapping table — every identified procurement risk
scenario, the gate assigned to it, the threshold, and the
HITL/HOTL classification with the reasoning for each.

Gate trigger test output — all six gates firing from real
data, confirming that the conditions and thresholds work
as designed. Each gate fires from the specific data scenario
it was built to catch.
Produced by: python test_gates.py

Code — gate implementation:
test_gates.py — runs each gate condition in isolation
against the real CSV data and confirms each one fires (and
does not fire when the threshold is not met).
betsy/nodes.py — the gate checks live inside decide_node
(G1, G3), evaluate_node (G2), monitor_node (G6), and
verify_node (G4, G5). Each check is a Python comparison —
no LLM involvement in the gate logic.
betsy/graph.py — the routing functions (_after_decide,
_after_evaluate, _after_monitor, _after_verify) that read
the gate field from state and direct the graph to
human_approval_node or continue.

Next LO stage: Moving to Designing

What I can now do that I could not before:
I can now place each gate at the correct point in the
workflow graph (DL3). The gate conditions are precise enough
to be coded directly — no further interpretation is needed.
The HITL/HOTL classification tells the architecture exactly
what each gate needs to do: pause the graph completely, or
notify and halt without pausing.

How I will know this worked:
When the system runs against the demo scenarios — a high-
value order, a price spike, an invoice mismatch — each gate
must fire correctly and behave as designed. G1 should pause
and wait; G3 should pause and wait; G6 should notify and
stop without pausing. If any gate fires at the wrong time
or behaves differently from its classification, the design
needs to be revisited.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ETHICS AND RESPONSIBILITY
─────────────────────────

The assignment brief specifically requires documenting what
could go wrong with an autonomous agent and how those risks
are mitigated. This section addresses that requirement.

What could go wrong:

1. Betsy places an order Jenny would not have approved.
   Mitigation: G1 (€300 threshold) and G3 (price spike)
   catch the most likely causes. Any order above €300 is
   paused. Any unusual price change is paused. The residual
   risk is a correctly-priced order below €300 for a part
   Jenny would have questioned — acceptable, because Jenny
   can see every autonomous order in the dashboard and audit
   log immediately after it is placed.

2. Betsy pays a fraudulent or incorrect invoice.
   Mitigation: G4 and G5 catch amount mismatches and
   duplicate invoices. Payment is blocked completely until
   Jenny investigates. Zero-tolerance policy means no
   discrepancy is too small to flag.

3. Betsy makes a decision on outdated inventory data.
   Mitigation: G6 checks data freshness before every cycle.
   If the data is more than 4 hours old, no orders are
   placed. The stale data is flagged to Jenny.

4. Betsy selects a supplier unfairly or inconsistently.
   Mitigation: The SAW scoring formula uses the same weights
   and criteria for every supplier on every run. The formula
   is transparent and documented. Every selection is logged
   with the scores and the reasoning text. Jenny can inspect
   any decision in the audit log.

5. Betsy's reasoning cannot be understood by a human.
   Mitigation: Every node writes a WHAT/WHY/NEXT entry to
   the audit log in plain language. The reasoning is not
   stored as model weights or probabilities — it is written
   out in sentences that any member of the procurement team
   can read.

6. Betsy acts during a system failure or data corruption.
   Mitigation: G6 catches stale data. LangGraph's checkpoint
   system means a partial run does not leave the system in
   an unknown state — the graph can be resumed or inspected
   at the last checkpoint.

What cannot be fully mitigated in the current prototype:
Real-time supplier API connection and live inventory system
integration are out of scope. The current system reads from
CSV files, which means a data entry error in the CSV will
propagate into Betsy's decisions. This is a known limitation
of the prototype scope and should be the first thing
addressed before any production deployment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
