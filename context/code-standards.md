# Code Standards

Engineering conventions for Aegis, covering both the FastAPI backend (Python) and React frontend (TypeScript). The goal is consistency across a fast-moving hackathon build, not bureaucracy — apply judgment where a rule would slow down real progress.

---

## Engineering Mindset

- Read the relevant context file (`architecture.md`, `ui-tokens.md`/`ui-rules.md`) before starting a new feature.
- Build one feature at a time per `build-plan.md`; verify it works before moving to the next.
- Keep physics/negotiation math in small, pure, testable functions (`cost_functions.py`) — never buried inside LLM prompts or route handlers.
- Prefer clean and readable over clever — this code needs to survive live debugging at 2am.
- When something breaks, fix the root cause once rather than patching around it repeatedly.
- Cached/fallback paths (per `architecture.md` §invariants) are not optional edge-case handling — they're the actual demo-day path. Build and test them early, not last.

---

## Python / FastAPI

- Type hints everywhere; Pydantic models for all request/response and internal event payloads.
- `async def` for all route handlers and any I/O (HTTP fetch, WebSocket send).
- Never let an unhandled exception crash the negotiation loop — catch at the orchestrator level, log, and emit a degraded-but-valid state (e.g. escalate) rather than hanging.
- Deterministic functions (`cost_functions.py`, `monitor_agent.py`'s conjunction math) should have zero LLM/network calls — pure, unit-testable functions of their inputs.
- LLM calls live only in `operator_agent.py`'s narration step; always validate the tool-call response against a Pydantic schema before using it, with one retry on failure, then fall back to the deterministic result with default narration text.

```python
# Route handler pattern
@app.websocket("/ws/negotiation/{session_id}")
async def negotiation_socket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        await orchestrator.stream_session(session_id, websocket)
    except WebSocketDisconnect:
        orchestrator.handle_disconnect(session_id)
```

---

## TypeScript / React

- Strict mode on; avoid `any` — if a type is genuinely unknown, use `unknown` and narrow it.
- Functional components with hooks; no class components.
- One component per file; colocate small subcomponents only if they're not reused elsewhere.
- Keep components presentational where possible — pull WebSocket/state logic into `store/` and `lib/`, not inline in JSX-heavy components.

```typescript
// Component file order
// 1. imports (external, then internal)
// 2. types
// 3. component function
import { useState } from 'react';
import { useNegotiationStore } from '@/store/useNegotiationStore';

type Props = {
  conjunctionId: string;
};

export function ConjunctionDetails({ conjunctionId }: Props) {
  // ...
}
```

---

## File & Folder Naming

- Backend: `snake_case.py` for files, `PascalCase` for Pydantic models/classes.
- Frontend: `PascalCase.tsx` for components, `camelCase.ts` for hooks/utilities, folders in `kebab-case` where they contain multiple related files.

---

## Error Handling

- Backend: never swallow exceptions silently — log with a clear prefix (`[monitor_agent]`, `[operator_agent]`, `[orchestrator]`) so demo-day issues are traceable fast.
- Frontend: WebSocket errors surface a visible "reconnecting..." state rather than failing silently (per `architecture.md` invariant 6).
- User-facing errors (if any surface, e.g. "no safe maneuver found") should be treated as legitimate states with their own UI, not generic error banners.

---

## Environment Variables

| Variable | Used in |
|---|---|
| `ANTHROPIC_API_KEY` | backend — Anthropic SDK calls |
| `CELESTRAK_BASE_URL` | backend — data fetch (has a sane default, override optional) |
| `NOAA_KP_URL` | backend — Phase 2 |
| `VITE_WS_URL` | frontend — WebSocket connection target |

Never hardcode keys in source. Frontend env vars must use the `VITE_` prefix to be exposed to the client bundle.

---

## Constants

Centralize demo-relevant thresholds rather than scattering magic numbers:
```python
# backend/app/agents/cost_functions.py
CONJUNCTION_THRESHOLD_KM = 5.0
HYSTERESIS_CLEAR_KM = 4.0
MAX_NEGOTIATION_ROUNDS = 3
VALIDATION_LOOKAHEAD_HOURS = 6
```

---

## Comments

Write comments that explain *why*, not *what* — especially around the deterministic-vs-LLM boundary and any deliberately simplified/simulated data, since that's the thing most likely to draw judge questions.

---

## Dependencies

Approved for this build — extend the list here if you add something new, so the team stays in sync:

**Backend:** `fastapi`, `uvicorn`, `sgp4`, `pydantic`, `anthropic`, `httpx`, `websockets`
**Frontend:** `react`, `vite`, `react-globe.gl`, `satellite.js`, `zustand`, `tailwindcss`

Keep the dependency list lean — every new package is one more thing that can break on the venue laptop.
