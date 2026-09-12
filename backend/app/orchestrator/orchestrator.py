"""Monitor slice of the orchestrator (build-plan.md Workstream B, task B3).

Wraps conjunction-detection output as `ConjunctionAlert` broadcast events.
Per architecture.md's §System Boundaries, this module never computes physics
itself — it only wraps and dispatches whatever `detect_conjunctions()`
(Dev A's `agents/monitor_agent.py`) returns.
"""

from __future__ import annotations

import asyncio
import logging

try:
    from backend.app.orchestrator.websocket_manager import ConnectionManager
    from backend.app.schemas import ConjunctionAlert, ConjunctionStatus, ErrorPayload, EventType
except ImportError:
    from app.orchestrator.websocket_manager import ConnectionManager
    from app.schemas import ConjunctionAlert, ConjunctionStatus, ErrorPayload, EventType

logger = logging.getLogger(__name__)

MONITOR_SESSION_ID = "monitor"


def negotiation_session_id(conjunction_id: str) -> str:
    """Session key for a /ws/negotiation/{conjunction_id} connection."""
    return f"negotiation:{conjunction_id}"


# Mock strategy per build-plan.md Workstream B: a single hardcoded alert,
# schema-valid, to unblock B2/B3 before Dev A's A3 (scenario/detection) lands.
_HARDCODED_ALERT = ConjunctionAlert(
    id="9f1c1e2a-4b3d-4a5e-9c6f-1a2b3c4d5e6f",
    primary_id="25544",
    secondary_id="48274",
    tca_utc="2026-01-14T06:12:00Z",
    miss_distance_km=3.2,
    relative_velocity_kmps=7.5,
    status=ConjunctionStatus.ALERTED,
    created_at="2026-01-14T00:00:00Z",
)


try:
    from backend.app.agents.monitor_agent import detect_conjunctions as run_detect_conjunctions
except ImportError:
    from app.agents.monitor_agent import detect_conjunctions as run_detect_conjunctions

try:
    from backend.app.agents.negotiator import NegotiationEngine, OperatorProfile
    from backend.app.data.scenario import get_seeded_scenario_objects
    from backend.app.schemas.negotiation import AgentId
except ImportError:
    from app.agents.negotiator import NegotiationEngine, OperatorProfile
    from app.data.scenario import get_seeded_scenario_objects
    from app.schemas.negotiation import AgentId

# Hardcoded demo profiles for the scripted scenario's conjunction pair
# (ISS 25544 <-> CSS Tianhe 48274) — same values used in Dev C's own
# test_negotiator.py fixtures. Not a lookup system: every negotiation
# session currently runs this exact pair regardless of conjunction_id,
# per this task's "keep this minimal" scope. Revisit once there's more
# than one live scripted scenario to route between.
_PROFILE_A = OperatorProfile(
    agent_id=AgentId.OPERATOR_A,
    operator_name="NASA / Roscosmos",
    satellite_name="ISS (ZARYA)",
    norad_id="25544",
    mvi=0.95,
    fuel_margin_pct=15.0,
    delta_v_mps=1.8,
)
_PROFILE_B = OperatorProfile(
    agent_id=AgentId.OPERATOR_B,
    operator_name="CMSA",
    satellite_name="CSS (TIANHE)",
    norad_id="48274",
    mvi=0.70,
    fuel_margin_pct=45.0,
    delta_v_mps=2.4,
)


class Orchestrator:
    """Owns session state and dispatches Monitor-slice events over the
    WebSocket layer via `ConnectionManager`. Never touches physics/negotiation
    math directly (architecture.md §System Boundaries)."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connections = connection_manager

    def detect_conjunctions(self) -> list[ConjunctionAlert]:
        alerts = run_detect_conjunctions()
        return alerts if alerts else [_HARDCODED_ALERT]

    async def broadcast_conjunction_alerts(
        self, session_id: str = MONITOR_SESSION_ID
    ) -> None:
        for alert in self.detect_conjunctions():
            await self._connections.broadcast(session_id, EventType.CONJUNCTION_ALERT, alert)

    async def run_negotiation_session(
        self,
        conjunction_id: str,
        session_id: str,
        force_rejection: bool = False,
    ) -> None:
        """
        Runs Dev C's NegotiationEngine (agents/negotiator.py) for the
        scripted scenario and streams every message live as it's produced,
        then the final Resolution — never computing negotiation math here,
        only dispatching what the engine returns (architecture.md
        §System Boundaries).

        TODO(Dev B/C): conjunction_id is accepted for future routing
        across multiple concurrent conjunctions but isn't looked up yet —
        every session currently runs the same scripted scenario B3's
        `detect_conjunctions()` already produces (per this task's
        "keep this minimal, prove the pipe" scope).

        NegotiationEngine.run_negotiation() builds its full transcript
        synchronously with no incremental hook, so "streamed live" here
        means each already-computed message is broadcast as its own
        WebSocket frame immediately after the engine returns — not
        delivered mid-computation. True as-computed streaming would need
        a callback/generator added to the engine itself, which is Dev C's
        file and out of scope for this change.
        """
        alerts = self.detect_conjunctions()
        alert = alerts[0]

        all_objects = get_seeded_scenario_objects()
        sat_a = next(obj for obj in all_objects if obj.norad_id == alert.primary_id)
        sat_b = next(obj for obj in all_objects if obj.norad_id == alert.secondary_id)

        engine = NegotiationEngine(alert, _PROFILE_A, _PROFILE_B, sat_a, sat_b, all_objects)

        try:
            # run_negotiation() is synchronous and calls out to the
            # Anthropic API (operator_agent.py) — run it off the event
            # loop thread so a slow/failed LLM call doesn't block every
            # other connection this server is handling.
            transcript, resolution = await asyncio.to_thread(
                engine.run_negotiation, force_initial_rejection=force_rejection
            )
        except Exception:
            logger.exception(
                "[orchestrator] negotiation engine failed for conjunction %s", conjunction_id
            )
            await self._connections.broadcast(
                session_id,
                EventType.ERROR,
                ErrorPayload(message="Negotiation engine failed", code="negotiation_error"),
            )
            return

        for message in transcript:
            await self._connections.broadcast(session_id, EventType.NEGOTIATION_MESSAGE, message)

        await self._connections.broadcast(session_id, EventType.RESOLUTION, resolution)
