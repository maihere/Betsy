# Ethics and Responsibility
## Betsy Autonomous Procurement Agent

This document is the standalone ethics analysis required by the assignment brief:
"Your decision log must include a section on ethical safeguards — what could go
wrong with your agent, and how you've mitigated those risks."

It is referenced by DL2 and supports LO2 (Advising) and LO6 (Professional Standard).

---

## The Ethical Shift: From Responding to Initiating

Traditional AI tools respond when asked. Betsy initiates — it places orders,
holds payments, and flags suppliers without being prompted. This creates four
fundamental responsibilities that do not exist with passive tools:

**Transparency** — Can humans understand why Betsy made a specific decision?

**Accountability** — When something goes wrong, how do we trace what happened
and who is responsible?

**Fairness** — Does Betsy treat all suppliers consistently, or does it
systematically favour some over others in ways that are not visible?

**Safety** — What prevents Betsy from making a catastrophically bad decision
when no one is watching?

---

## Risk Register

### Risk 1 — Betsy places an order the operations manager would not have approved

**Likelihood:** Medium (routine orders are low-risk; edge cases exist)

**Impact:** Financial — order cannot be cancelled after supplier confirms

**Mitigation:**
- G1 (spend gate): any order above €300 is paused. The operations manager
  approves before anything is placed.
- G3 (price spike): any price increase above 15% over the rolling average is
  paused. Unusual prices are always reviewed.
- HOTL notification: even for autonomous orders (below €300, no spike), a
  notification is sent immediately. The operations manager has 1 hour to
  override before the order is confirmed with the supplier.

**Residual risk:** An order below €300 for a part the manager would have
questioned — for example, ordering a part that is already on order from a
different run. Betsy does not yet check for in-flight duplicate orders.
This is a known limitation for future improvement.

---

### Risk 2 — Betsy pays a fraudulent or incorrect invoice

**Likelihood:** Low-to-medium (duplicate invoices are a known common fraud vector)

**Impact:** Financial — payments that go through cannot always be recovered

**Mitigation:**
- G4 (invoice mismatch): any invoice where the amount does not match the
  purchase order total exactly is held. Zero-tolerance policy — even €1
  difference triggers a review.
- G5 (duplicate invoice): any invoice submitted with the same supplier, PO,
  and amount as an existing record is blocked. This is the primary defence
  against the most common form of accounts payable fraud.
- In the manual process, 3 duplicate payments slipped through in 8 weeks.
  With Betsy, zero duplicate payments have been approved in testing.

**Residual risk:** A supplier who submits an invoice with a slightly different
amount (for example, adding a small "handling fee" not in the original PO)
will trigger G4 correctly. However, a supplier who alters the PO reference
number would bypass the duplicate check. Invoice fraud is adversarial — the
checks protect against the most common patterns, not all possible patterns.

---

### Risk 3 — Betsy makes decisions based on outdated inventory data

**Likelihood:** Medium (the data feed depends on external updates)

**Impact:** Ordering parts that are already stocked, or missing genuine stockouts

**Mitigation:**
- G6 (stale data): if the inventory file has not been updated within 4 hours,
  Betsy halts the ordering cycle. No orders are placed on old data.
- The 4-hour threshold matches the monitoring interval — if data is older than
  one full cycle, the data pipeline has a problem that needs human attention.

**Residual risk:** The current implementation reads from a CSV file, not a live
ERP system. Any data that is entered incorrectly into the CSV (wrong stock count,
wrong part ID) will propagate into Betsy's decisions. Data quality at the source
is outside Betsy's control in the prototype.

---

### Risk 4 — Betsy selects suppliers unfairly or inconsistently

**Likelihood:** Low (formula is deterministic)

**Impact:** Suppliers disadvantaged without justification; procurement decisions
cannot be explained or defended

**Mitigation:**
- The SAW scoring formula is transparent and documented: reliability × 0.40,
  price × 0.35, delivery × 0.25. The same formula applies to every supplier
  on every run.
- All weights are justified in DL3 with references to Dickson (1966) supplier
  selection research.
