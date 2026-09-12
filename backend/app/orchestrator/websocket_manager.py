"""Connection management, sequence numbering, and reconnect handling for
Aegis's live WebSocket sessions.

Per architecture.md: broadcasts include a monotonically increasing sequence
number per session; on new client connection, always send a full snapshot
before streaming deltas (invariant 6). This module owns transport only — it
never computes physics or negotiation state itself (architecture.md
§System Boundaries); callers (the orchestrator) supply the snapshot/event
payloads.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from backend.app.schemas import ErrorPayload, EventType, WebSocketEnvelope
except ImportError:
    from app.schemas import ErrorPayload, EventType, WebSocketEnvelope

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks connected clients and sequence numbers per session.

    A "session" groups the clients watching the same negotiation/monitor
    feed; each session has its own monotonic sequence counter so a client
    can detect gaps and request a fresh snapshot on reconnect.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._sequence: dict[str, int] = {}

    async def connect(
        self, session_id: str, websocket: WebSocket, snapshot_payload: Any
    ) -> None:
        """Accept a new client and always send it a full snapshot first
        (invariant 6) before it receives any subsequent deltas."""
        await websocket.accept()
        self._connections.setdefault(session_id, set()).add(websocket)
        self._sequence.setdefault(session_id, 0)
        await self._send(session_id, websocket, EventType.SNAPSHOT, snapshot_payload)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(session_id)
        if connections is not None:
            connections.discard(websocket)
            if not connections:
                self._connections.pop(session_id, None)
                self._sequence.pop(session_id, None)

    async def broadcast(
        self, session_id: str, event_type: EventType, payload: Any
    ) -> None:
        """Send an event to every client currently connected to a session,
        stamped with the session's next monotonic sequence number."""
        connections = list(self._connections.get(session_id, ()))
        if not connections:
            return

        sequence = self._next_sequence(session_id)
        envelope = WebSocketEnvelope(type=event_type, sequence=sequence, payload=payload)
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(envelope.model_dump_json())
            except Exception:
                logger.warning("[websocket_manager] failed to send to a client, dropping it")
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session_id, websocket)

    async def send_error(self, session_id: str, websocket: WebSocket, message: str, code: str | None = None) -> None:
        await self._send(
            session_id, websocket, EventType.ERROR, ErrorPayload(message=message, code=code)
        )

    async def _send(
        self, session_id: str, websocket: WebSocket, event_type: EventType, payload: Any
    ) -> None:
        sequence = self._next_sequence(session_id)
        envelope = WebSocketEnvelope(type=event_type, sequence=sequence, payload=payload)
        await websocket.send_text(envelope.model_dump_json())

    def _next_sequence(self, session_id: str) -> int:
        sequence = self._sequence.get(session_id, 0) + 1
        self._sequence[session_id] = sequence
        return sequence
