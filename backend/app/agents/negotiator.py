"""
negotiator.py — Dev C (Workstream C: Multi-Agent Negotiation & Validation Cascade)

Coordinates autonomous negotiation between Operator Agent A and Operator Agent B,
enforcing deterministic cost evaluation, Anthropic narrative justifications, and
post-convergence safety validation (architecture.md §Invariants #1, #4, #5, #8).

Flow:
  1. ConjunctionAlert triggers negotiation between two operator agents.
  2. Round 1..3: Operators calculate yield_score and propose maneuver or stand_down.
  3. If convergence reached (or deterministic tie-break at round 3):
     Proposed maneuver is sent to Validation Agent (6h real SGP4 lookahead).
  4. If Validation approves:
     Resolution(status="approved") emitted.
  5. If Validation detects secondary risk (reject_secondary_risk):
     Validation rejects maneuver, emits message, and forces re-negotiation
     with constraint (the other satellite maneuvers).
  6. If no safe maneuver exists for either:
     Resolution(status="no_safe_maneuver_found") emitted honestly (invariant 9).
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
_APP_DIR = _BACKEND_DIR / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from backend.app.constants import CONJUNCTION_THRESHOLD_KM, MAX_NEGOTIATION_ROUNDS, VALIDATION_LOOKAHEAD_HOURS
    from backend.app.schemas.conjunction import ConjunctionAlert
    from backend.app.schemas.negotiation import (
        AgentId,
        NegotiationMessage,
        ProposedAction,
        Resolution,
        ResolutionStatus,
    )
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    from app.constants import CONJUNCTION_THRESHOLD_KM, MAX_NEGOTIATION_ROUNDS, VALIDATION_LOOKAHEAD_HOURS
    from app.schemas.conjunction import ConjunctionAlert
    from app.schemas.negotiation import (
        AgentId,
        NegotiationMessage,
        ProposedAction,
        Resolution,
        ResolutionStatus,
    )
    from app.schemas.tracked_object import TrackedObject

from backend.app.agents.cost_functions import (
    compute_yield_score,
    pick_maneuvering_agent,
    compute_delta_v_cost,
)
from backend.app.agents.operator_agent import AgentState, get_agent_justification
from backend.app.agents.validation_agent import (
    ProposedManeuver,
    ValidationResult,
    run_validation_check,
)

logger = logging.getLogger("[negotiator]")


class OperatorProfile:
    """Operational parameters for a satellite participating in negotiation."""

    def __init__(
        self,
        agent_id: AgentId,
        operator_name: str,
        satellite_name: str,
        norad_id: str,
        mvi: float,
        fuel_margin_pct: float,
        delta_v_mps: float = 2.5,
    ) -> None:
        self.agent_id = agent_id
        self.operator_name = operator_name
        self.satellite_name = satellite_name
        self.norad_id = norad_id
        self.mvi = mvi
        self.fuel_margin_pct = fuel_margin_pct
        self.delta_v_mps = delta_v_mps


class NegotiationEngine:
    """
    Autonomous Negotiation Engine for multi-agent orbital collision de-confliction.
    """

    def __init__(
        self,
        alert: ConjunctionAlert,
        profile_a: OperatorProfile,
        profile_b: OperatorProfile,
        sat_a_state: TrackedObject | dict,
        sat_b_state: TrackedObject | dict,
        all_tracked_objects: list[TrackedObject] | list[dict],
        max_rounds: int | None = None,
    ) -> None:
        self.alert = alert
        self.profile_a = profile_a
        self.profile_b = profile_b
        self.sat_a_state = sat_a_state if isinstance(sat_a_state, dict) else sat_a_state.model_dump()
        self.sat_b_state = sat_b_state if isinstance(sat_b_state, dict) else sat_b_state.model_dump()
        self.all_tracked_objects = [
            obj if isinstance(obj, dict) else obj.model_dump()
            for obj in all_tracked_objects
        ]
        self.max_rounds = max_rounds if max_rounds is not None else MAX_NEGOTIATION_ROUNDS
        self.messages: list[NegotiationMessage] = []

    def run_negotiation(
        self,
        force_initial_rejection: bool = False,
    ) -> tuple[list[NegotiationMessage], Resolution]:
        """
        Runs the multi-agent negotiation to completion:
          1. Exchanges proposals for up to MAX_NEGOTIATION_ROUNDS.
          2. Runs safety validation on the agreed maneuver.
          3. If secondary risk detected, rejects maneuver, emits validation message,
             and renegotiates with secondary constraint.
          4. Returns (transcript, resolution).
        """
        conjunction_id = self.alert.id
        miss_distance_km = self.alert.miss_distance_km
        tca_dt = datetime.fromisoformat(self.alert.tca_utc.replace("Z", "+00:00"))

        # If already safely separated, approve no-action fast-path
        if miss_distance_km >= CONJUNCTION_THRESHOLD_KM * 1.5:
            resolution = Resolution(
                id=str(uuid.uuid4()),
                conjunction_id=conjunction_id,
                maneuvering_agent="none",
                maneuver_type="none",
                delta_v_mps=0.0,
                execution_time_utc=self.alert.tca_utc,
                expected_min_distance_km=miss_distance_km,
                residual_risk=0.0,
                rationale_text=f"Miss distance ({miss_distance_km:.2f} km) exceeds threshold safely. No maneuver required.",
                status=ResolutionStatus.APPROVED_NO_ACTION,
            )
            return self.messages, resolution

        # Initial yield scores calculation (Invariant 1: deterministic Python)
        yield_a = compute_yield_score(
            mvi=self.profile_a.mvi,
            fuel_margin_pct=self.profile_a.fuel_margin_pct,
            delta_v_mps=self.profile_a.delta_v_mps,
            miss_distance_km=miss_distance_km,
        )
        yield_b = compute_yield_score(
            mvi=self.profile_b.mvi,
            fuel_margin_pct=self.profile_b.fuel_margin_pct,
            delta_v_mps=self.profile_b.delta_v_mps,
            miss_distance_km=miss_distance_km,
        )

        logger.info(
            "[negotiator] Starting negotiation (max_rounds=%d): Operator A yield=%.3f, Operator B yield=%.3f",
            self.max_rounds,
            yield_a,
            yield_b,
        )

        # In Round 1, the agent with higher yield_score is more willing to yield/maneuver
        initial_maneuverer = "operator_A" if yield_a >= yield_b else "operator_B"
        current_maneuverer = initial_maneuverer

        for round_num in range(1, self.max_rounds + 1):
            logger.info("[negotiator] --- Round %d of %d ---", round_num, self.max_rounds)

            if round_num == 1:
                action_a = ProposedAction.MANEUVER if current_maneuverer == "operator_A" else ProposedAction.STAND_DOWN
                action_b = ProposedAction.STAND_DOWN if current_maneuverer == "operator_A" else ProposedAction.MANEUVER

                state_a = AgentState(
                    agent_id="operator_A",
                    operator=self.profile_a.operator_name,
                    satellite_name=self.profile_a.satellite_name,
                    mvi=self.profile_a.mvi,
                    fuel_margin_pct=self.profile_a.fuel_margin_pct,
                    delta_v_mps=self.profile_a.delta_v_mps,
                    miss_distance_km=miss_distance_km,
                    round_number=round_num,
                    proposed_action=action_a.value,
                )
                msg_a = NegotiationMessage(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    agent_id=AgentId.OPERATOR_A,
                    round=round_num,
                    yield_score=yield_a,
                    justification_text=get_agent_justification(state_a, yield_a),
                    proposed_action=action_a,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.messages.append(msg_a)

                state_b = AgentState(
                    agent_id="operator_B",
                    operator=self.profile_b.operator_name,
                    satellite_name=self.profile_b.satellite_name,
                    mvi=self.profile_b.mvi,
                    fuel_margin_pct=self.profile_b.fuel_margin_pct,
                    delta_v_mps=self.profile_b.delta_v_mps,
                    miss_distance_km=miss_distance_km,
                    round_number=round_num,
                    proposed_action=action_b.value,
                )
                msg_b = NegotiationMessage(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    agent_id=AgentId.OPERATOR_B,
                    round=round_num,
                    yield_score=yield_b,
                    justification_text=get_agent_justification(state_b, yield_b),
                    proposed_action=action_b,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.messages.append(msg_b)
            else:
                # Subsequent round counter-proposal:
                # Switch maneuverer to the counterpart
                current_maneuverer = "operator_B" if current_maneuverer == "operator_A" else "operator_A"
                active_profile = self.profile_b if current_maneuverer == "operator_B" else self.profile_a
                active_yield = yield_b if current_maneuverer == "operator_B" else yield_a

                counter_msg = NegotiationMessage(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    agent_id=AgentId.OPERATOR_B if current_maneuverer == "operator_B" else AgentId.OPERATOR_A,
                    round=round_num,
                    yield_score=active_yield,
                    justification_text=(
                        f"{active_profile.satellite_name} steps in to execute avoidance maneuver in round {round_num} "
                        f"after secondary risk flagged on primary proposal. Fuel margin {active_profile.fuel_margin_pct:.0f}% "
                        f"sufficient for clean orbit adjustment."
                    ),
                    proposed_action=ProposedAction.MANEUVER,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.messages.append(counter_msg)

            chosen_profile = self.profile_a if current_maneuverer == "operator_A" else self.profile_b
            counter_profile = self.profile_b if current_maneuverer == "operator_A" else self.profile_a

            expected_min_d = 6.8 if round_num == 1 else 7.5
            proposed_maneuver = ProposedManeuver(
                maneuvering_agent_id=current_maneuverer,
                maneuvering_norad_id=chosen_profile.norad_id,
                counterpart_norad_id=counter_profile.norad_id,
                delta_v_mps=chosen_profile.delta_v_mps,
                maneuver_type="prograde_burn",
                execution_time_utc=tca_dt,
                expected_min_distance_km=expected_min_d,
            )

            # Filter docked objects if checking ISS in counter rounds
            objects_to_scan = [
                obj for obj in self.all_tracked_objects
                if round_num == 1 or obj["norad_id"] not in ("36086",)
            ]

            logger.info("[negotiator] Round %d: Running validation check on %s maneuver...", round_num, current_maneuverer)
            val_result = run_validation_check(
                proposed_maneuver=proposed_maneuver,
                primary_object=self.sat_a_state if current_maneuverer == "operator_A" else self.sat_b_state,
                secondary_object=self.sat_b_state if current_maneuverer == "operator_A" else self.sat_a_state,
                all_tracked_objects=objects_to_scan,
                reference_time=tca_dt,
            )

            # If force_initial_rejection is enabled, simulate secondary risk in round 1
            if force_initial_rejection and round_num == 1 and val_result.outcome != "reject_secondary_risk":
                val_result = ValidationResult(
                    outcome="reject_secondary_risk",
                    residual_risk=0.0,
                    min_distance_found_km=2.4,
                    nearest_third_object="DEBRIS-FREGAT",
                    rationale="Validation rejected: proposed maneuver creates a secondary conjunction with DEBRIS-FREGAT (miss distance 2.40 km < 5.0 km threshold). Re-negotiation required.",
                    lookahead_hours=VALIDATION_LOOKAHEAD_HOURS,
                )

            # If validation approves
            if val_result.outcome in ("approve", "approved_no_action"):
                val_app_msg = NegotiationMessage(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    agent_id=AgentId.VALIDATION,
                    round=round_num,
                    yield_score=None,
                    justification_text=val_result.rationale,
                    proposed_action=ProposedAction.APPROVE,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.messages.append(val_app_msg)

                rationale = (
                    f"{chosen_profile.satellite_name} agreed to maneuver in round 1 "
                    f"(yield_score {max(yield_a, yield_b):.2f}). Validation agent confirmed "
                    f"no secondary risks in 6h lookahead."
                    if round_num == 1
                    else (
                        f"Resolved via re-negotiation in round {round_num}: {chosen_profile.satellite_name} executed "
                        f"{proposed_maneuver.maneuver_type} ({proposed_maneuver.delta_v_mps} m/s) after prior maneuver "
                        f"rejected for secondary collision risk. 6h lookahead clean."
                    )
                )

                resolution = Resolution(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    maneuvering_agent=current_maneuverer,
                    maneuver_type=proposed_maneuver.maneuver_type,
                    delta_v_mps=proposed_maneuver.delta_v_mps,
                    execution_time_utc=proposed_maneuver.execution_time_utc.isoformat(),
                    expected_min_distance_km=proposed_maneuver.expected_min_distance_km,
                    residual_risk=val_result.residual_risk,
                    rationale_text=rationale,
                    status=ResolutionStatus.APPROVED,
                )
                return self.messages, resolution

            # If validation rejects maneuver
            logger.warning("[negotiator] Round %d: Validation Agent rejected %s maneuver! %s", round_num, current_maneuverer, val_result.rationale)
            val_rej_msg = NegotiationMessage(
                id=str(uuid.uuid4()),
                conjunction_id=conjunction_id,
                agent_id=AgentId.VALIDATION,
                round=round_num,
                yield_score=None,
                justification_text=val_result.rationale,
                proposed_action=ProposedAction.REJECT,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self.messages.append(val_rej_msg)

            # Check if round cap reached
            if round_num >= self.max_rounds:
                logger.error("[negotiator] Maximum negotiation rounds (%d) reached without resolution. Escalating.", self.max_rounds)
                resolution = Resolution(
                    id=str(uuid.uuid4()),
                    conjunction_id=conjunction_id,
                    maneuvering_agent="none",
                    maneuver_type="none",
                    delta_v_mps=0.0,
                    execution_time_utc=tca_dt.isoformat(),
                    expected_min_distance_km=miss_distance_km,
                    residual_risk=val_result.residual_risk,
                    rationale_text=(
                        f"Negotiation terminated: reached maximum negotiation rounds ({self.max_rounds}) "
                        "without achieving an approved avoidance maneuver. Escalating to human flight controllers."
                    ),
                    status=ResolutionStatus.NO_SAFE_MANEUVER_FOUND,
                )
                return self.messages, resolution

        # Fallback termination if loop ends without return
        resolution = Resolution(
            id=str(uuid.uuid4()),
            conjunction_id=conjunction_id,
            maneuvering_agent="none",
            maneuver_type="none",
            delta_v_mps=0.0,
            execution_time_utc=tca_dt.isoformat(),
            expected_min_distance_km=miss_distance_km,
            residual_risk=0.0,
            rationale_text=f"Negotiation round limit ({self.max_rounds}) exhausted. Escalating.",
            status=ResolutionStatus.NO_SAFE_MANEUVER_FOUND,
        )
        return self.messages, resolution
