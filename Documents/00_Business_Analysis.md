# Stage 0 — Business Analysis
## Betsy: Autonomous Procurement Agent
### Precision Manufacturing Co. — Pre-Project Context

---

## 1. Business Case

### 1.1 Who Is This For?

**Organisation:** Precision Manufacturing Co. — a small-to-medium manufacturing business producing precision mechanical components. The company runs two active assembly lines and depends on a reliable supply of spare parts and consumable materials to avoid production stoppages.

**Primary user:** Jenny, Operations Manager. Jenny is responsible for procurement, supplier relationships, inventory oversight, and production support. She has no dedicated procurement team — all purchasing decisions flow through her.

### 1.2 The Problem Jenny Has Right Now

Jenny spends more than 30 hours every week on procurement tasks that do not require her expertise. These are not strategic decisions — they are repetitive, rule-bound, reactive tasks that consume the majority of her working week.

**What she does manually today:**

- Checks inventory levels by opening a spreadsheet — typically once or twice a week, not in real time
- Notices a shortage only when a production engineer flags it, often too late to avoid disruption
- Looks up supplier contacts from memory or a saved email thread — no structured comparison
- Sends enquiry emails or makes phone calls to get quotes — no standard format, no audit trail
- Picks a supplier based on familiarity and gut feel — no scoring, no documented rationale
- Writes purchase orders manually and emails them to suppliers
- Follows up on delivery by emailing or calling the supplier
- Receives invoices by email, opens the original PO, compares numbers manually
- Approves payment if the numbers match — flags a discrepancy if not, and chases the supplier
- Discovers budget overruns at the end of the month, after the damage is done

**The consequences:**

| Problem | Real-world impact |
|---|---|
| Reactive inventory monitoring | Stockouts happen because the shortage is noticed too late |
| No structured supplier scoring | Cheaper, less reliable suppliers get chosen over better ones |
| Manual PO creation | Errors, delays, no consistency |
| Ad-hoc invoice matching | Duplicate invoices and overbilling slip through |
| No audit trail | Cannot explain why a supplier was chosen — accountability gap |
| Time trapped in operations | Strategic work (supplier relationships, cost negotiation, process improvement) never gets done |

**The financial cost of the current process:**

- Jenny's operational procurement time: 30+ hours/week × approximately €35/hour = **over €1,000/week in labour cost** for tasks that are largely automatable
- One production line stoppage from a preventable stockout: estimated **€15,000 in lost productivity**
- Duplicate invoice payments that slipped through before Betsy: **3 in 8 weeks** — each one requiring manual recovery

### 1.3 Why Automation, and Why Now

The volume of routine procurement tasks is growing as the company scales. Jenny cannot take on a procurement assistant without a business case. The tasks themselves are rule-bound — they follow a consistent pattern: check stock, score suppliers, place order, verify invoice. This pattern is exactly the type of work that an autonomous AI agent can handle reliably.

The key insight from researching autonomous procurement systems is that the right split is not "automate everything" or "automate nothing." It is: **automate the routine, escalate the exceptional.** Jenny should only see decisions that genuinely require her judgment — high-value orders, unusual price changes, invoice discrepancies.

### 1.4 What Success Looks Like

A successful implementation of Betsy means:

- **80% of routine procurement tasks are handled autonomously** — Jenny reviews and approves rather than initiates and executes
- **Zero stockouts caused by procurement delay** — Betsy detects upcoming shortages before they become crises
- **100% of invoice discrepancies are caught before payment** — no more duplicate payments or overbilling slipping through
- **Full audit trail on every decision** — every autonomous action is logged with a plain-language explanation of what was done and why
- **Jenny's operational procurement time falls below 10 hours/week** — the rest goes to strategic supplier management and process improvement

---

## 2. As-Is BPM — The Current Manual Procurement Process

This is how procurement works at Precision Manufacturing Co. today, before Betsy.

### 2.1 Process Flow: Manual Procurement (As-Is)

