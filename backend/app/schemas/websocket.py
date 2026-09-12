"""WebSocket envelope contract: every message sent over the wire is
`{type, sequence, payload}`.

`sequence` is monotonically increasing per session (see
`orchestrator/websocket_manager.py`); on reconnect, the client always
requests a fresh `snapshot` rather than assuming delta continuity
(architecture.md invariant 6).
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class EventType(str, Enum):
    SNAPSHOT = "snapshot"
    CONJUNCTION_ALERT = "conjunction_alert"
    NEGOTIATION_MESSAGE = "negotiation_message"
    RESOLUTION = "resolution"
    ERROR = "error"


class WebSocketEnvelope(BaseModel):
    type: EventType
    sequence: int
    payload: Any


class ErrorPayload(BaseModel):
    message: str
    code: str | None = None
