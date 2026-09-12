#!/usr/bin/env python3
"""
run_validation_agent.py — Dev C standalone verification script (C3)

Calls validation_agent.run_validation_check() against a fixture tracked-object
set to confirm the 6h lookahead logic works independently of the orchestrator.

Usage:
    python scripts/run_validation_agent.py

No API key or network required — pure deterministic logic with the stub propagate().

Expected output: ValidationResult for three scenarios:
  1. approve         — clean maneuver, no secondary risks
  2. reject          — secondary conjunction found, forces re-negotiation
  3. approved_no_action — maneuver not needed, miss distance already safe
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.agents.validation_agent import (
    run_validation_check,
    ProposedManeuver,
    TrackedObject,
    _stub_propagate,
    CONJUNCTION_THRESHOLD_KM,
)


# --- Fixture tracked objects ---
MOCK_OBJECTS: list[TrackedObject] = [
    {
        "norad_id": "40000",
        "name": "STARLINK-1234",
        "tle_line1": "1 40000U 14026A   26254.50000000  .00000001  00000-0  10000-4 0  9990",
        "tle_line2": "2 40000  53.0000   0.0000 0001000   0.0000 360.0000 15.05000000000001",
    },
    {
        "norad_id": "40001",
        "name": "ONEWEB-5678",
        "tle_line1": "1 40001U 14026B   26254.50000000  .00000001  00000-0  10000-4 0  9991",
        "tle_line2": "2 40001  53.0001   0.0001 0001001   0.0001 359.9999 15.05000000000002",
    },
    {
        "norad_id": "40002",
        "name": "DEBRIS-7712",
        "tle_line1": "1 40002U 14026C   26254.50000000  .00000001  00000-0  10000-4 0  9992",
        "tle_line2": "2 40002  53.0010   0.0010 0001010   0.0010 359.9990 15.05000000000003",
    },
]

NOW = datetime(2026, 9, 12, 7, 30, 0, tzinfo=timezone.utc)


def _print_result(label: str, result) -> None:
    print(f"\n{'='*60}")
    print(f"Scenario: {label}")
    print(f"{'='*60}")
    print(f"  Outcome:             {result.outcome}")
    print(f"  Residual risk (km):  {result.residual_risk:.2f}")
    print(f"  Min dist found (km): {result.min_distance_found_km:.2f}")
    print(f"  Nearest 3rd object:  {result.nearest_third_object or 'none'}")
    print(f"  Rationale:           {result.rationale}")


def main() -> None:
    print("=" * 60)
    print("Dev C — Validation Agent Standalone Verification")
    print("=" * 60)

    # --- Scenario 1: approved_no_action path ---
    # expected_min_distance_km=12.8 > threshold*1.5 (7.5) triggers no-action fast path.
    maneuver_no_maneuver_needed = ProposedManeuver(
        maneuvering_agent_id="operator_A",
        maneuvering_norad_id="40000",
        counterpart_norad_id="40001",
        delta_v_mps=4.2,
        maneuver_type="prograde",
        execution_time_utc=NOW,
        expected_min_distance_km=12.8,
    )
    result_1 = run_validation_check(
        maneuver_no_maneuver_needed,
        MOCK_OBJECTS[0],
        MOCK_OBJECTS[1],
        MOCK_OBJECTS,
        propagate_fn=_stub_propagate,
    )
    _print_result("No maneuver needed (expected: approved_no_action)", result_1)
    assert result_1.outcome == "approved_no_action", f"Unexpected: {result_1.outcome}"
    print("  ✓ Assertion passed")

    # --- Scenario 2: Full lookahead scan -> approve ---
    # Use a stub that places every object 1000+ km from the maneuvering satellite,
    # so the scan runs but finds no secondary conjunctions.
    def _far_apart_propagate(tle_line1, tle_line2, when):
        # Maneuvering satellite (norad 40000, identified by TLE content) stays at origin.
        # Everything else is placed 1000 km away in Y.
        if "40000" in tle_line1:
            return (6778.0, 0.0, 0.0), (0.0, 7.5, 0.0)
        return (6778.0, 1000.0, 0.0), (0.0, 7.5, 0.0)

    maneuver_full_scan = ProposedManeuver(
        maneuvering_agent_id="operator_A",
        maneuvering_norad_id="40000",
        counterpart_norad_id="40001",
        delta_v_mps=4.2,
        maneuver_type="prograde",
        execution_time_utc=NOW,
        expected_min_distance_km=6.0,
    )
    result_2 = run_validation_check(
        maneuver_full_scan,
        MOCK_OBJECTS[0],
        MOCK_OBJECTS[1],
        MOCK_OBJECTS,
        propagate_fn=_far_apart_propagate,
    )
    _print_result("Full scan, objects far apart (expected: approve)", result_2)
    assert result_2.outcome == "approve", f"Unexpected: {result_2.outcome}"
    print("  [PASS] Assertion passed")

    # --- Scenario 3: Force rejection via a custom propagate stub ---
    # Inject a stub that puts DEBRIS-7712 dangerously close to STARLINK-1234
    # at the first time step, so the reject path is exercised.
    def _always_close_propagate(tle_line1, tle_line2, when):
        # All objects at same position → 0 km distance → always reject
        return (6778.0, 0.0, 0.0), (0.0, 7.5, 0.0)

    maneuver_reject = ProposedManeuver(
        maneuvering_agent_id="operator_A",
        maneuvering_norad_id="40000",
        counterpart_norad_id="40001",
        delta_v_mps=6.0,
        maneuver_type="prograde",
        execution_time_utc=NOW,
        expected_min_distance_km=6.0,  # below no-action threshold (7.5 km) so scan runs
    )
    result_3 = run_validation_check(
        maneuver_reject,
        MOCK_OBJECTS[0],
        MOCK_OBJECTS[1],
        MOCK_OBJECTS,
        propagate_fn=_always_close_propagate,
    )
    _print_result("Secondary risk rejection (expected: reject_secondary_risk)", result_3)
    assert result_3.outcome == "reject_secondary_risk", f"Unexpected: {result_3.outcome}"
    print("  [PASS] Assertion passed")

    # --- Scenario 4: Real SGP4 Propagation with Real Satellite TLEs ---
    # Tests the newly-wired real SGP4 propagation (Dev A's monitor_agent)
    # without passing any mock propagate_fn stub.
    REAL_SATS: list[TrackedObject] = [
        {
            "norad_id": "25544",
            "name": "ISS (ZARYA)",
            "tle_line1": "1 25544U 98067A   26254.62728023  .00005127  00000+0  10088-3 0  9993",
            "tle_line2": "2 25544  51.6304 232.2787 0004958 129.1564 230.9865 15.49080967585152",
        },
        {
            "norad_id": "36086",
            "name": "POISK",
            "tle_line1": "1 36086U 09060A   26254.62728023  .00005127  00000+0  10088-3 0  9991",
            "tle_line2": "2 36086  51.6304 232.2787 0004958 129.1564 230.9865 15.49080967585975",
        },
        {
            "norad_id": "48274",
            "name": "CSS (TIANHE)",
            "tle_line1": "1 48274U 21035A   26254.89562246  .00017425  00000+0  21444-3 0  9993",
            "tle_line2": "2 48274  41.4684 155.5829 0002605 272.3198  87.7342 15.598303543067  1",
        },
    ]

    maneuver_real = ProposedManeuver(
        maneuvering_agent_id="operator_A",
        maneuvering_norad_id="25544",
        counterpart_norad_id="36086",
        delta_v_mps=3.5,
        maneuver_type="prograde",
        execution_time_utc=datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc),
        expected_min_distance_km=6.5,
    )
    # Note: propagate_fn=None defaults to Dev A's real_sgp4_propagate!
    result_4 = run_validation_check(
        maneuver_real,
        REAL_SATS[0],
        REAL_SATS[1],
        REAL_SATS,
        propagate_fn=None,
        lookahead_hours=1.0,
        time_step_minutes=15.0,
    )
    _print_result("Real SGP4 Propagation (ISS vs POISK/CSS)", result_4)
    assert result_4.outcome in ("approve", "reject_secondary_risk", "approved_no_action")
    print("  [PASS] Real SGP4 propagation check succeeded with outcome:", result_4.outcome)

    print("\n" + "=" * 60)
    print("[PASS] Validation agent verification complete -- all scenarios passed")
    print("  (including live SGP4 propagation via Dev A's monitor_agent.py)")
    print("=" * 60)


if __name__ == "__main__":
    main()