```
TRIGGER: Engineer notices a part is low or missing
           ↓
Jenny opens inventory spreadsheet
(manually maintained, updated irregularly)
           ↓
Jenny identifies which part needs ordering
(reactive — often already too late for standard delivery)
           ↓
Jenny looks up supplier options
(memory, saved emails, no structured list)
           ↓
Jenny contacts 1–3 suppliers for quotes
(email or phone — no standard format, no SLA for response)
           ↓
Jenny compares quotes manually
(price only — reliability and delivery not scored)
           ↓
Jenny selects a supplier
(gut feel and familiarity — no documented rationale)
           ↓
Jenny creates purchase order manually
(Word/Excel template, emailed to supplier)
           ↓
Jenny waits for order confirmation from supplier
(no automatic tracking)
           ↓
Supplier delivers (or doesn't)
           ↓
Jenny chases if delivery is late
(manual email/phone — no scheduled follow-up)
           ↓
Invoice arrives by email
           ↓
Jenny manually matches invoice to original PO
(opens both, compares numbers by eye)
           ↓
Match: Jenny approves payment
No match: Jenny disputes with supplier manually
           ↓
Finance processes payment
(end of month — overruns discovered here)
```

### 2.2 Pain Points in the As-Is Process

| Stage | Pain point | Type |
|---|---|---|
| Inventory check | Reactive — triggered by a problem, not a schedule | Risk |
| Supplier lookup | No structured list, no scoring | Quality |
| Quote comparison | Price only, no reliability weighting | Quality |
| Supplier selection | Not documented — no accountability | Compliance |
| PO creation | Manual, error-prone, no template enforcement | Efficiency |
| Delivery tracking | Manual follow-up only when Jenny remembers | Risk |
| Invoice matching | Manual, error-prone — duplicates slip through | Financial risk |
| Budget visibility | End-of-month discovery of overruns | Financial risk |
| Audit trail | None | Compliance |

### 2.3 Time Breakdown (Estimated Weekly Hours)

| Activity | Hours/week |
|---|---|
| Inventory spreadsheet checks | 3–4 hours |
| Supplier research and quoting | 5–6 hours |
| PO creation and sending | 4–5 hours |
| Delivery follow-up | 3–4 hours |
| Invoice matching and approval | 5–6 hours |
| Chasing discrepancies and disputes | 3–4 hours |
| Ad-hoc urgent procurement (crises) | 5–8 hours |
| **Total** | **28–37 hours** |

Jenny's working week is largely consumed by these tasks. Strategic work — supplier relationship development, cost negotiation, quality reviews — happens only when there is capacity left, which is rarely.

---

## 3. To-Be BPM — The Procurement Process With Betsy

This is how procurement works after Betsy is implemented.

### 3.1 Process Flow: Autonomous Procurement (To-Be)

```
TRIGGER: APScheduler fires every 4 hours (automated)
           ↓
MONITOR NODE
Betsy reads inventory.csv
Identifies parts below reorder threshold
Checks data freshness (G6: if data > 4 hours old → HOTL alert, halt)
           ↓
EVALUATE NODE
Betsy scores all approved suppliers using SAW formula:
  score = (reliability × 0.40) + (price_score × 0.35) + (delivery_score × 0.25)
If no approved supplier exists → G2 fires (HITL: Jenny must resolve)
           ↓
DECIDE NODE
LLM confirms highest-scored supplier
Calculates order quantity and total value

  ┌─ If order value > €300 → G1 fires (HITL: Jenny must approve)
  ├─ If price spike > 15% → G3 fires (HITL: Jenny must confirm)
  └─ If all clear → continue autonomously
           ↓
ORDER NODE (routine orders only — all gates clear)
Betsy writes purchase order to database
Sends HOTL notification to Jenny:
"Order placed for [part] from [supplier]. Total: €[amount]. No action needed."
           ↓
TRACK NODE
Betsy checks open POs against expected delivery dates
If overdue → HOTL alert: "Delivery from [supplier] is X days late."
           ↓
VERIFY NODE
Betsy matches incoming invoice against PO total

  ┌─ If invoice ≠ PO total → G4 fires (HITL: payment held)
  ├─ If duplicate invoice detected → G5 fires (HITL: payment blocked)
  └─ If match → HOTL notification: "Invoice verified. Payment can proceed."
           ↓
END OF CYCLE
All decisions logged with WHAT/WHY/NEXT in audit log
Next cycle fires in 4 hours
```

