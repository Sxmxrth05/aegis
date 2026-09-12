#!/usr/bin/env python3
"""
run_negotiation_simulation.py — Dev C Verification & Simulation Script (Workstream C)

Simulates the autonomous multi-agent negotiation engine:
  Scenario 1: Clean convergence and validation approval
  Scenario 2: Validation rejection on primary proposal (secondary risk) ->
              Automatic re-negotiation round with secondary constraint ->
              Counter-proposal accepted and approved by Validation Agent
  Scenario 3: Validation rejection on both proposals ->
              Honest Resolution(status="no_safe_maneuver_found") (Invariant #9)

Usage:
  python scripts/run_negotiation_simulation.py
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timezone

# Fix UnicodeEncodeError on Windows cp1252 terminals (Delta, em-dash characters)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.agents.negotiator import NegotiationEngine, OperatorProfile
from backend.app.schemas.conjunction import ConjunctionAlert
from backend.app.schemas.negotiation import (
    AgentId,
    NegotiationMessage,
    ProposedAction,
    Resolution,
    ResolutionStatus,
)
from backend.app.data.scenario import get_seeded_conjunction_alert, get_seeded_scenario_objects


def print_banner(title: str) -> None:
    print(f"\n{'='*75}")
    print(f" {title}")
    print(f"{'='*75}")


def print_transcript(messages: list[NegotiationMessage], resolution: Resolution) -> None:
    print(f"\n--- Negotiation Transcript ({len(messages)} messages) ---")
    for idx, msg in enumerate(messages, start=1):
        yield_str = f"yield={msg.yield_score:.3f}" if msg.yield_score is not None else "yield=N/A"
        print(f"[{idx}] Round {msg.round} | Agent: {msg.agent_id.value:<12} | Action: {msg.proposed_action.value:<10} | {yield_str}")
        print(f"    Justification: {msg.justification_text}")

    print(f"\n--- Final Resolution ---")
    print(f"  Status:          {resolution.status.value}")
    print(f"  Maneuvering Sat: {resolution.maneuvering_agent}")
    print(f"  Maneuver Type:   {resolution.maneuver_type} ({resolution.delta_v_mps} m/s)")
    print(f"  Execution Time:  {resolution.execution_time_utc}")
    print(f"  Expected Min D:  {resolution.expected_min_distance_km:.2f} km")
    print(f"  Residual Risk:   {resolution.residual_risk:.2f}")
    print(f"  Rationale:       {resolution.rationale_text}")


def main() -> None:
    print("=" * 75)
    print("  AEGIS DEV C - MULTI-AGENT NEGOTIATION & VALIDATION SIMULATION")
    print("=" * 75)

    alert = get_seeded_conjunction_alert()
    all_objects = get_seeded_scenario_objects()

    # Find ISS and CSS objects
    sat_a = next(o for o in all_objects if o.norad_id == "25544")
    sat_b = next(o for o in all_objects if o.norad_id == "48274")

    # =========================================================================
    # SCENARIO 1: Clean Negotiation & Validation Approval
    # =========================================================================
    print_banner("SCENARIO 1: Clean Negotiation & Validation Approval")
    print("Operator A (ISS - High MVI 0.95, Low Fuel Margin 15%)")
    print("Operator B (CSS - Moderate MVI 0.70, High Fuel Margin 45%)")

    profile_a = OperatorProfile(
        agent_id=AgentId.OPERATOR_A,
        operator_name="NASA / Roscosmos",
        satellite_name="ISS (ZARYA)",
        norad_id="25544",
        mvi=0.95,
        fuel_margin_pct=15.0,
        delta_v_mps=1.8,
    )
    profile_b = OperatorProfile(
        agent_id=AgentId.OPERATOR_B,
        operator_name="CMSA",
        satellite_name="CSS (TIANHE)",
        norad_id="48274",
        mvi=0.70,
        fuel_margin_pct=45.0,
        delta_v_mps=2.4,
    )

    # Filter out docked POISK (36086) for clean scenario to test clean approval path
    clean_objects = [o for o in all_objects if o.norad_id != "36086"]

    engine1 = NegotiationEngine(
        alert=alert,
        profile_a=profile_a,
        profile_b=profile_b,
        sat_a_state=sat_a,
        sat_b_state=sat_b,
        all_tracked_objects=clean_objects,
    )

    transcript1, resolution1 = engine1.run_negotiation(force_initial_rejection=False)
    print_transcript(transcript1, resolution1)

    assert resolution1.status == ResolutionStatus.APPROVED, f"Expected APPROVED, got {resolution1.status}"
    assert resolution1.maneuvering_agent in ("operator_A", "operator_B")
    print("\n[OK] Scenario 1 verified successfully!")

    # =========================================================================
    # SCENARIO 2: Validation Rejection -> Re-negotiation -> Counter-proposal Approved
    # =========================================================================
    print_banner("SCENARIO 2: Validation Rejection & Re-negotiation Flow")
    print("Trigger: Primary maneuver proposal creates secondary risk with third body.")
    print("Action: Validation Agent REJECTS -> Triggers Round 2 with counter-proposal.")

    # Using all objects with docked POISK triggers real SGP4 secondary collision detection on ISS
    engine2 = NegotiationEngine(
        alert=alert,
        profile_a=profile_a,
        profile_b=profile_b,
        sat_a_state=sat_a,
        sat_b_state=sat_b,
        all_tracked_objects=all_objects,
    )

    transcript2, resolution2 = engine2.run_negotiation(force_initial_rejection=True)
    print_transcript(transcript2, resolution2)

    assert any(m.proposed_action == ProposedAction.REJECT for m in transcript2), "Expected rejection message in transcript"
    assert resolution2.status == ResolutionStatus.APPROVED, f"Expected APPROVED, got {resolution2.status}"
    assert resolution2.maneuvering_agent == "operator_A", f"Expected operator_A after B was rejected, got {resolution2.maneuvering_agent}"
    print("\n[OK] Scenario 2 (Re-negotiation cascade) verified successfully!")

    # =========================================================================
    # SCENARIO 3: Both Maneuvers Unsafe -> NO_SAFE_MANEUVER_FOUND (Invariant #9)
    # =========================================================================
    print_banner("SCENARIO 3: No Safe Maneuver Found -> Flight Controller Escalation")
    print("Trigger: Both primary and secondary proposed maneuvers create secondary risks.")
    print("Action: NegotiationEngine safely emits NO_SAFE_MANEUVER_FOUND.")

    # We mock run_validation_check returning reject_secondary_risk for both
    from unittest.mock import patch
    from backend.app.agents.validation_agent import ValidationResult

    with patch("backend.app.agents.negotiator.run_validation_check") as mock_val:
        mock_val.return_value = ValidationResult(
            outcome="reject_secondary_risk",
            residual_risk=1.2,
            min_distance_found_km=1.2,
            nearest_third_object="DEBRIS-COSMOS-2251",
            rationale="Secondary conjunction detected: predicted miss distance 1.20 km < 5.0 km threshold.",
            lookahead_hours=6.0,
        )

        engine3 = NegotiationEngine(
            alert=alert,
            profile_a=profile_a,
            profile_b=profile_b,
            sat_a_state=sat_a,
            sat_b_state=sat_b,
            all_tracked_objects=all_objects,
        )

        transcript3, resolution3 = engine3.run_negotiation(force_initial_rejection=True)
        print_transcript(transcript3, resolution3)

        assert resolution3.status == ResolutionStatus.NO_SAFE_MANEUVER_FOUND, f"Expected NO_SAFE_MANEUVER_FOUND, got {resolution3.status}"
        assert resolution3.maneuvering_agent == "none"
        print("\n[OK] Scenario 3 (Invariant #9 escalation) verified successfully!")

    print_banner("ALL NEGOTIATION & VALIDATION SIMULATION TESTS PASSED!")


if __name__ == "__main__":
    main()
