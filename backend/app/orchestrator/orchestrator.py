"""Monitor slice of the orchestrator (build-plan.md Workstream B, task B3).

Wraps conjunction-detection output as `ConjunctionAlert` broadcast events.
Per architecture.md's §System Boundaries, this module never computes physics
itself — it only wraps and dispatches whatever `detect_conjunctions()`
(Dev A's `agents/monitor_agent.py`) returns.
"""

from __future__ import annotations

from app.orchestrator.websocket_manager import ConnectionManager
from app.schemas import ConjunctionAlert, ConjunctionStatus, EventType

MONITOR_SESSION_ID = "monitor"

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


class Orchestrator:
    """Owns session state and dispatches Monitor-slice events over the
    WebSocket layer via `ConnectionManager`. Never touches physics/negotiation
    math directly (architecture.md §System Boundaries)."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connections = connection_manager

    def detect_conjunctions(self) -> list[ConjunctionAlert]:
        # TODO(Dev A): swap this hardcoded fixture for a real call to
        # `agents/monitor_agent.py`'s `detect_conjunctions()` once A3 lands.
        # The return type (list[ConjunctionAlert]) is the locked contract —
        # this line is the only thing that should need to change.
        return [_HARDCODED_ALERT]

    async def broadcast_conjunction_alerts(
        self, session_id: str = MONITOR_SESSION_ID
    ) -> None:
        for alert in self.detect_conjunctions():
            await self._connections.broadcast(session_id, EventType.CONJUNCTION_ALERT, alert)