### 3.2 Jenny's New Role With Betsy

| What Jenny no longer does | What Jenny does instead |
|---|---|
| Manual inventory checks | Reviews Betsy's dashboard for system health (5 min/day) |
| Supplier research and quoting | Strategic supplier relationship management |
| Routine PO creation | Approves only flagged high-value or risk orders (est. 2–3/week) |
| Manual delivery follow-up | Receives HOTL alerts only when something is actually overdue |
| Manual invoice matching | Reviews HITL alerts for genuine discrepancies only |
| Chasing overruns at month end | Reviews audit log — full decision trail is always available |

**Estimated time reduction:**

| Activity | As-Is | To-Be |
|---|---|---|
| Inventory monitoring | 3–4 hours/week | 0 (automated) |
| Routine PO creation | 4–5 hours/week | 0 (automated) |
| Delivery follow-up | 3–4 hours/week | <1 hour (alerts only) |
| Invoice matching | 5–6 hours/week | <1 hour (exceptions only) |
| Supplier selection research | 5–6 hours/week | 0 (automated with scoring) |
| Exception handling (approvals) | — | 2–3 hours/week |
| Dashboard monitoring | — | 0.5 hours/week |
| **Total** | **28–37 hours** | **~4 hours** |

### 3.3 Human Oversight Model

Betsy uses three levels of human involvement depending on the risk of the decision:

| Level | Name | When | Jenny's role |
|---|---|---|---|
| Full Autonomy | No gate fires | Routine, low-value, approved supplier, no price change | Notified only — no action needed |
| HOTL | Human-on-the-Loop | Action taken, notification sent | Can override within 1 hour if she disagrees |
| HITL | Human-in-the-Loop | Gate fires — graph pauses completely | Must approve or reject before anything proceeds |

This model ensures Jenny is never surprised by a large financial commitment, but is not burdened by approving routine €50 consumable orders.

---

## 4. GAP Analysis

### 4.1 What Is This?

The GAP analysis maps the difference between what exists today (the as-is state) and what is required for Betsy to operate effectively (the to-be state). It identifies what needs to be built, configured, or changed for the to-be process to work.

### 4.2 Data and Infrastructure Gaps

| Area | Current State | Required for Betsy | Gap | Status in Betsy |
|---|---|---|---|---|
| Inventory data | Manual spreadsheet, updated irregularly | `inventory.csv` updated on a schedule — data must be ≤4 hours old (G6) | Requires a reliable data feed into the CSV | Simulated with static CSV — **real integration not built** |
| Supplier master data | Ad-hoc email contacts, no scoring fields | `suppliers.csv` with price, delivery days, reliability score, approval status per part | Structured supplier data must be created and maintained | Built and seeded with 20 suppliers |
| Purchase order history | Paper/email trail, no queryable format | SQLite `purchase_orders` table with gate, status, and amount fields | Historical PO data must be migrated and kept current | Built — 17 historical POs seeded |
| Invoice data | Paper/email invoices | `invoices.csv` or SQLite `invoices` table for Betsy to match against | Invoices must be captured in structured format before payment | Built — 18 invoices seeded including test discrepancies |
| Audit trail | None | `audit_log` table with WHAT/WHY/NEXT entries per run | New — did not exist before | Built into every node |

### 4.3 Process Gaps

