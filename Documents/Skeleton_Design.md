# Skeleton Design — Original Workflow Architecture
## Betsy Autonomous Procurement Agent
### The core design as established before implementation began

---

## Purpose of This Document

This document records the original skeleton design of Betsy — the workflow structure, data schema, routing logic, and scoring formula as they were designed and validated before the full system was built. It is evidence for DL3 (LO3 Designing) showing that the architecture was deliberately planned and tested at the skeleton stage, not discovered through trial and error.

This design pre-dates the additions made during the managing phase (invoice-only routing, price history table, dynamic reliability scoring) which are documented in DL5 and DL6. The core 6-node structure, gate positions, and state schema described here remained unchanged throughout the project.

---

## 1. The Core Design Question

Before writing a single node, the central structural question had to be answered:

> How do you design a workflow where every step has exactly one responsibility, data flows cleanly from step to step, and the workflow can be frozen at any point and resumed from the exact same position after a human decision?

LangGraph's `StateGraph` answered this by providing:
- A shared state dictionary that every node reads from and writes to
- Conditional edges (routing functions) that decide which node runs next
- `interrupt()` — a built-in mechanism that freezes the graph at any node
- `SqliteSaver` — a checkpointer that saves the full graph state to a file so it survives process restarts

The design task was to define: what nodes, what state fields, what routing rules, and what gates.

---

## 2. The BetsyState Schema — Original Design

The state is a single TypedDict that all six nodes share. Every field was chosen for a specific purpose. Nothing was added speculatively.

```python
class BetsyState(TypedDict):

    # Run identity — links all audit log entries for one cycle
    run_id: str

    # ── Node 1: Monitor ──────────────────────────────────────────────
    inventory_snapshot: list    # all rows from inventory.csv
    low_stock_items:    list    # rows where current_stock < reorder_threshold
    data_age_hours:     float   # hours since inventory.csv was last updated

    # ── Node 2: Evaluate ─────────────────────────────────────────────
    candidate_suppliers: list   # approved suppliers, scored and ranked

    # ── Node 3: Decide (LLM) ─────────────────────────────────────────
    selected_supplier:  dict    # the chosen supplier record
    order_quantity:     int     # quantity to order (from reorder_quantity field)
    order_value:        float   # unit_price × order_quantity (Python, not LLM)
    decision:           str     # "order" | "skip" | "escalate"

    # ── Node 4: Order ────────────────────────────────────────────────
    purchase_order:     dict    # the PO record written to betsy.db

    # ── Node 6: Verify ───────────────────────────────────────────────
    invoice:             dict   # the invoice being checked
    verification_result: str    # "match" | "mismatch" | "duplicate" | "no_invoice"

    # ── Human oversight fields ────────────────────────────────────────
    gate:               str     # "G1"–"G6" or None
    gate_reason:        str     # plain-language explanation of why the gate fired
    escalation_payload: dict    # full context sent to human at the gate
    human_response:     str     # "approve" | "reject" — set when human decides

    # ── Audit trail ───────────────────────────────────────────────────
    reasoning_log: Annotated[list, add]   # all nodes append — never overwrite
```

**Key design decisions in the schema:**

**`reasoning_log: Annotated[list, add]`** — the most important structural choice. LangGraph's `add` reducer means every node appends its entries to a shared list. No node can overwrite another node's entries. After a full cycle, the log contains every WHAT/WHY/NEXT entry from every node in order, automatically. This was not achievable with message-passing frameworks (AutoGen, CrewAI) which only return the final output.

**`decision: str` with three values** — using a string enum rather than a boolean allows representing "pending" state. During an `interrupt()`, the graph is frozen with `decision = "escalate"`. This is how the workflow knows to wait for `human_response` before continuing. A boolean `approved/rejected` could not represent the in-between state.

**Separate `gate`, `gate_reason`, and `escalation_payload` fields** — these model the pause-and-resume lifecycle explicitly. When a gate fires, these three fields are written. When `interrupt()` suspends the graph, these fields are preserved in the checkpoint. When the graph resumes, `human_approval_node` reads them to construct the response.

**No inter-node message passing** — all nodes read from and write to the shared state dict. This was a deliberate choice over message-passing architectures. It makes the data flow explicit: any field set by Node 1 is available to Node 6 without any intermediate passing logic.

