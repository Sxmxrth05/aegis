#!/usr/bin/env python3
"""
run_operator_agent.py — Dev C standalone verification script (C2)

Calls operator_agent.build_negotiation_message() with fixture input and
prints the result. Run this to confirm the Anthropic call + yield_score
computation pipeline works end-to-end before orchestrator integration.

Usage:
    ANTHROPIC_API_KEY=sk-... python scripts/run_operator_agent.py

    # With fallback mode (no API key set — demonstrates template fallback):
    python scripts/run_operator_agent.py

Expected output: a negotiation message dict with agent_id, round,
yield_score, justification_text, proposed_action — all fields populated.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.agents.operator_agent import build_negotiation_message, AgentState

# --- Fixture inputs (hard-coded demo scenario) ---
FIXTURE_STATES = [
    {
        "agent_id": "operator_A",
        "operator": "Starlink Operations",
        "satellite_name": "STARLINK-1234",
        "mvi": 3.0,
        "fuel_margin_pct": 72.0,
        "delta_v_mps": 4.2,
        "miss_distance_km": 1.8,
        "round_number": 1,
        "proposed_action": "maneuver",
    },
    {
        "agent_id": "operator_B",
        "operator": "OneWeb Ground Systems",
        "satellite_name": "ONEWEB-5678",
        "mvi": 8.5,
        "fuel_margin_pct": 18.0,
        "delta_v_mps": 4.2,
        "miss_distance_km": 1.8,
        "round_number": 1,
        "proposed_action": "stand_down",
    },
]


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "[run_operator_agent] ANTHROPIC_API_KEY not set — "
            "LLM calls will fail and fall back to deterministic templates.\n"
        )

    print("=" * 60)
    print("Dev C — Operator Agent Standalone Verification")
    print("=" * 60)

    for state_dict in FIXTURE_STATES:
        print(f"\nAgent: {state_dict['agent_id']} ({state_dict['satellite_name']})")
        print("-" * 40)

        message = build_negotiation_message(state_dict)
        print(json.dumps(message, indent=2))

        # Assertions
        assert "agent_id" in message
        assert "yield_score" in message
        assert "justification_text" in message
        assert 0.0 <= message["yield_score"] <= 1.0
        assert len(message["justification_text"]) >= 10
        print("  ✓ All assertions passed")

    print("\n" + "=" * 60)
    print("✓ Operator agent verification complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
