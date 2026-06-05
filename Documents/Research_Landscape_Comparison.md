# Research Landscape Comparison
## Real-World Autonomous Agent Deployments vs Betsy

This document is LO1 (Analysing) Library evidence — it shows the investigation
of the broader autonomous agent landscape before designing the solution.

---

## Why This Comparison Matters

Before designing Betsy, the question was not "can an AI agent do procurement?"
but "what do production autonomous agents actually do, where do they succeed,
and what makes them trustworthy in a real business environment?" This comparison
maps three real deployments against what Betsy is designed to do.

---

## Comparison Table

| Dimension | Klarna AI Agent | Genentech Research Agent | Pets at Home Fraud Monitor | Betsy (this project) |
|---|---|---|---|---|
| **Domain** | Customer service — refunds, returns, account queries | Biomarker research — literature search and synthesis | Payment fraud — transaction anomaly detection | Procurement — inventory monitoring, supplier selection, invoice verification |
| **What it does autonomously** | Resolves 2/3 of customer chats without human involvement. Handles refund requests, order status, account changes. | Searches biomedical literature, extracts relevant findings, synthesises research questions autonomously. | Monitors transactions in real time, flags anomalies, blocks suspicious payments automatically. | Monitors inventory every 4 hours, scores suppliers, places orders under €300, verifies invoices. |
| **When it involves a human** | Escalates to a human agent when sentiment is negative, issue is complex, or customer requests it. | Flags low-confidence findings for researcher review. Does not publish conclusions autonomously. | Flags high-risk transactions for human review before blocking; some blocks are automatic for clear patterns. | HITL interrupt on 5 conditions: order > €300, no approved supplier, price spike > 15%, invoice mismatch, duplicate invoice. |
| **Transparency mechanism** | Conversation log available. Klarna publishes aggregate metrics on resolution rates. | Research findings are traceable to source documents. No black-box conclusions. | Anomaly scores logged with contributing factors visible to fraud analysts. | WHAT/WHY/NEXT audit log for every node in every cycle. Every autonomous decision has a plain-language explanation. |
| **What it replaced** | 700 full-time equivalent customer service agents (Klarna stated publicly). | Manual literature review taking weeks per research question. | Manual fraud review team — reduced false positive review time significantly. | 30+ hours/week of manual procurement tasks by the operations manager. |
| **Known risk or limitation** | Accuracy dropped in some languages; some customers reported worse experience than human agents. Legal and regulatory questions about AI-handled financial decisions remain open. | Research synthesis may miss nuance or context that experienced researchers catch. Relies on quality of source data. | False positives block legitimate transactions; threshold tuning is ongoing. Adversarial fraud patterns evolve. | CSV-based data feed (not live ERP integration). Static seeded data for prototype; real deployment needs live inventory and supplier APIs. |
| **Autonomy level** | High — resolves most cases without human review. | Medium — synthesises autonomously but conclusions reviewed before use. | High for low-risk patterns; Medium for high-risk (human review required). | Calibrated — full autonomy for routine orders, mandatory human approval for 5 risk conditions. |

---

## What This Tells Us About Betsy's Design

**The production systems confirm three things:**

1. **Autonomy without oversight is not production-ready.** Every system in this comparison has a mechanism for escalating to humans — not as a fallback for failures, but as a designed feature for cases where autonomous action creates unacceptable risk. Betsy's six gates are not a limitation; they are the mechanism that makes the system trustworthy.

2. **Transparency is non-negotiable.** All three production systems maintain audit trails and explanations. Klarna publishes aggregate data. Genentech traces findings to sources. Pets at Home logs anomaly scores. Betsy's WHAT/WHY/NEXT audit log was not an optional feature — it was a design requirement informed by seeing how real systems handle accountability.

3. **Scope discipline matters.** Every production system has a clearly bounded task. Klarna handles service queries, not account closures. Genentech synthesises, not publishes. Betsy monitors and orders, not negotiates contracts or changes supplier relationships. The boundary of what the agent is trusted to do is as important as what it does.

**Where Betsy is different from these examples:**

Betsy operates at a smaller scale (one manufacturing company vs enterprise deployments) and uses a local LLM rather than a cloud model. This means no data leaves the machine — a privacy requirement for commercially sensitive supplier pricing data. The trade-off is that the local model is less capable on complex reasoning, which is why the LLM is used only for supplier selection confirmation and reasoning text, with all arithmetic handled by Python.

---

## Sources Used

- Klarna AI agent announcement (February 2024) — Klarna press release on autonomous customer service agent performance
- Genentech AI research agent — published case study on autonomous biomarker research synthesis
- Pets at Home fraud prevention — referenced in the course assignment brief as a production autonomous monitoring system
- Assignment brief — "Autonomous agents are already in production at major companies... These aren't experiments — they're production systems making real decisions with real consequences."

---

*Research Landscape Comparison — Betsy Autonomous Procurement Agent — LO1 Analysing*
*GenAI Semester 2026*