---

## 3. The Six-Node Graph — Original Topology

```
Entry point: monitor_node
                │
                ▼
         ┌─────────────┐
         │ monitor_node │  Reads inventory.csv
         │ (Node 1)    │  Finds low-stock parts
         │             │  Checks data freshness (G6)
         └──────┬──────┘
                │
         ┌──────▼──────────────────────────────┐
         │ Routing: _after_monitor              │
         │   G6 fired?           → human_approval│
         │   low_stock empty?    → END           │
         │   low_stock present?  → evaluate      │
         └──────┬──────────────────────────────-┘
                │
         ┌──────▼──────┐
         │evaluate_node│  Scores approved suppliers
         │ (Node 2)    │  SAW formula (Python only)
         │             │  Fires G2 if no approved supplier
         └──────┬──────┘
                │
         ┌──────▼──────────────────────────────┐
         │ Routing: _after_evaluate             │
         │   G2 fired?  → human_approval        │
         │   otherwise? → decide                │
         └──────┬───────────────────────────────┘
                │
         ┌──────▼──────┐
         │ decide_node  │  LLM selects top supplier
         │ (Node 3)    │  Calculates order total (Python)
         │             │  Checks G1 (spend) and G3 (price)
         └──────┬──────┘
                │
         ┌──────▼──────────────────────────────┐
         │ Routing: _after_decide               │
         │   G1 or G3 fired?  → human_approval  │
         │   decision="order"? → order           │
         │   otherwise?        → END             │
         └──────┬───────────────────────────────┘
                │
         ┌──────▼──────┐
         │  order_node  │  Creates PO record
         │ (Node 4)    │  Writes to betsy.db
         │             │  Sends HOTL notification
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │track_delivery│ Checks all open POs
         │ _node        │ against expected_by dates
         │ (Node 5)    │  Flags overdue as "delayed"
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │ verify_node  │  Reads pending invoice
         │ (Node 6)    │  Matches against PO total
         │             │  Checks G4 (mismatch) and G5 (duplicate)
         └──────┬──────┘
                │
         ┌──────▼──────────────────────────────┐
         │ Routing: _after_verify               │
         │   G4 or G5 fired?  → human_approval  │
         │   otherwise?        → END             │
         └─────────────────────────────────────-┘

         ┌─────────────────────────────────────┐
         │ human_approval_node                  │
         │                                     │
         │  interrupt(payload)                 │
         │  → graph freezes here               │
         │  → state saved to betsy_state.db    │
         │  → resumes when Command(resume=...) │
         │                                     │
         │  Routing: _after_human_approval      │
         │   G1/G2/G3 approved → order         │
         │   G4/G5 approved    → END           │
         │   any rejected      → END           │
         │   G6 acknowledged   → END           │
         └─────────────────────────────────────┘
```

**Why linear, not branching:** An early design considered a branching structure where Monitor could route to different evaluation paths based on urgency. This was discarded because it made gate placement ambiguous — if two paths converge at Order, which path's gate logic applies? The linear design makes gate responsibility unambiguous: each gate belongs to exactly one node.

**Why `human_approval_node` is a separate node:** An earlier approach put the `interrupt()` call inside `decide_node` and `verify_node` directly. This worked for simple cases but broke state management — the resuming Command couldn't cleanly route back to the correct next step because the interrupted node had already completed its other logic. Making `human_approval_node` a standalone node with a single responsibility (`interrupt()` → return `human_response`) gave clean routing and made the state explicit.

---

## 4. The Routing Functions — Gate Logic in Code

The routing decisions are pure Python functions — no LLM involvement. Each function takes the current state and returns the name of the next node.

```python
def _after_monitor(state: BetsyState) -> str:
    if state.get("gate") == "G6":
        return "human_approval"        # stale data — HOTL
    if not state.get("low_stock_items"):
        return END                     # nothing to order
    return "evaluate"

def _after_evaluate(state: BetsyState) -> str:
    if state.get("gate") == "G2":
        return "human_approval"        # no approved supplier
    return "decide"

def _after_decide(state: BetsyState) -> str:
    gate = state.get("gate")
    if gate in ("G1", "G3"):
        return "human_approval"        # spend or price spike
    if state.get("decision") == "order":
        return "order"
    return END

def _after_human_approval(state: BetsyState) -> str:
    approved = "approve" in (state.get("human_response") or "").lower()
    if not approved:
        return END
    gate = state.get("gate", "")
    if gate in ("G1", "G2", "G3"):
        return "order"                 # approved → place order
    if gate in ("G4", "G5", "G6"):
        return END                     # invoice/stale gates resolve here

def _after_verify(state: BetsyState) -> str:
    if state.get("gate") in ("G4", "G5"):
        return "human_approval"        # invoice problem
    return END
```