- Every selection is logged in the audit trail with the full score breakdown
  visible. Any supplier or auditor can see exactly why one supplier was chosen
  over another.
- The LLM confirms the selection but does not change it — the formula result
  is the decision. The LLM only explains it in plain language.

**Residual risk:** The reliability score in the suppliers table is seeded from
the CSV and updated dynamically based on delivery outcomes. If the initial
seed data contains biased reliability scores (for example, a supplier was given
a low score based on historical issues that no longer apply), that bias persists
until the dynamic scoring corrects it over time.

---

### Risk 5 — Betsy's reasoning cannot be understood or challenged

**Likelihood:** Low (designed explicitly to be transparent)

**Impact:** Trust collapse — if the operations manager cannot understand or
verify a decision, she will stop trusting the system entirely

**Mitigation:**
- WHAT/WHY/NEXT format: every node writes a plain-language entry to the audit
  log. "WHAT: selected AccuParts Corp. WHY: highest SAW score (73.04) — good
  reliability (88) at a competitive price (€247). NEXT: order total €9,880
  exceeds €300 threshold, G1 gate fired."
- The audit log is visible on the dashboard Audit Log page at any time.
- The escalation payload sent to the operations manager at a gate includes
  Betsy's reasoning, the alternatives considered, and the exact condition
  that triggered the gate.

**Residual risk:** The reasoning text is generated by the LLM, which means
it can be fluent but imprecise. In one observed case, the reasoning said
"I prioritised overall value proposition" — accurate but vague. The formula
score is always shown alongside the text so the operations manager can verify
the reasoning against the numbers.

---

### Risk 6 — System failure during a HITL pause leaves an order in unknown state

**Likelihood:** Low (but consequence is high)

**Impact:** An order that is neither confirmed nor cancelled — unknown financial
commitment

**Mitigation:**
- LangGraph's SqliteSaver checkpointer writes the full graph state to disk
  at every node. If the process is killed while a gate is waiting for approval,
  the state is preserved.
- On restart, the graph can be resumed from the exact same point with the same
  context. The operations manager's decision (approve/reject) will pick up
  where it left off.
- The `betsy_notifications.log` file records all gate alerts as a permanent
  text record that survives restarts, so the operations manager always has
  a record of what was pending.

**Residual risk:** If the SQLite state database file is corrupted or deleted,
the paused state is lost. For a production deployment, a more robust checkpoint
store (PostgreSQL, cloud storage) would be required.

---

## Known Prototype Limitations

These are limitations of the current implementation that would need to be
addressed before any real deployment:

1. **CSV-based data** — inventory, suppliers, and invoices are read from files,
   not live systems. A real deployment requires integration with the ERP,
   supplier portals, and accounts payable system.

2. **No duplicate order check** — Betsy does not check whether a part already
   has an open purchase order before placing a new one. Two back-to-back runs
   could both order the same part.

3. **Local LLM only** — `llama3.2:3b` runs on the local machine. If Ollama is
   not running, the Decide node fails. A production system needs a fallback
   (pure Python top-score selection without LLM confirmation).

4. **Single-tenant** — the current implementation is designed for one company
   with one operations manager. Multi-tenant deployment would require
   per-company data isolation.

5. **No audit log retention policy** — the audit log grows indefinitely.
   A production system needs archival and retention management.

---

## Responsible Deployment Checklist

Before using Betsy in a real procurement environment:

- [ ] Replace CSV files with live system integration (ERP, supplier APIs)
- [ ] Test all 6 gates against real transaction volumes
- [ ] Review and agree the €300 spend threshold with the operations manager
- [ ] Train the operations manager on the approve/reject flow and the 1-hour override window
- [ ] Establish a review cadence (weekly or monthly) to check supplier reliability score trends
- [ ] Add duplicate-order detection before deploying autonomous ordering
- [ ] Document the escalation procedure for when Betsy is unavailable (e.g., Ollama not running)
- [ ] Agree data retention policy for the audit log

---

*Ethics and Responsibility — Betsy Autonomous Procurement Agent*
*LO2 Advising + LO6 Professional Standard evidence*
*GenAI Semester 2026*
