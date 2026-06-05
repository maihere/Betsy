"""
Shared test data used by ALL three framework agents.
Same input, same task — ensures the comparison is fair.

Task: score three suppliers for an order of Bearing 608ZZ
      and select the best one. If total order value > €300,
      an approval gate should fire (tests C2).
"""

ORDER_REQUEST = {
    "item":               "Bearing 608ZZ",
    "quantity":           80,           # 80 units → all totals exceed €300 → HITL gate fires
    "approval_threshold": 300.0,
}

SUPPLIERS = [
    {
        "id":                "SUP001",
        "name":              "AccuParts Ltd",
        "price_per_unit":    4.20,
        "delivery_hours":    48,
        "reliability_score": 85,
    },
    {
        "id":                "SUP002",
        "name":              "BoltCo GmbH",
        "price_per_unit":    3.80,
        "delivery_hours":    72,
        "reliability_score": 60,
    },
    {
        "id":                "SUP003",
        "name":              "SpeedFix Inc",
        "price_per_unit":    5.00,
        "delivery_hours":    24,
        "reliability_score": 92,
    },
]
# Total values at qty=80:
#   AccuParts = €336  ← above threshold → gate fires
#   BoltCo    = €304  ← above threshold → gate fires
#   SpeedFix  = €400  ← above threshold → gate fires

PAST_DECISIONS = [
    {
        "supplier_id": "SUP002",
        "item":        "Bearing 608ZZ",
        "date":        "2025-04-15",
        "notes":       "Delivered 2 days late. Production stalled for 4 hours.",
    },
]
# BoltCo (SUP002) has a late delivery on record.
# Agents that use this data (C4 memory) apply a -20 reliability penalty
# and rank BoltCo lower. Agents without memory cannot use this.
