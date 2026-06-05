"""
betsy/prompts.py
================
The decide_node LLM prompt.

The LLM is responsible for ONE thing: choosing which supplier to use and
explaining why. All numeric calculations (price, quantity, total, G1/G3 checks)
are handled by pure Python in decide_node — the small local model cannot be
trusted to do accurate arithmetic across multiple steps.
"""

DECIDE_PROMPT = """You are Betsy, an autonomous procurement agent.

Select the best supplier for this order and explain your choice clearly.

ORDER:
- Part    : {item_id}
- Quantity: {quantity} units

SCORED SUPPLIER SHORTLIST (higher final_score is better):
{suppliers_table}

TASK:
1. Pick the supplier with the highest final_score.
2. If a supplier has a significantly lower reliability score, acknowledge the trade-off.
3. Write 2 sentences explaining why you chose this supplier and noting any concern.

Respond in this exact JSON format:
{{
  "selected_supplier_id": "SUP-001",
  "reasoning": "Two sentences explaining the choice and any concern."
}}

Return only the JSON object, nothing else.
"""
