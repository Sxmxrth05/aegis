"""
validation_agent.py — Dev C (Workstream C3, early start)

Cascade/Safety Validation Agent: after the operator agents converge on a
proposed maneuver, this agent re-propagates both satellites ±VALIDATION_LOOKAHEAD_HOURS
to verify the maneuver doesn't create a new downstream close approach with any
tracked object.

INVARIANT: This module is purely deterministic — no LLM calls. It uses the
same propagate() interface that Dev A's monitor_agent.py will provide. Until
Dev A's real propagate() is available (post-Checkpoint 1), a stub function is
used via dependency injection. See architecture.md §Invariants.

Ownership: Dev C only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from pydantic import BaseModel

try:
    from backend.app.agents.cost_functions import CONJUNCTION_THRESHOLD_KM, VALIDATION_LOOKAHEAD_HOURS
except ImportError:
    try:
        from app.agents.cost_functions import CONJUNCTION_THRESHOLD_KM, VALIDATION_LOOKAHEAD_HOURS
    except ImportError:
        from cost_functions import CONJUNCTION_THRESHOLD_KM, VALIDATION_LOOKAHEAD_HOURS

try:
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    from app.schemas.tracked_object import TrackedObject

try:
    from backend.app.agents.monitor_agent import build_satellite, propagate, PropagationError
except ImportError:
    try:
        from app.agents.monitor_agent import build_satellite, propagate, PropagationError
    except ImportError:
        build_satellite = None
        propagate = None
        PropagationError = Exception

logger = logging.getLogger("[validation_agent]")

# ---------------------------------------------------------------------------
# Type definitions (matching architecture.md DB schema shape)
# ---------------------------------------------------------------------------

PropagateFn = Callable[[str, str, datetime], tuple[tuple[float, float, float], tuple[float, float, float]]]
"""
Type signature of Dev A's propagate() function.
Args:   tle_line1, tle_line2, when (UTC datetime)
Returns: (position_km, velocity_kmps) both as (x, y, z) ECI tuples.

This is the *interface contract* Dev C depends on. Dev A's implementation
will satisfy this signature exactly (per build-plan.md §Workstream A).
"""

ValidationOutcome = Literal["approve", "reject_secondary_risk", "approved_no_action"]
"""
Three valid outcomes per architecture.md §Data Flow step 8:
- approve: proposed maneuver is safe, proceed.
- reject_secondary_risk: maneuver creates a new close approach; reject it
  and loop back to negotiation with added constraint.
- approved_no_action: no maneuver is needed (miss distance already safe);
  valid outcome per invariant 5.
