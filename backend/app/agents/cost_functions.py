"""
cost_functions.py — Dev C (Workstream C1)

Deterministic cost functions for Aegis negotiation.

INVARIANT: Every number that affects a safety decision (yield_score, Δv cost)
is computed here — pure, unit-testable Python. The LLM only narrates these
outputs; it never produces or modifies them. See architecture.md §Invariants.

Ownership: Dev C only. Do not add LLM/network calls to this module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SHARED CONSTANTS
# Dev B is the single owner of backend/app/constants.py. We import from there,
# with fallback definitions so unit tests remain fully runnable standalone.
# ---------------------------------------------------------------------------

try:
    from backend.app.constants import (
        CONJUNCTION_THRESHOLD_KM,
        HYSTERESIS_CLEAR_KM,
        MAX_NEGOTIATION_ROUNDS,
        VALIDATION_LOOKAHEAD_HOURS,
    )
except ImportError:
    try:
        from app.constants import (
            CONJUNCTION_THRESHOLD_KM,
            HYSTERESIS_CLEAR_KM,
            MAX_NEGOTIATION_ROUNDS,
            VALIDATION_LOOKAHEAD_HOURS,
        )
    except ImportError:
        CONJUNCTION_THRESHOLD_KM: float = 5.0
        HYSTERESIS_CLEAR_KM: float = 4.0
        MAX_NEGOTIATION_ROUNDS: int = 3
        VALIDATION_LOOKAHEAD_HOURS: float = 6.0

# ---------------------------------------------------------------------------
# Internal weights (tunable, but not agent-visible — judges can trace these)
# ---------------------------------------------------------------------------

_FUEL_WEIGHT: float = 0.40
"""Weight given to fuel/Δv cost in yield_score. Higher → satellites with
expensive or constrained maneuvers are less likely to yield."""

_MVI_WEIGHT: float = 0.35
"""Weight given to Mission Value Index. Higher → high-MVI satellites yield
less. MVI range is 0–10 (10 = most mission-critical)."""

_MISS_DIST_WEIGHT: float = 0.25
"""Weight given to miss-distance urgency. Closer approaches push both
satellites toward willingness to maneuver."""

_MAX_DELTA_V_MPS: float = 50.0
"""Normalization ceiling for Δv cost in m/s. Maneuvers above this are treated
as maximally expensive (yield_score contribution capped at 1.0 for this term).
Representative of a large station-keeping burn; well above typical avoidance
maneuvers (1–10 m/s)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_yield_score(
    mvi: float,
    fuel_margin_pct: float,
    delta_v_mps: float,
    miss_distance_km: float,
) -> float:
    """
    Compute the yield_score for one satellite operator in a conjunction event.

    yield_score ∈ [0.0, 1.0]
    Higher score  → this satellite *should yield* (maneuver)
    Lower score   → this satellite should hold position; the other yields

    The orchestrator compares yield_scores from both operators to determine
    who maneuvers. In the negotiation protocol, the operator with the higher
    yield_score is more willing to concede the maneuver.

    Parameters
    ----------
    mvi : float
        Mission Value Index, 0–10.  10 = maximally critical mission (ISS,
        national-security payload, etc.); 1 = expendable/redundant satellite.
        Higher MVI → satellite should NOT yield → lower yield_score.

    fuel_margin_pct : float
        Current propellant margin as % of total capacity, 0–100.
        Higher margin → maneuver is cheaper → higher yield_score.

    delta_v_mps : float
        Estimated Δv required for the avoidance maneuver, in m/s.
        Higher Δv → maneuver is more expensive → lower yield_score.

    miss_distance_km : float
        Current predicted closest-approach distance in km.
        Smaller distance → higher urgency → slightly elevates willingness
        to maneuver for the satellite that can afford it.

    Returns
    -------
    float
        yield_score ∈ [0.0, 1.0], rounded to 4 decimal places.

    Raises
    ------
    ValueError
        If any input is outside its valid range.
    """
    _validate_inputs(mvi, fuel_margin_pct, delta_v_mps, miss_distance_km)

    # --- fuel/Δv term: cheap maneuver → higher score ---
    # Normalize Δv cost relative to max expected burn; scale against margin.
    # A satellite with plenty of fuel and a tiny burn has fuel_term → 1.0.
    delta_v_norm = min(delta_v_mps / _MAX_DELTA_V_MPS, 1.0)
    fuel_margin_norm = fuel_margin_pct / 100.0
    # Fuel term combines: cheap burn AND healthy margin → high willingness
    fuel_term = fuel_margin_norm * (1.0 - delta_v_norm)

    # --- MVI term: low MVI → higher score (more willing to yield) ---
    mvi_norm = mvi / 10.0
    mvi_term = 1.0 - mvi_norm  # invert: low MVI → high yield willingness

    # --- miss-distance urgency term: closer → slightly higher willingness ---
    # Normalized so that at threshold (5 km) urgency is 1.0, at 0 km it caps.
    urgency_norm = min(1.0 - (miss_distance_km / CONJUNCTION_THRESHOLD_KM), 1.0)
    urgency_norm = max(urgency_norm, 0.0)  # clamp to [0, 1]
    miss_term = urgency_norm

    # --- weighted sum ---
    score = (
        _FUEL_WEIGHT * fuel_term
        + _MVI_WEIGHT * mvi_term
        + _MISS_DIST_WEIGHT * miss_term
    )

    return round(float(score), 4)


