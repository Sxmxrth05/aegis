"""
test_cost_functions.py — Dev C

Unit tests for cost_functions.py. All tests are deterministic: fixed inputs →
asserted outputs. No LLM, network, or filesystem calls.

Run with:  python -m pytest backend/app/agents/tests/ -v
"""

import sys
import os
import pytest

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.agents.cost_functions import (
    compute_yield_score,
    compute_delta_v_cost,
    pick_maneuvering_agent,
    CONJUNCTION_THRESHOLD_KM,
    HYSTERESIS_CLEAR_KM,
    MAX_NEGOTIATION_ROUNDS,
    VALIDATION_LOOKAHEAD_HOURS,
)


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------

class TestConstants:
    def test_threshold_greater_than_hysteresis(self):
        """Hysteresis must be below threshold to prevent alert flicker."""
        assert HYSTERESIS_CLEAR_KM < CONJUNCTION_THRESHOLD_KM

    def test_max_rounds_positive(self):
        assert MAX_NEGOTIATION_ROUNDS > 0

    def test_lookahead_positive(self):
        assert VALIDATION_LOOKAHEAD_HOURS > 0


# ---------------------------------------------------------------------------
# compute_yield_score — boundary and scenario tests
# ---------------------------------------------------------------------------

class TestComputeYieldScore:

    def test_output_in_range(self):
        """yield_score must always be in [0.0, 1.0]."""
        score = compute_yield_score(
            mvi=5.0,
            fuel_margin_pct=50.0,
            delta_v_mps=10.0,
            miss_distance_km=2.5,
        )
        assert 0.0 <= score <= 1.0

    def test_low_mvi_yields_more(self):
        """A satellite with lower mission value should yield more than one with
        higher mission value, all else equal."""
        score_low_mvi = compute_yield_score(
            mvi=1.0, fuel_margin_pct=60.0, delta_v_mps=5.0, miss_distance_km=3.0
        )
        score_high_mvi = compute_yield_score(
            mvi=9.0, fuel_margin_pct=60.0, delta_v_mps=5.0, miss_distance_km=3.0
        )
        assert score_low_mvi > score_high_mvi, (
            f"Low MVI ({score_low_mvi}) should yield more than high MVI ({score_high_mvi})"
        )

    def test_high_fuel_yields_more(self):
        """A satellite with more fuel available should be more willing to yield."""
        score_full_tank = compute_yield_score(
            mvi=5.0, fuel_margin_pct=90.0, delta_v_mps=5.0, miss_distance_km=3.0
        )
        score_low_tank = compute_yield_score(
            mvi=5.0, fuel_margin_pct=10.0, delta_v_mps=5.0, miss_distance_km=3.0
        )
        assert score_full_tank > score_low_tank, (
            f"Full tank ({score_full_tank}) should yield more than near-empty ({score_low_tank})"
        )

    def test_expensive_burn_yields_less(self):
        """A large required Δv makes the satellite less willing to yield."""
        score_cheap = compute_yield_score(
            mvi=5.0, fuel_margin_pct=60.0, delta_v_mps=1.0, miss_distance_km=3.0
        )
        score_expensive = compute_yield_score(
            mvi=5.0, fuel_margin_pct=60.0, delta_v_mps=40.0, miss_distance_km=3.0
        )
        assert score_cheap > score_expensive, (
            f"Cheap burn ({score_cheap}) should yield more than expensive burn ({score_expensive})"
        )

    def test_closer_approach_slightly_increases_score(self):
        """Closer miss distance increases urgency term, nudging yield_score up."""
        score_very_close = compute_yield_score(
            mvi=5.0, fuel_margin_pct=60.0, delta_v_mps=5.0, miss_distance_km=0.5
        )
        score_near_threshold = compute_yield_score(
            mvi=5.0, fuel_margin_pct=60.0, delta_v_mps=5.0, miss_distance_km=4.5
        )
        assert score_very_close >= score_near_threshold, (
            "Closer approach should not reduce yield_score urgency"
        )

    def test_return_type_and_precision(self):
        """Must return a float rounded to 4 decimal places."""
        score = compute_yield_score(
            mvi=3.0, fuel_margin_pct=45.0, delta_v_mps=7.5, miss_distance_km=2.1
        )
        assert isinstance(score, float)
        assert score == round(score, 4)

    def test_maximum_willingness(self):
        """Near-zero MVI, full tank, tiny burn at close range → high yield_score."""
        score = compute_yield_score(
            mvi=0.0, fuel_margin_pct=100.0, delta_v_mps=0.0, miss_distance_km=0.1
        )
        assert score > 0.7, f"Max willingness scenario scored too low: {score}"

    def test_minimum_willingness(self):
        """High MVI, near-empty tank, massive burn → low yield_score."""
        score = compute_yield_score(
            mvi=10.0, fuel_margin_pct=5.0, delta_v_mps=50.0, miss_distance_km=4.9
        )
        assert score < 0.3, f"Min willingness scenario scored too high: {score}"

    def test_scenario_iss_style_holds_position(self):
        """ISS-equivalent (MVI=10, full tank, affordable burn) still has lower
        yield_score than an expendable relay (MVI=1) — mission priority wins."""
        iss_score = compute_yield_score(
            mvi=10.0, fuel_margin_pct=80.0, delta_v_mps=2.0, miss_distance_km=2.0
        )
        relay_score = compute_yield_score(
            mvi=1.0, fuel_margin_pct=80.0, delta_v_mps=2.0, miss_distance_km=2.0
        )
        assert relay_score > iss_score, (
            "Expendable relay should yield more than critical mission asset"
        )