"""


_TRACKED_OBJECT_STATE_PLACEHOLDERS = {
    "timestamp_utc": "1970-01-01T00:00:00Z",
    "position_km": (0.0, 0.0, 0.0),
    "velocity_kmps": (0.0, 0.0, 0.0),
}
"""
run_validation_check() only ever reads a tracked object's TLE identity
fields (norad_id/name/tle_line1/tle_line2) and re-propagates fresh via
propagate_fn — it never reads position_km/velocity_kmps/timestamp_utc off
the object itself. These placeholders let a caller pass a minimal
dict (just the TLE fields) through _as_tracked_object() without needing
to fabricate state it doesn't have.
"""


def _as_tracked_object(obj: TrackedObject | dict) -> TrackedObject:
    """
    Normalize a tracked-object-shaped input to the canonical Pydantic
    TrackedObject (schemas.tracked_object) so downstream code can use
    attribute access uniformly. Accepts either a real TrackedObject or a
    plain dict (e.g. this module's own standalone-script fixtures, or
    negotiator.py's pre-existing dict-based state).
    """
    if isinstance(obj, TrackedObject):
        return obj
    return TrackedObject(**{**_TRACKED_OBJECT_STATE_PLACEHOLDERS, **obj})


class ProposedManeuver(BaseModel):
    """The maneuver proposed by the negotiation agents, ready for validation."""

    maneuvering_agent_id: str
    """'operator_A' or 'operator_B' — which satellite performs the maneuver."""

    maneuvering_norad_id: str
    """NORAD catalog number of the satellite that will maneuver."""

    counterpart_norad_id: str
    """NORAD catalog number of the other conjunction satellite."""

    delta_v_mps: float
    """Proposed Δv in m/s."""

    maneuver_type: str
    """E.g. 'prograde', 'retrograde', 'radial' — for logging/display."""

    execution_time_utc: datetime
    """Planned maneuver execution time (UTC)."""

    expected_min_distance_km: float
    """Expected post-maneuver minimum miss distance, as computed by the
    proposing operator agent's cost function."""


class ValidationResult(BaseModel):
    """Output of run_validation_check()."""

    outcome: ValidationOutcome
    residual_risk: float
    """Post-maneuver minimum predicted miss distance in km across the
    lookahead window. 0.0 if outcome is reject_secondary_risk (new risk found)."""

    min_distance_found_km: float
    """Closest approach found during the lookahead window against all tracked
    objects. If this is below CONJUNCTION_THRESHOLD_KM, the maneuver is rejected."""

    nearest_third_object: str | None
    """Name of the closest third-party object found, if relevant."""

    rationale: str
    """Human-readable explanation of the validation decision (for UI display)."""

    lookahead_hours: float = VALIDATION_LOOKAHEAD_HOURS
    """Lookahead window used for this check."""


# ---------------------------------------------------------------------------
# SGP4 Propagation: Dev A's real implementation + fallback stub
# ---------------------------------------------------------------------------

_SAT_CACHE: dict[tuple[str, str], object] = {}


def real_sgp4_propagate(
    tle_line1: str,
    tle_line2: str,
    when: datetime,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Real SGP4 propagation function powered by Dev A's monitor_agent.py.

    Caches Satrec objects in memory so repeated evaluations across the lookahead
    scan do not re-parse TLE strings. Returns ECI position (km) and velocity (km/s).
    """
    if build_satellite is None or propagate is None:
        return _stub_propagate(tle_line1, tle_line2, when)

    key = (tle_line1.strip(), tle_line2.strip())
    sat = _SAT_CACHE.get(key)
    if sat is None:
        sat = build_satellite(tle_line1, tle_line2)
        _SAT_CACHE[key] = sat

    norad_id = tle_line1[2:7].strip() if len(tle_line1) >= 7 else "00000"
    state = propagate(sat, norad_id, when)
    return state.position_km, state.velocity_kmps


def _stub_propagate(
    tle_line1: str,
    tle_line2: str,
    when: datetime,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Fallback STUB: Returns a mock ECI position/velocity for testing without SGP4.
    """
    hour_offset = when.hour * 100.0
    char_sum = sum(ord(c) for c in tle_line1[:20]) if tle_line1 else 0
    x = 6778.0 + (char_sum % 200) + hour_offset * 0.001
    y = 0.0 + (char_sum % 100)
    z = 0.0
    return (x, y, z), (0.0, 7.5, 0.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_validation_check(
    proposed_maneuver: ProposedManeuver | dict,
    primary_object: TrackedObject | dict,
    secondary_object: TrackedObject | dict,
    all_tracked_objects: list[TrackedObject | dict],
    *,
    propagate_fn: PropagateFn | None = None,
    lookahead_hours: float = VALIDATION_LOOKAHEAD_HOURS,
    time_step_minutes: float = 10.0,
    reference_time: datetime | None = None,
) -> ValidationResult:
    """
    Re-propagate the conjunction pair and all tracked objects for
    VALIDATION_LOOKAHEAD_HOURS after the proposed maneuver execution time,
    checking whether the maneuver creates any new close approaches.

    Uses Dev A's real SGP4 propagation (`monitor_agent.propagate`) by default.

    Parameters
    ----------
    proposed_maneuver : ProposedManeuver | dict
        The proposed maneuver from the operator agent convergence.
    primary_object : TrackedObject | dict
        The maneuvering satellite.
    secondary_object : TrackedObject | dict
        The counterpart satellite.
    all_tracked_objects : list[TrackedObject | dict]
        Full curated tracked set (including primary and secondary).
        The maneuvering satellite's post-maneuver TLE is used; all others
        use their current TLE. For the MVP, "applied maneuver" is approximated
        by a positional offset — actual maneuver propagation is Phase 2.
    propagate_fn : PropagateFn
        Inject Dev A's real propagate() here post-Checkpoint 1.
        Defaults to the stub during Phase 1 development.
    lookahead_hours : float
        How far ahead to propagate (default: VALIDATION_LOOKAHEAD_HOURS = 6h).
    time_step_minutes : float
        Time resolution of the lookahead scan. 10 min is sufficient for LEO
        collision avoidance screening over a 6h window.
    reference_time : datetime | None
        Start time of the lookahead window. Defaults to UTC now if None.

    Returns
    -------
    ValidationResult
        outcome, residual_risk, and rationale.
    """
    if isinstance(proposed_maneuver, dict):
        proposed_maneuver = ProposedManeuver(**proposed_maneuver)

    primary_object = _as_tracked_object(primary_object)
    secondary_object = _as_tracked_object(secondary_object)
    all_tracked_objects = [_as_tracked_object(obj) for obj in all_tracked_objects]

    if propagate_fn is None:
        propagate_fn = real_sgp4_propagate if build_satellite is not None else _stub_propagate

    # Use execution_time_utc as the start of lookahead if reference not given
    start_time = reference_time or proposed_maneuver.execution_time_utc
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # --- Check 1: approved_no_action path ---
    # If expected miss distance is already well above threshold, no maneuver needed.
    if proposed_maneuver.expected_min_distance_km >= CONJUNCTION_THRESHOLD_KM * 1.5:
        logger.info(
            "[validation_agent] approved_no_action — expected miss distance %.2f km "
            "is safely above threshold (%.2f km)",
            proposed_maneuver.expected_min_distance_km,
            CONJUNCTION_THRESHOLD_KM,
        )
        return ValidationResult(
            outcome="approved_no_action",
            residual_risk=proposed_maneuver.expected_min_distance_km,
            min_distance_found_km=proposed_maneuver.expected_min_distance_km,
            nearest_third_object=None,
            rationale=(
                f"No maneuver required. Predicted miss distance "
                f"({proposed_maneuver.expected_min_distance_km:.2f} km) is safely above "
                f"the {CONJUNCTION_THRESHOLD_KM:.1f} km threshold. Approving no-action."
            ),
            lookahead_hours=lookahead_hours,
        )

    # --- Check 2: scan lookahead window for secondary conjunctions ---
    steps = int((lookahead_hours * 60) / time_step_minutes)
    closest_third_party_km: float = float("inf")
    closest_third_party_name: str | None = None

    # Build the set of "other" objects to screen against the maneuvering satellite
    maneuvering_norad = proposed_maneuver.maneuvering_norad_id
    other_objects = [
        obj for obj in all_tracked_objects
        if obj.norad_id != maneuvering_norad
    ]

    # Find the maneuvering satellite's TLE
    maneuvering_obj = _find_object(all_tracked_objects, maneuvering_norad)
    if maneuvering_obj is None:
        logger.error(
            "[validation_agent] maneuvering object %s not found in tracked set",
            maneuvering_norad,
        )
        return _rejection_result(
            "Maneuvering satellite not found in tracked object set.",
            proposed_maneuver,
        )

    logger.info(
        "[validation_agent] scanning %d time steps over %.1f h lookahead "
        "against %d objects",
        steps,
        lookahead_hours,
        len(other_objects),
    )

    for step in range(steps + 1):
        t = start_time + timedelta(minutes=step * time_step_minutes)

        try:
            # Propagate the maneuvering satellite
            # NOTE: In Phase 1 (stub), this returns a fixed position.
            # Post-Checkpoint 1: Dev A's real propagate() is injected here.
            man_pos, _ = propagate_fn(
                maneuvering_obj.tle_line1,
                maneuvering_obj.tle_line2,
                t,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[validation_agent] propagation error at step %d (%s); skipping",
                step,
                exc,
            )
            continue

        # Check against all other objects
        for other in other_objects:
            try:
                other_pos, _ = propagate_fn(other.tle_line1, other.tle_line2, t)
            except Exception:  # noqa: BLE001
                continue

            dist_km = _euclidean_distance_km(man_pos, other_pos)

            if dist_km < closest_third_party_km:
                closest_third_party_km = dist_km
                closest_third_party_name = other.name

                # Early exit: if we've already found a sub-threshold secondary risk,
                # no need to keep scanning — outcome is already reject.
                if dist_km < CONJUNCTION_THRESHOLD_KM:
                    logger.warning(
                        "[validation_agent] secondary risk detected: %s at %.2f km "
                        "at t+%d min",
                        other.name,
                        dist_km,
                        step * time_step_minutes,
                    )
                    return _rejection_result(
                        f"Secondary conjunction risk: {other.name} comes within "
                        f"{dist_km:.2f} km ({CONJUNCTION_THRESHOLD_KM:.1f} km threshold) "
                        f"at T+{step * time_step_minutes:.0f} min after maneuver.",
                        proposed_maneuver,
                        nearest_third_object=other.name,
                        min_distance_km=dist_km,
                    )

    # --- All steps clean: approve ---
    residual = min(
        proposed_maneuver.expected_min_distance_km,
        closest_third_party_km if closest_third_party_km < float("inf") else proposed_maneuver.expected_min_distance_km,
    )
    logger.info(
        "[validation_agent] approve — no secondary conjunctions found; "
        "closest third-party %.2f km (%s)",
        closest_third_party_km,
        closest_third_party_name or "none",
    )
    return ValidationResult(
        outcome="approve",
        residual_risk=residual,
        min_distance_found_km=closest_third_party_km if closest_third_party_km < float("inf") else proposed_maneuver.expected_min_distance_km,
        nearest_third_object=closest_third_party_name,
        rationale=(
            f"Maneuver validated. No secondary conjunctions found in the "
            f"{lookahead_hours:.0f}-hour lookahead window. "
            f"Closest third-party object: "
            f"{closest_third_party_name or 'none'} at "
            f"{closest_third_party_km:.2f} km "
            f"(threshold: {CONJUNCTION_THRESHOLD_KM:.1f} km). "
            f"Expected post-maneuver miss distance: "
            f"{proposed_maneuver.expected_min_distance_km:.2f} km."
        ),
        lookahead_hours=lookahead_hours,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _euclidean_distance_km(
    pos_a: tuple[float, float, float],
    pos_b: tuple[float, float, float],
) -> float:
    """Straight-line distance between two ECI position vectors, in km."""
    return (
        (pos_a[0] - pos_b[0]) ** 2
        + (pos_a[1] - pos_b[1]) ** 2
        + (pos_a[2] - pos_b[2]) ** 2
    ) ** 0.5


def _find_object(objects: list[TrackedObject], norad_id: str) -> TrackedObject | None:
    for obj in objects:
        if obj.norad_id == norad_id:
            return obj
    return None


def _rejection_result(
    rationale: str,
    maneuver: ProposedManeuver,
    nearest_third_object: str | None = None,
    min_distance_km: float = 0.0,
) -> ValidationResult:
    return ValidationResult(
        outcome="reject_secondary_risk",
        residual_risk=0.0,
        min_distance_found_km=min_distance_km,
        nearest_third_object=nearest_third_object,
        rationale=rationale,
        lookahead_hours=VALIDATION_LOOKAHEAD_HOURS,
    )