| Process | As-Is | Required | Gap | Status in Betsy |
|---|---|---|---|---|
| Inventory monitoring | Reactive, manual | Proactive, scheduled every 4 hours | Automated scheduling needed | APScheduler built |
| Supplier scoring | None (gut feel) | SAW formula: reliability × 0.40 + price × 0.35 + delivery × 0.25 | Scoring formula and data fields required | Built in evaluate_node |
| Supplier selection | Undocumented | LLM-assisted, highest SAW score, reasoning logged | LLM integration needed | Built using llama3.2:3b via Ollama |
| Order approval escalation | Jenny approves everything | Only orders above €300 or with price spikes escalated | Gate system needed | G1, G3 built |
| Invoice verification | Manual eye-check | Automated match against PO, zero-tolerance discrepancy policy | Automated verification needed | G4, G5 built |
| Delivery tracking | Manual follow-up | Automated overdue check with HOTL alert | Automated tracking needed | Built in track_delivery_node |

### 4.4 Capability Gaps (What the Assignment Requires That Betsy Does Not Yet Have)

These are gaps between what the assignment brief asks for and what the current Betsy implementation delivers.

| Required Capability | Assignment Requirement | Current Betsy | Gap |
|---|---|---|---|
| Learning from past decisions | "Learn from past decisions to improve supplier scoring over time" | SAW formula uses static reliability scores from suppliers.csv — scores do not update based on delivery history | **Dynamic reliability scoring not built.** Betsy stores delivery outcomes in the PO database but does not feed them back into the reliability score for the next cycle. |
| Memory of supplier pricing trends | "Memory to track supplier history and pricing trends" | Price comparison happens per cycle only — no trending or historical price tracking | **Price trend memory not built.** The G3 spike check compares current vs previous price but does not maintain a price history table. |
| Real system integration | "Tool integration with inventory systems, email, and supplier APIs" | Reads from CSV files — no live system connections | **CSV-based only.** Real ERP/inventory system integration is out of scope for this prototype but is a known limitation. |
| Demonstrate 95%+ approval rate | "Maintains a 95%+ human approval rate on autonomous purchasing decisions" | Gates designed to minimise unnecessary escalation but no rate measurement built | **Approval rate not tracked or reported.** Dashboard shows gate history but does not calculate the approval rate as a KPI. |

### 4.5 What Needs to Be Rebuilt or Added

Based on the GAP analysis, the following additions would close the gaps between the current prototype and a production-ready system:

**Priority 1 — Close assignment requirement gaps (needed for portfolio completeness):**

1. **Dynamic reliability scoring** — After each delivery, the actual delivery outcome (on time / late / cancelled) should update the supplier's reliability score in the database. The SAW formula then uses the updated score on the next cycle. This closes the "learning from past decisions" requirement.

2. **Approval rate KPI** — Add a metric to the dashboard showing what percentage of Betsy's autonomous decisions were executed without a gate firing. Target: 95%+. This directly demonstrates the assignment success criterion.

3. **Price history table** — Store the unit price recorded each cycle per supplier in a `price_history` table. The G3 spike check then compares current price against the rolling average of the last 3 recorded prices, not just the previous single price. This closes the "pricing trends" memory requirement.

**Priority 2 — Strengthen the existing implementation:**

4. **Supplier selection fallback** — If the LLM returns invalid JSON, the current code falls back to the highest SAW score by Python. This fallback should be logged explicitly in the reasoning log so the audit trail is honest about when the LLM was not used.

5. **Stale data handling** — When G6 fires (data too old), Betsy currently halts and notifies. It should also log the data age and the timestamp of the last valid read in the audit log, so there is a traceable record of data quality issues.

---

## 5. Summary

| Document section | Key output |
|---|---|
| Business case | Jenny's 30+ hour/week problem, €1,000+/week cost, 3 duplicate payments in 8 weeks |
| As-Is BPM | 9-step manual process: reactive, undocumented, error-prone |
| To-Be BPM | Automated 4-hour cycle: HITL for exceptions, HOTL for notifications, full audit log |
| GAP analysis | 3 priority gaps to close: dynamic reliability scoring, approval rate KPI, price history |

The current Betsy implementation is a working prototype that demonstrates the core architecture correctly. The three Priority 1 gaps are the difference between a proof-of-concept and a system that fully meets the assignment brief.

---