These functions are the design. They encode every branching decision in the system. Reading them answers: "under what conditions does the system ask a human?" The answer is fully explicit and testable.

---

## 5. The Supplier Scoring Formula — Original Design

The Simple Additive Weighting (SAW) formula from Fishburn (1967) was chosen because it is transparent, reproducible, and academically defensible. The weights reflect Dickson's (1966) finding that reliability, price, and delivery speed are the top three supplier selection criteria.

```
Final score = (reliability × 0.40) + (price_score × 0.35) + (delivery_score × 0.25)
```

Where each component is normalised to 0–100 relative to the candidate set for that order:

```python
price_score    = 100 - ((price - min_price) / price_range) × 100
delivery_score = 100 - ((delivery_hours - min_hours) / hours_range) × 100
reliability    = reliability_score (from database, 0–100 scale)
```

**Why normalise within the candidate set?** Absolute prices are meaningless without context. A price of €50 is cheap if competitors charge €80 and expensive if they charge €30. Normalising within the candidate set for each order means the score always reflects relative value, not absolute value.

**Why is this Python, not LLM?** The formula is deterministic — same inputs, same output, every run. LLMs introduce variance: the same prompt can produce different numerical outputs across runs. For a financial decision (which supplier to pay, what amount to commit), the calculation must be reproducible and auditable. The LLM receives the pre-computed scores and confirms the selection in plain language. It never touches the arithmetic.

---

## 6. The WHAT/WHY/NEXT Audit Log Format

Every node writes to `reasoning_log` using a structured format:

```
WHAT: [what the node observed or decided]
WHY:  [the rule or evidence that drove the action]
NEXT: [what was passed to the following step, or what gate fired]
```

This format was designed to be readable by procurement staff, not just developers. The test applied during design: can a non-technical member of the team read this entry and explain what Betsy did and why?

Example from Node 3 (Decide):
```
WHAT: Selected AccuParts Corp for 40 × PART-001 @ €247.0 = €9,880.00.
WHY:  AccuParts Corp had the highest SAW score (73.0) among 3 approved
      suppliers for PART-001. Reliability 88, price €247 (mid-range),
      delivery 2 days.
NEXT: Gate G1 triggered — order value €9,880.00 exceeds €300 approval
      threshold. Workflow paused for human approval.
```

Example from Node 6 (Verify):
```
WHAT: Verified invoice INV-TEST-001 — €6,200.00 against PO PO-2025-005.
      Result: mismatch.
WHY:  Gate G4 — invoice amount €6,200.00 does not match PO total
      €5,775.00 (difference €425.00).
NEXT: Gate G4 HITL interrupt — payment held until human reviews.
```

---

## 7. What the Skeleton Proof Confirmed

Before building the full system, a skeleton version was run against real inventory and supplier data. The skeleton proof (`run_dl3.py`) confirmed:

- Node 1 correctly identified 8 parts below reorder threshold from `inventory.csv`
- Node 2 scored the correct suppliers and returned the highest-scored candidate
- Node 3 called the LLM, received valid JSON, selected the highest-scored supplier, and calculated the order total in Python
- The G1 gate fired correctly when the order total exceeded €300
- `interrupt()` froze the graph at `human_approval_node`
- The state was preserved in `data/betsy_state.db`
- After sending the approval response, the graph resumed from the interrupted node
- All entries appeared in `reasoning_log` in the correct order

**This confirmed the design was correct before any production code was written.** The full implementation then followed the skeleton structure exactly — no redesign of the core architecture was needed. Only additions were made (invoice-only routing in DL6, price history table in DL6) — the original 6-node topology was unchanged.

---

*Skeleton Design Document — Betsy Autonomous Procurement Agent — GenAI Semester 2026*
*Referenced by: DL3_Architecture.md (section 5 and 7)*