def compute_delta_v_cost(
    delta_v_mps: float,
    fuel_margin_pct: float,
) -> float:
    """
    Compute a normalized maneuver cost for display in the UI and negotiation log.

    This is a supporting metric shown alongside yield_score, not the primary
    decision variable. It represents "how expensive is this maneuver relative
    to the satellite's reserves."

    Returns a value in [0.0, 1.0]; 1.0 = satellite cannot afford the maneuver.

    Parameters
    ----------
    delta_v_mps : float
        Required Δv in m/s.
    fuel_margin_pct : float
        Current propellant margin as % of capacity.

    Returns
    -------
    float
        Normalized cost ∈ [0.0, 1.0].
    """
    if fuel_margin_pct <= 0:
        return 1.0  # no fuel → maneuver is impossible → maximum cost
    delta_v_norm = min(delta_v_mps / _MAX_DELTA_V_MPS, 1.0)
    affordability = fuel_margin_pct / 100.0
    cost = delta_v_norm / affordability if affordability > 0 else 1.0
    return round(min(float(cost), 1.0), 4)


def pick_maneuvering_agent(
    yield_score_a: float,
    yield_score_b: float,
    agent_a_id: str = "operator_A",
    agent_b_id: str = "operator_B",
) -> str:
    """
    Deterministic tie-break: returns the ID of the agent that should maneuver.

    The agent with the *higher* yield_score yields (maneuvers). On an exact
    tie (unlikely with floats, but possible with identical inputs), agent_a
    maneuvers by convention — this is the deterministic tie-break rule
    referenced in build-plan.md invariant 4.

    Parameters
    ----------
    yield_score_a, yield_score_b : float
        yield_scores for agent A and agent B respectively.
    agent_a_id, agent_b_id : str
        Identifiers to return (default match the DB schema agent_id values).

    Returns
    -------
    str
        The agent_id of the satellite that should perform the maneuver.
    """
    if yield_score_a >= yield_score_b:
        return agent_a_id
    return agent_b_id


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_inputs(
    mvi: float,
    fuel_margin_pct: float,
    delta_v_mps: float,
    miss_distance_km: float,
) -> None:
    if not (0.0 <= mvi <= 10.0):
        raise ValueError(f"mvi must be in [0, 10]; got {mvi}")
    if not (0.0 <= fuel_margin_pct <= 100.0):
        raise ValueError(f"fuel_margin_pct must be in [0, 100]; got {fuel_margin_pct}")
    if delta_v_mps < 0.0:
        raise ValueError(f"delta_v_mps must be non-negative; got {delta_v_mps}")
    if miss_distance_km < 0.0:
        raise ValueError(f"miss_distance_km must be non-negative; got {miss_distance_km}")
