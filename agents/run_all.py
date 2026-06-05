"""
Run all three framework agents on the same task and print an evidence table.

Usage:
    python -m agents.run_all                  # auto-approve the HITL gate (demo mode)
    python -m agents.run_all --interactive    # real human input at the LangGraph gate

After reviewing the output, add any empirical findings to:
    comparison/empirical.json
Then re-run:
    python run_comparison.py
to update the full comparison report.

Install requirements for all three frameworks:
    pip install pyautogen crewai
(LangGraph is already installed.)
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .autogen_agent import run_autogen_agent
from .crewai_agent import run_crewai_agent
from .langgraph_agent import run_langgraph_agent

DIVIDER = "=" * 60


def _symbol(value: bool) -> str:
    return "✓  Yes — native" if value else "✗  No  — manual workaround needed"


def main(interactive: bool = False) -> None:
    print(f"\n{DIVIDER}")
    print("  AGENT COMPARISON — Same task, three frameworks")
    print("  Task: Score 3 suppliers for Bearing 608ZZ (qty 80)")
    print("        Trigger HITL gate if total > €300")
    print("        Use past delivery record to adjust reliability score")
    print(DIVIDER)

    results = {}
    results["langgraph"] = run_langgraph_agent(interactive=interactive)
    results["autogen"]   = run_autogen_agent()
    results["crewai"]    = run_crewai_agent()

    # ── Evidence summary table ─────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  CRITERIA EVIDENCE — What each framework demonstrated\n")

    header = f"  {'Criterion':<34} {'LangGraph':<22} {'AutoGen':<22} {'CrewAI'}"
    print(header)
    print(f"  {'-' * (len(header) - 2)}")

    # DL1 criteria: the three requirements from Decision Log 1
    criteria_rows = [
        ("C1 — Runs without human trigger",  "C1_scheduling_native"),
        ("C2 — HITL gate (native interrupt)", "C2_hitl_native"),
        ("C3 — Per-step audit log (native)",  "C3_log_native"),
    ]

    for label, key in criteria_rows:
        lg = _symbol(results["langgraph"]["criteria_evidence"].get(key, False))
        ag = _symbol(results["autogen"]["criteria_evidence"].get(key, False))
        cr = _symbol(results["crewai"]["criteria_evidence"].get(key, False))
        print(f"  {label:<34} {lg:<22} {ag:<22} {cr}")

    print(f"\n{DIVIDER}")
    print("  WHAT THIS MEANS FOR BETSY\n")
    print("  LangGraph: All three DL1 criteria met natively.")
    print("             C1: graph.invoke() runs standalone — no human message needed to start.")
    print("             C2: interrupt() paused the graph at the spend gate and resumed after approval.")
    print("             C3: reasoning_log built automatically — every node appends to state.")
    print("             Note: scoring uses pure Python (Design Document formula), not an LLM.")
    print("             This is intentional — LangGraph lets you mix deterministic and LLM nodes.")
    print()
    print("  AutoGen:   Conversation-based — requires a human or proxy to initiate each run (C1 ✗).")
    print("             No interrupt() equivalent for a conditional spend gate (C2 ✗).")
    print("             Returns only the final message, no per-step log (C3 ✗).")
    print()
    print("  CrewAI:    Crew.kickoff() can be called externally but is not designed for")
    print("             autonomous scheduling loops (C1 ✗). No pause mechanism (C2 ✗).")
    print("             Only the final task output is returned — no per-step log (C3 ✗).")
    print()
    print("  To add these findings to the scored comparison report:")
    print("  1. Open comparison/empirical.json")
    print("  2. Add overrides based on what you observed here")
    print("  3. Run: python run_comparison.py")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    interactive = "--interactive" in sys.argv
    main(interactive=interactive)
