from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.orchestrator.orchestrator import MONITOR_SESSION_ID, Orchestrator, negotiation_session_id
from app.orchestrator.websocket_manager import ConnectionManager

app = FastAPI(title="Aegis")

connection_manager = ConnectionManager()
orchestrator = Orchestrator(connection_manager)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/trajectory/{conjunction_id}")
async def get_trajectory_simulation(conjunction_id: str) -> dict:
    from app.data.trajectory import simulate_seeded_conjunction_trajectory
    result = simulate_seeded_conjunction_trajectory()
    return result.model_dump()


@app.get("/api/history")
async def get_history_list(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    from app.storage.db import get_history
    return get_history(status_filter=status, limit=limit, offset=offset)


@app.get("/api/history/{conjunction_id}")
async def get_history_detail(conjunction_id: str) -> dict:
    from fastapi import HTTPException
    from app.storage.db import get_full_session_details
    details = get_full_session_details(conjunction_id)
    if not details:
        raise HTTPException(status_code=404, detail="Conjunction session not found")
    return details


@app.websocket("/ws/echo")
async def echo_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/monitor")
async def monitor_socket(websocket: WebSocket) -> None:
    # TODO: once the orchestrator tracks real session state, this snapshot
    # should reflect currently-known conjunctions rather than an empty list.
    snapshot_payload = {"conjunctions": []}
    await connection_manager.connect(MONITOR_SESSION_ID, websocket, snapshot_payload)
    try:
        # Simplest trigger for now: broadcast on connect. Every new connection
        # re-broadcasts to all clients in the session — fine for the current
        # single-alert mock, revisit once B3 tracks per-alert delivery state.
        await orchestrator.broadcast_conjunction_alerts(MONITOR_SESSION_ID)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(MONITOR_SESSION_ID, websocket)


@app.websocket("/ws/negotiation/{conjunction_id}")
async def negotiation_socket(
    websocket: WebSocket, conjunction_id: str, force_rejection: bool = False
) -> None:
    # `force_rejection` is a verification knob (see NegotiationEngine's own
    # force_initial_rejection param) — connect with ?force_rejection=true to
    # exercise the validation-reject / re-negotiation path over the socket.
    session_id = negotiation_session_id(conjunction_id)
    snapshot_payload = {"messages": [], "resolution": None}
    await connection_manager.connect(session_id, websocket, snapshot_payload)
    try:
        await orchestrator.run_negotiation_session(
            conjunction_id, session_id, force_rejection=force_rejection
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id, websocket)
