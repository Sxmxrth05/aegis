"""
test_negotiator.py — Dev C tests for NegotiationEngine

Covers:
  - Clean negotiation convergence & validation approval
  - Secondary risk detection -> Validation rejection -> Counter-proposal round
  - Invariant #9: Honest NO_SAFE_MANEUVER_FOUND when all maneuvers unsafe
  - Pydantic schema validation of all NegotiationMessage and Resolution objects
  - Invariant #1: Deterministic cost evaluation (yield score matches pure function)
"""

from __future__ import annotations

from unittest.mock import patch
from datetime import datetime, timezone

import pytest

from backend.app.agents.cost_functions import compute_yield_score
from backend.app.agents.negotiator import NegotiationEngine, OperatorProfile
from backend.app.agents.validation_agent import ValidationResult
from backend.app.data.scenario import get_seeded_conjunction_alert, get_seeded_scenario_objects
from backend.app.schemas.negotiation import (
    AgentId,
    NegotiationMessage,
    ProposedAction,
    Resolution,
    ResolutionStatus,
)


@pytest.fixture
def scenario_setup():
    alert = get_seeded_conjunction_alert()
    all_objects = get_seeded_scenario_objects()
    sat_a = next(o for o in all_objects if o.norad_id == "25544")
    sat_b = next(o for o in all_objects if o.norad_id == "48274")
    clean_objects = [o for o in all_objects if o.norad_id != "36086"]

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

    return {
        "alert": alert,
        "sat_a": sat_a,
        "sat_b": sat_b,
        "clean_objects": clean_objects,
        "all_objects": all_objects,
        "profile_a": profile_a,
        "profile_b": profile_b,
    }


def test_clean_negotiation_approval(scenario_setup):
    s = scenario_setup
    engine = NegotiationEngine(
        alert=s["alert"],
        profile_a=s["profile_a"],
        profile_b=s["profile_b"],
        sat_a_state=s["sat_a"],
        sat_b_state=s["sat_b"],
        all_tracked_objects=s["clean_objects"],
    )

    transcript, resolution = engine.run_negotiation(force_initial_rejection=False)

    assert resolution.status == ResolutionStatus.APPROVED
    assert resolution.maneuvering_agent == "operator_B"
    assert len(transcript) == 3

    # Check Pydantic validity
    for msg in transcript:
        assert isinstance(msg, NegotiationMessage)
    assert isinstance(resolution, Resolution)


def test_validation_rejection_triggers_renegotiation(scenario_setup):
    s = scenario_setup
    engine = NegotiationEngine(
        alert=s["alert"],
        profile_a=s["profile_a"],
        profile_b=s["profile_b"],
        sat_a_state=s["sat_a"],
        sat_b_state=s["sat_b"],
        all_tracked_objects=s["all_objects"],
    )

    transcript, resolution = engine.run_negotiation(force_initial_rejection=True)

    # Transcript should contain:
    # Round 1: Operator A (stand_down), Operator B (maneuver), Validation (reject)
    # Round 2: Operator A (maneuver), Validation (approve)
    assert len(transcript) == 5
    assert transcript[2].agent_id == AgentId.VALIDATION
    assert transcript[2].proposed_action == ProposedAction.REJECT
    assert transcript[3].agent_id == AgentId.OPERATOR_A
    assert transcript[3].proposed_action == ProposedAction.MANEUVER
    assert transcript[4].agent_id == AgentId.VALIDATION
    assert transcript[4].proposed_action == ProposedAction.APPROVE

    assert resolution.status == ResolutionStatus.APPROVED
    assert resolution.maneuvering_agent == "operator_A"
    assert "re-negotiation" in resolution.rationale_text.lower()


def test_invariant_1_yield_score_deterministic(scenario_setup):
    s = scenario_setup
    engine = NegotiationEngine(
        alert=s["alert"],
        profile_a=s["profile_a"],
        profile_b=s["profile_b"],
        sat_a_state=s["sat_a"],
        sat_b_state=s["sat_b"],
        all_tracked_objects=s["clean_objects"],
    )

    expected_yield_a = compute_yield_score(
        mvi=s["profile_a"].mvi,
        fuel_margin_pct=s["profile_a"].fuel_margin_pct,
        delta_v_mps=s["profile_a"].delta_v_mps,
        miss_distance_km=s["alert"].miss_distance_km,
    )
    expected_yield_b = compute_yield_score(
        mvi=s["profile_b"].mvi,
        fuel_margin_pct=s["profile_b"].fuel_margin_pct,
        delta_v_mps=s["profile_b"].delta_v_mps,
        miss_distance_km=s["alert"].miss_distance_km,
    )

    transcript, _ = engine.run_negotiation(force_initial_rejection=False)
    msg_a = next(m for m in transcript if m.agent_id == AgentId.OPERATOR_A)
    msg_b = next(m for m in transcript if m.agent_id == AgentId.OPERATOR_B)

    assert msg_a.yield_score == pytest.approx(expected_yield_a, rel=1e-4)
    assert msg_b.yield_score == pytest.approx(expected_yield_b, rel=1e-4)


def test_invariant_9_no_safe_maneuver(scenario_setup):
    s = scenario_setup
    with patch("backend.app.agents.negotiator.run_validation_check") as mock_val:
        mock_val.return_value = ValidationResult(
            outcome="reject_secondary_risk",
            residual_risk=1.5,
            min_distance_found_km=1.5,
            nearest_third_object="DEBRIS-TEST",
            rationale="Secondary collision guaranteed.",
            lookahead_hours=6.0,
        )

        engine = NegotiationEngine(
            alert=s["alert"],
            profile_a=s["profile_a"],
            profile_b=s["profile_b"],
            sat_a_state=s["sat_a"],
            sat_b_state=s["sat_b"],
            all_tracked_objects=s["all_objects"],
        )

        transcript, resolution = engine.run_negotiation(force_initial_rejection=True)

        assert resolution.status == ResolutionStatus.NO_SAFE_MANEUVER_FOUND
        assert resolution.maneuvering_agent == "none"
        assert resolution.delta_v_mps == 0.0
        assert "secondary collision risks" in resolution.rationale_text.lower()