# ---------------------------------------------------------------------------
# compute_yield_score — input validation
# ---------------------------------------------------------------------------

class TestComputeYieldScoreValidation:

    @pytest.mark.parametrize("bad_mvi", [-0.1, 10.1, 100.0])
    def test_invalid_mvi_raises(self, bad_mvi):
        with pytest.raises(ValueError, match="mvi"):
            compute_yield_score(bad_mvi, 50.0, 5.0, 3.0)

    @pytest.mark.parametrize("bad_fuel", [-1.0, 101.0])
    def test_invalid_fuel_raises(self, bad_fuel):
        with pytest.raises(ValueError, match="fuel_margin_pct"):
            compute_yield_score(5.0, bad_fuel, 5.0, 3.0)

    def test_negative_delta_v_raises(self):
        with pytest.raises(ValueError, match="delta_v_mps"):
            compute_yield_score(5.0, 50.0, -1.0, 3.0)

    def test_negative_miss_distance_raises(self):
        with pytest.raises(ValueError, match="miss_distance_km"):
            compute_yield_score(5.0, 50.0, 5.0, -0.1)


# ---------------------------------------------------------------------------
# compute_delta_v_cost
# ---------------------------------------------------------------------------

class TestComputeDeltaVCost:

    def test_output_in_range(self):
        cost = compute_delta_v_cost(10.0, 50.0)
        assert 0.0 <= cost <= 1.0

    def test_no_fuel_returns_max_cost(self):
        assert compute_delta_v_cost(10.0, 0.0) == 1.0

    def test_zero_delta_v_cheap(self):
        cost = compute_delta_v_cost(0.0, 80.0)
        assert cost == 0.0

    def test_high_delta_v_expensive(self):
        cost_small = compute_delta_v_cost(1.0, 80.0)
        cost_large = compute_delta_v_cost(40.0, 80.0)
        assert cost_large > cost_small


# ---------------------------------------------------------------------------
# pick_maneuvering_agent
# ---------------------------------------------------------------------------

class TestPickManeuveringAgent:

    def test_higher_score_yields(self):
        result = pick_maneuvering_agent(0.7, 0.4)
        assert result == "operator_A"

    def test_b_maneuvers_when_higher(self):
        result = pick_maneuvering_agent(0.3, 0.8)
        assert result == "operator_B"

    def test_tie_goes_to_a(self):
        """Exact tie → agent A maneuvers by deterministic convention."""
        result = pick_maneuvering_agent(0.5, 0.5)
        assert result == "operator_A"

    def test_custom_agent_ids(self):
        result = pick_maneuvering_agent(
            0.2, 0.9, agent_a_id="STARLINK-1234", agent_b_id="ONEWEB-5678"
        )
        assert result == "ONEWEB-5678"


# ---------------------------------------------------------------------------
# Harness: run standalone (python -m pytest or python tests/test_cost_functions.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
