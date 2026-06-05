"""
AutoGen Simple Agent — Supplier Evaluation Demo
================================================
Uses autogen-agentchat 0.7.x (new API — async, different from 0.2.x).

Same task as langgraph_agent.py. Demonstrates what AutoGen CANNOT do natively:

  C1 — Autonomous Scheduling : Requires an external call to start.
                               The agent does not trigger itself.

  C2 — Human Approval Gate  : No interrupt() equivalent. The agent runs
                               to completion. There is no way to pause at
                               a spend threshold and resume the same run
                               after human input.

  C3 — Readable Audit Log   : Returns only the final reply message.
                               No per-step log of what was decided and why
                               at each stage of the workflow.

Run standalone:
    python -m agents.autogen_agent
"""

import asyncio
import json

from .shared_data import ORDER_REQUEST, PAST_DECISIONS, SUPPLIERS

DIVIDER = "-" * 56

try:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.messages import TextMessage
    from autogen_core import CancellationToken
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


async def _run_agent() -> str:
    """Run AutoGen AssistantAgent on the supplier evaluation task."""
    model_client = OpenAIChatCompletionClient(
        model="llama3.2:3b",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model_info={
            "vision":            False,
            "function_calling":  False,
            "json_output":       False,
            "structured_output": False,
            "family":            "unknown",
        },
    )

    agent = AssistantAgent(
        name="procurement_evaluator",
        model_client=model_client,
        system_message=(
            "You are a procurement evaluator. "
            "Score suppliers using: reliability 40%, price 35%, delivery 25%. "
            "Normalise each metric 0–100 before weighting. "
            "Recommend the best supplier with a brief score breakdown."
        ),
    )

    # C4 LIMITATION:
    # Past decisions must be injected into the prompt every run.
    # AutoGen has no shared state object that survives between script restarts.
    prompt = (
        f"Evaluate these suppliers for our order.\n\n"
        f"ORDER: {ORDER_REQUEST['quantity']} units of {ORDER_REQUEST['item']}\n"
        f"APPROVAL THRESHOLD: €{ORDER_REQUEST['approval_threshold']}\n\n"
        f"SUPPLIERS:\n{json.dumps(SUPPLIERS, indent=2)}\n\n"
        f"PAST PERFORMANCE (injected manually — not stored natively):\n"
        f"{json.dumps(PAST_DECISIONS, indent=2)}\n\n"
        f"Instructions:\n"
        f"1. Normalise price and delivery to 0–100 (lower price/faster = higher score).\n"
        f"2. Apply a -20 reliability penalty to any supplier with a late delivery note.\n"
        f"3. Final = (reliability × 0.40) + (price_score × 0.35) + (delivery_score × 0.25)\n"
        f"4. Recommend the highest-scoring supplier.\n"
        f"5. Note if total value (price × {ORDER_REQUEST['quantity']}) exceeds "
        f"€{ORDER_REQUEST['approval_threshold']} — but AutoGen cannot pause for approval."
    )

    # C2 LIMITATION: no interrupt mechanism — agent runs to completion
    result = await agent.on_messages(
        [TextMessage(content=prompt, source="user")],
        CancellationToken(),
    )

    await model_client.close()
    return result.chat_message.content


def run_autogen_agent() -> dict:
    print(f"\n  {'AutoGen Agent':^{len(DIVIDER) - 2}}")
    print(f"  {DIVIDER}")

    if not _AVAILABLE:
        print("    ✗ autogen-agentchat or autogen-ext not installed.")
        print("      Install with: pip install pyautogen 'autogen-ext[openai]'")
        return {
            "framework": "AutoGen",
            "skipped":   True,
            "criteria_evidence": {
                "C1_scheduling_native": False,
                "C2_hitl_native":       False,
                "C3_log_native":        False,
            },
        }

    print("    NOTE: C1 — Agent must be called externally; does not trigger itself.")
    print("    NOTE: C2 — No HITL gate. Runs to completion without pausing.")
    print("    NOTE: C3 — Only final reply returned. No per-step log.\n")

    try:
        final_reply = asyncio.run(_run_agent())
    except Exception as e:
        final_reply = f"Error: {type(e).__name__}: {e}"

    print(f"    AutoGen response (truncated):")
    print(f"    {final_reply[:500]}")
    print()
    print(f"    C1 (Scheduling)  : ✗  External trigger required — no autonomous start.")
    print(f"    C2 (HITL gate)   : ✗  No interrupt(). Approval flagged in text only.")
    print(f"    C3 (Audit log)   : ✗  Single reply. No per-step decision log.")

    return {
        "framework": "AutoGen",
        "response":  final_reply,
        "criteria_evidence": {
            "C1_scheduling_native": False,  # requires initiate_chat / on_messages call
            "C2_hitl_native":       False,  # no conditional pause/resume mechanism
            "C3_log_native":        False,  # only final reply, no step-by-step log
        },
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_autogen_agent()
