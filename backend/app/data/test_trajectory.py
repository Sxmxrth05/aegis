"""
test_trajectory.py — Dev A (Phase 2 Workstream A)

Unit and regression tests for orbital trajectory simulation and maneuver preview.
Verifies:
1. RK4 numerical integration & orbital mechanics consistency
2. Impulsive burn vectors (prograde, retrograde, radial, normal)
3. End-to-end before/after trajectory generation for the locked scenario
4. Maneuver divergence & conjunction clearance (> CONJUNCTION_THRESHOLD_KM)
5. Generation of frontend mock fixture (trajectory_simulation.json)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.constants import CONJUNCTION_THRESHOLD_KM
from app.data.scenario import get_seeded_scenario_objects, SCENARIO_TCA_UTC
from app.data.trajectory import (
    EARTH_MU,
    EARTH_RADIUS_KM,
    apply_impulse_burn,
    distance_km,
    eci_to_geodetic,
    generate_maneuver_trajectory,
    rk4_step,
    simulate_seeded_conjunction_trajectory,
    TrajectoryWaypoint,
    TrajectoryStep,
    ManeuverTrajectoryResult,
)
from app.schemas.negotiation import Resolution, ResolutionStatus
from app.schemas.tracked_object import TrackedObject


def test_rk4_orbital_energy_conservation():
    """Verify that RK4 numerical integration preserves orbital energy over multiple steps."""
    # LEO circular orbit at 400 km altitude: r ~ 6778 km, v ~ 7.67 km/s
    r0 = (6778.0, 0.0, 0.0)
    v0 = (0.0, 7.6686, 0.0)

    # Initial specific orbital mechanical energy: E = v^2/2 - mu/r
    e0 = (v0[0]**2 + v0[1]**2 + v0[2]**2) / 2.0 - EARTH_MU / math.sqrt(r0[0]**2 + r0[1]**2 + r0[2]**2)

    # Propagate for 1 full orbit (~5400 seconds) in 30s steps
    dt = 30.0
    r, v = r0, v0
    for _ in range(180):
        r, v = rk4_step(r, v, dt)

    e_final = (v[0]**2 + v[1]**2 + v[2]**2) / 2.0 - EARTH_MU / math.sqrt(r[0]**2 + r[1]**2 + r[2]**2)
    relative_energy_drift = abs((e_final - e0) / e0)

    assert relative_energy_drift < 1e-4, f"Energy drift too high: {relative_energy_drift}"
    # Verify altitude remains in LEO
    alt_km = math.sqrt(r[0]**2 + r[1]**2 + r[2]**2) - EARTH_RADIUS_KM
    assert 390.0 < alt_km < 410.0


def test_apply_impulse_burn_directions():
    """Verify prograde, retrograde, radial, and normal velocity impulses."""
    r = (7000.0, 0.0, 0.0)
    v = (0.0, 7.5, 0.0)
    v_mag = 7.5

    # 1. Prograde (+100 m/s = +0.1 km/s along velocity)
    v_pro = apply_impulse_burn(r, v, "prograde_burn", delta_v_mps=100.0)
    assert math.isclose(v_pro[1], 7.6, abs_tol=1e-6)
    assert math.isclose(v_pro[0], 0.0, abs_tol=1e-6)
    assert math.isclose(v_pro[2], 0.0, abs_tol=1e-6)

    # 2. Retrograde (-100 m/s = -0.1 km/s along velocity)
    v_ret = apply_impulse_burn(r, v, "retrograde_burn", delta_v_mps=100.0)
    assert math.isclose(v_ret[1], 7.4, abs_tol=1e-6)

    # 3. Radial (+100 m/s along position vector)
    v_rad = apply_impulse_burn(r, v, "radial_burn", delta_v_mps=100.0)
    assert math.isclose(v_rad[0], 0.1, abs_tol=1e-6)
    assert math.isclose(v_rad[1], 7.5, abs_tol=1e-6)

    # 4. Normal (+100 m/s along r x v = +z axis)
    v_norm = apply_impulse_burn(r, v, "normal_burn", delta_v_mps=100.0)
    assert math.isclose(v_norm[2], 0.1, abs_tol=1e-6)
    assert math.isclose(v_norm[1], 7.5, abs_tol=1e-6)


def test_eci_to_geodetic_bounds():
    """Verify coordinate conversion produces valid lat, lng, and altitude."""
    now = datetime(2026, 1, 14, 6, 12, 0, tzinfo=timezone.utc)
    r_eci = (2577.608, -3366.514, 5294.249)

    lat, lng, alt = eci_to_geodetic(r_eci, now)
    assert -90.0 <= lat <= 90.0
    assert -180.0 <= lng <= 180.0
    assert 300.0 < alt < 600.0, f"Unexpected altitude {alt} km for LEO object"


def test_generate_maneuver_trajectory_conjunction_clearance():
    """Verify that a maneuver successfully widens miss distance and clears the conjunction."""
    result = simulate_seeded_conjunction_trajectory()

    assert isinstance(result, ManeuverTrajectoryResult)
    assert result.primary_norad_id == "25544"
    assert result.secondary_norad_id == "48274"
    assert result.maneuvering_norad_id == "25544"

    # Nominal closest approach must replicate the sub-threshold close approach (~3.2 km)
    assert result.min_distance_nominal_km < CONJUNCTION_THRESHOLD_KM
    assert math.isclose(result.min_distance_nominal_km, 3.20, abs_tol=0.2)

    # Maneuvered closest approach must clear the 5.0 km threshold
    assert result.min_distance_maneuvered_km >= CONJUNCTION_THRESHOLD_KM
    assert result.cleared_threshold is True
    assert result.min_distance_maneuvered_km > 10.0, (
        f"Post-maneuver miss distance should widen significantly, got {result.min_distance_maneuvered_km} km"
    )

    # Timeline scrubber steps
    assert len(result.steps) > 50
    # Before burn, nominal and maneuvered distances should be identical
    pre_burn_steps = [s for s in result.steps if not s.is_post_burn]
    assert len(pre_burn_steps) > 0
    for s in pre_burn_steps:
        assert math.isclose(s.nominal_distance_km, s.maneuvered_distance_km, abs_tol=1e-4)

    # After burn, distances diverge
    post_burn_steps = [s for s in result.steps if s.is_post_burn]
    assert len(post_burn_steps) > 0
    diverged = any(abs(s.nominal_distance_km - s.maneuvered_distance_km) > 0.5 for s in post_burn_steps)
    assert diverged, "Trajectories should visibly diverge post-burn"

    # Polylines for 3D Globe
    assert len(result.nominal_path_primary) == len(result.steps)
    assert len(result.nominal_path_secondary) == len(result.steps)
    assert len(result.maneuvered_path) == len(result.steps)


def test_generate_and_save_fixture():
    """Generates the static JSON fixture in fixtures/ for Dev D mock-first frontend use."""
    result = simulate_seeded_conjunction_trajectory()
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixtures_dir / "trajectory_simulation.json"

    fixture_path.write_text(result.model_dump_json(indent=2))
    assert fixture_path.exists()
    assert fixture_path.stat().st_size > 1000
