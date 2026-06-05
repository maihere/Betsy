"""
test_model_choice.py — Model comparison: llama3.2:3b vs gemma4:e4b
====================================================================
Tests both models on the exact task Betsy's decide_node runs:
  - Parse the supplier shortlist
  - Return valid JSON with selected_supplier_id and reasoning
  - Select the correct top-scored supplier

This output justifies the model choice recorded in the Design Document.

Usage:
    python test_model_choice.py
"""

import sys
import json
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

DIVIDER  = "=" * 62
DIVIDER2 = "-" * 62

# ── Test prompt (same as betsy/prompts.py decide_node task) ───────────────────

PROMPT = """You are Betsy, an autonomous procurement agent.

Select the best supplier for this order and explain your choice clearly.

ORDER:
- Part    : PART-017 (Viton Seal Kit 32mm)
- Quantity: 40 units

SCORED SUPPLIER SHORTLIST (higher final_score is better):
id | name | price | last_price | delivery_days | reliability | score
SUP-007 | ViennaMach GmbH | 95.0 | 75.0 | 2 | 92 | 91.2
SUP-008 | PolyParts AG | 60.0 | 58.0 | 4 | 42 | 36.8

TASK:
1. Pick the supplier with the highest final_score.
2. If a supplier has a significantly lower reliability score, acknowledge the trade-off.
3. Write 2 sentences explaining why you chose this supplier and noting any concern.

Respond in this exact JSON format:
{
  "selected_supplier_id": "SUP-001",
  "reasoning": "Two sentences explaining the choice and any concern."
}

Return only the JSON object, nothing else.
"""

CORRECT_SUPPLIER = "SUP-007"   # ViennaMach GmbH — highest score (91.2)

# ── Run one model and return results ──────────────────────────────────────────

def test_model(model_name: str, runs: int = 3) -> dict:
    llm = ChatOllama(model=model_name, format="json", temperature=0)

    results = []
    for i in range(runs):
        t0     = time.time()
        raw    = ""
        valid  = False
        correct = False
        reasoning = ""
        selected  = ""

        try:
            resp = llm.invoke([HumanMessage(content=PROMPT)])
            raw  = resp.content.strip()
            elapsed = round(time.time() - t0, 1)

            parsed    = json.loads(raw)
            valid     = True
            selected  = parsed.get("selected_supplier_id", "")
            reasoning = parsed.get("reasoning", "")
            correct   = (selected == CORRECT_SUPPLIER)

        except json.JSONDecodeError:
            elapsed = round(time.time() - t0, 1)
        except Exception as e:
            elapsed = round(time.time() - t0, 1)
            raw = f"ERROR: {e}"

        results.append({
            "run":       i + 1,
            "valid":     valid,
            "correct":   correct,
            "selected":  selected,
            "reasoning": reasoning,
            "time_s":    elapsed,
            "raw":       raw if not valid else "",
        })

    return results


# ── Display results ────────────────────────────────────────────────────────────

def show_results(model_name: str, results: list) -> dict:
    valid_count   = sum(1 for r in results if r["valid"])
    correct_count = sum(1 for r in results if r["correct"])
    avg_time      = round(sum(r["time_s"] for r in results) / len(results), 1)

    print(f"\n  Model: {model_name}")
    print(f"  {DIVIDER2}")
    print(f"  Valid JSON  : {valid_count}/{len(results)}")
    print(f"  Correct selection : {correct_count}/{len(results)}  "
          f"(expected {CORRECT_SUPPLIER} — ViennaMach GmbH)")
    print(f"  Avg response time : {avg_time}s")

    for r in results:
        status = "OK" if r["valid"] and r["correct"] else ("WRONG" if r["valid"] else "INVALID")
        print(f"\n  Run {r['run']}  [{status}]  {r['time_s']}s")
        if r["valid"]:
            print(f"    Selected  : {r['selected']}")
            print(f"    Reasoning : {r['reasoning'][:120]}{'...' if len(r['reasoning']) > 120 else ''}")
        else:
            print(f"    Raw output: {r['raw'][:200]}")

    return {
        "model":    model_name,
        "valid":    valid_count,
        "correct":  correct_count,
        "avg_time": avg_time,
        "total":    len(results),
    }


# ── Summary and decision ───────────────────────────────────────────────────────

def print_decision(summaries: list) -> None:
    print(f"\n{DIVIDER}")
    print("  MODEL COMPARISON SUMMARY")
    print(DIVIDER)
    print(f"  {'Model':<22} {'Valid JSON':>10} {'Correct':>8} {'Avg time':>10}")
    print(f"  {DIVIDER2}")
    for s in summaries:
        print(f"  {s['model']:<22} "
              f"{s['valid']}/{s['total']:>8} "
              f"{s['correct']}/{s['total']:>6} "
              f"{s['avg_time']:>9}s")

    print(f"\n{DIVIDER}")
    print("  DECISION RATIONALE")
    print(DIVIDER)

    best_valid   = max(summaries, key=lambda x: x["valid"])
    best_correct = max(summaries, key=lambda x: x["correct"])
    fastest      = min(summaries, key=lambda x: x["avg_time"])

    print(f"""
  Task: Betsy's decide_node sends a scored supplier table as JSON context
  and asks the model to output a single JSON object with:
    - selected_supplier_id  (must match highest final_score)
    - reasoning             (2-sentence plain English explanation)

  What matters for this task:
  1. JSON validity      — the node must parse the response without error
  2. Correct selection  — the top-scored supplier must be chosen
  3. Response time      — each monitoring run must complete in under 60s

  Best JSON validity  : {best_valid['model']}  ({best_valid['valid']}/{best_valid['total']})
  Best correct choice : {best_correct['model']}  ({best_correct['correct']}/{best_correct['total']})
  Fastest response    : {fastest['model']}  ({fastest['avg_time']}s avg)

  Context on model sizes:
    llama3.2:3b  — 3B parameters,  2.0 GB. Minimal compute, fast on CPU.
    gemma4:e4b   — 9.6 GB.         Larger, slower on CPU, better reasoning.

  Note: arithmetic (unit_price × quantity = total) is handled by pure Python
  in decide_node regardless of model — this was a deliberate design fix after
  the model returned wrong prices. The LLM only selects supplier + writes
  reasoning. This means the model size mainly affects reasoning quality and
  JSON format compliance, not numeric accuracy.
""")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    RUNS = 3

    print(f"\n{'BETSY — MODEL SELECTION TEST':^{len(DIVIDER)}}")
    print(DIVIDER)
    print(f"  Task: supplier selection JSON output ({RUNS} runs each)")
    print(f"  Correct answer: {CORRECT_SUPPLIER} (ViennaMach GmbH — score 91.2)")
    print(DIVIDER)

    summaries = []

    print(f"\n  Testing llama3.2:3b...")
    r1 = test_model("llama3.2:3b", runs=RUNS)
    s1 = show_results("llama3.2:3b", r1)
    summaries.append(s1)

    print(f"\n  {DIVIDER2}")
    print(f"\n  Testing gemma4:e4b...")
    r2 = test_model("gemma4:e4b", runs=RUNS)
    s2 = show_results("gemma4:e4b", r2)
    summaries.append(s2)

    print_decision(summaries)
