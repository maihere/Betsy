"""
CrewAI Simple Agent — Supplier Evaluation Demo
===============================================
Same task as langgraph_agent.py. Demonstrates what CrewAI CANNOT do natively:

  C2 — Human Approval Gate : No interrupt mechanism. The Crew runs every task
                             to completion automatically. There is no way to
                             pause a task mid-run and wait for human input
                             before continuing.

  C3 — Readable Audit Log  : CrewAI returns the final task output only.
                             There is no built-in per-step log showing what
                             the agent reasoned at each decision point.

  C4 — Persistent Memory   : No built-in persistence across separate script runs.
                             Past decisions must be injected into the task
                             description manually each time.

Install requirement:
    pip install crewai

Run standalone:
    python -m agents.crewai_agent
"""

import json

from .shared_data import ORDER_REQUEST, PAST_DECISIONS, SUPPLIERS

DIVIDER = "-" * 56

try:
    from crewai import Agent, Crew, LLM, Task
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run_crewai_agent() -> dict:
    if not _AVAILABLE:
        print(f"\n  {'CrewAI Agent':^{len(DIVIDER) - 2}}")
        print(f"  {DIVIDER}")
        print("    ✗ CrewAI not installed.")
        print("      Install with: pip install crewai")
        return {
            "framework": "CrewAI",
            "skipped":   True,
            "criteria_evidence": {
                "C2_hitl_native":   False,
                "C3_log_native":    False,
                "C4_memory_native": False,
            },
        }

    # CrewAI 1.x uses its own LLM wrapper. For Ollama, point at the
    # OpenAI-compatible endpoint (port 11434/v1) with a dummy api_key.
    llm = LLM(
        model="llama3.2:3b",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        temperature=0,
    )

    evaluator = Agent(
        role="Procurement Evaluator",
        goal="Evaluate the given suppliers and recommend the best one for the order.",
        backstory=(
            "You are a procurement specialist who scores suppliers on reliability, "
            "price, and delivery speed using a weighted formula."
        ),
        llm=llm,
        verbose=False,
    )

    # C4 LIMITATION:
    # Past performance is injected into the task description.
    # CrewAI has no built-in state object that persists between script restarts.
    # Every run starts with a blank slate unless the developer manages external storage.
    #
    # C2 LIMITATION:
    # The task runs to completion. There is no mechanism to pause at "spend > €300"
    # and wait for a human to approve before the task continues.
    task = Task(
        description=f"""
Score the following suppliers and recommend the best one.

ORDER: {ORDER_REQUEST['quantity']} units of {ORDER_REQUEST['item']}
APPROVAL THRESHOLD: €{ORDER_REQUEST['approval_threshold']}

SUPPLIERS:
{json.dumps(SUPPLIERS, indent=2)}

PAST PERFORMANCE (manually provided — C4 limitation: CrewAI does not persist this natively):
{json.dumps(PAST_DECISIONS, indent=2)}

Instructions:
1. Normalise price and delivery to 0–100 (lower cost/faster delivery = higher score).
2. Apply a -20 reliability penalty to any supplier with a late delivery note in past performance.
3. Calculate: Final = (reliability × 0.40) + (price_score × 0.35) + (delivery_score × 0.25)
4. Recommend the highest-scoring supplier.
5. State whether the total order value exceeds €{ORDER_REQUEST['approval_threshold']}.
   Note: CrewAI cannot stop here to request approval — this is a known limitation.
""",
        agent=evaluator,
        expected_output=(
            "A ranked list of suppliers with scores and a clear recommendation, "
            "including whether approval would be required."
        ),
    )

    crew = Crew(agents=[evaluator], tasks=[task], verbose=False)

    print(f"\n  {'CrewAI Agent':^{len(DIVIDER) - 2}}")
    print(f"  {DIVIDER}")
    print("    NOTE: C2 — No HITL gate. Crew will run to completion without pausing.")
    print("    NOTE: C3 — Only final task output returned. No per-step reasoning log.")
    print("    NOTE: C4 — Past decisions injected manually. Not remembered natively.\n")

    import logging, io, sys as _sys
    # Suppress CrewAI's verbose internal output — we handle failures ourselves.
    # Capture both stdout and stderr to silence the EventBus and retry warnings.
    logging.disable(logging.CRITICAL)
    _old_stdout, _old_stderr = _sys.stdout, _sys.stderr
    _sys.stdout = _sys.stderr = io.StringIO()

    llm_connected = False
    output        = ""
    _err_type     = ""
    try:
        result        = crew.kickoff()
        output        = str(result)
        llm_connected = True
    except Exception as _e:
        output    = f"LLM connection failed: {type(_e).__name__}"
        _err_type = type(_e).__name__
    finally:
        _sys.stdout = _old_stdout          # Restore stdout
        _sys.stderr = _old_stderr          # Restore stderr
        logging.disable(logging.NOTSET)    # Re-enable logging

    if llm_connected:
        print(f"    CrewAI response (truncated):")
        print(f"    {output[:500]}")
    else:
        print(f"    [!] CrewAI could not reach the LLM: {_err_type}")
        print(f"    C7 evidence — CrewAI 1.x needs extra Ollama config steps.")
        print(f"    LangGraph uses ChatOllama which connects immediately with no setup.")

    print()
    print(f"    C1 (Scheduling)  : ✗  kickoff() can be called externally but not designed for autonomous loops.")
    print(f"    C2 (HITL gate)   : ✗  No pause/resume. Crew runs to completion every time.")
    print(f"    C3 (Audit log)   : ✗  Only task output. No step-by-step reasoning log.")
    if not llm_connected:
        print(f"    C7 (Setup)       : ✗  Ollama connection failed — extra config needed vs LangGraph.")

    return {
        "framework":     "CrewAI",
        "response":       output,
        "llm_connected":  llm_connected,
        "criteria_evidence": {
            "C1_scheduling_native": False,  # kickoff() not designed for autonomous scheduling loops
            "C2_hitl_native":       False,  # No pause mechanism; task runs to completion
            "C3_log_native":        False,  # Final output only, no per-step reasoning log
        },
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_crewai_agent()
