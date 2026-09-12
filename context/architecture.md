# Architecture

## Stack

| Layer | Tool | Purpose |
|---|---|---|
| Backend framework | FastAPI (Python 3.11+) | REST + WebSocket server, async-native |
| Orbital propagation | `sgp4` (Python) | Real SGP4 propagation from TLE data |
| Data validation | Pydantic | Schema enforcement for all agent messages and API payloads |
| LLM | Anthropic API (Claude), via `anthropic` Python SDK | Negotiation narration + structured tool-calling |
| Negotiation state machine | Hand-rolled enum/dispatch (swap for LangGraph only if the team already knows it) | Avoids unforced framework risk under time pressure |
| Local persistence | SQLite (or plain JSON files if faster to stand up) | Conjunction history, cached TLE/NOAA snapshots |
| Frontend framework | React + Vite | Fast dev server, team's existing comfort zone |
| Globe visualization | `react-globe.gl` | 3D globe, points/arcs/rings layers for satellites, orbits, alerts |
| Client-side propagation (optional) | `satellite.js` | Smooth client-side orbit animation without full backend round-trips |
| Styling | Tailwind CSS | Fast theming, dark space aesthetic |
| Frontend state | Zustand | Lightweight store for live WebSocket state |
| Language | TypeScript (frontend), Python (backend) | — |

---

## Folder Structure

```
/backend
  /app
    main.py                 → FastAPI app entrypoint, WebSocket route registration
    /agents
      monitor_agent.py       → Conjunction Monitor Agent (deterministic, no LLM)
      operator_agent.py      → Satellite Operator Agent (LLM narration + tool-calling)
      validation_agent.py    → Cascade/Safety Validation Agent (deterministic)
      cost_functions.py      → yield_score, delta_v calculations — pure functions, unit-testable
    /data
      celestrak.py           → CelesTrak TLE fetch + cache
      noaa.py                → NOAA Kp-index fetch + cache (Phase 2)
      scenario.py             → Scripted/seeded demo conjunction generator
      cache/                  → Cached TLE/NOAA snapshots (committed for demo reliability)
    /schemas
      conjunction.py          → ConjunctionAlert Pydantic model
      negotiation.py          → NegotiationMessage, Resolution Pydantic models
    /orchestrator
      orchestrator.py         → Owns negotiation session state, dispatches between agents
      websocket_manager.py    → Connection management, sequence numbering, reconnect handling
    /storage
      db.py                    → SQLite connection + queries (history log)
  requirements.txt

/frontend
  /src
    /components
      /globe                 → One configurable Globe component (live/conjunction/trajectory modes)
      /negotiation            → Negotiation console (two-column transcript, round tracker)
      /conjunction             → Conjunction details cards
      /history                 → History table
      /shared                  → Buttons, cards, badges, nav — shared UI primitives
    /pages
      Landing.tsx
      Monitor.tsx
      Negotiate.tsx
      Trajectory.tsx
      History.tsx
      About.tsx
    /store
      useNegotiationStore.ts   → Zustand store for live negotiation/globe state
    /lib
      websocket.ts              → WebSocket client hook, reconnect + sequence handling
      propagate.ts               → satellite.js wrapper for client-side propagation (if used)
    App.tsx
    main.tsx
  package.json
```

---

## System Boundaries

| Folder | Owns | Does NOT do |
|---|---|---|
| `agents/` | Agent reasoning logic (deterministic + LLM) | Never touches WebSocket transport directly — emits events to the orchestrator |
| `orchestrator/` | Session state, event sequencing, WebSocket broadcast | Never computes physics or negotiation math itself — delegates to agents |
| `data/` | External data fetch + caching | Never makes negotiation decisions |
| `components/` (frontend) | Rendering + local UI state | Never calls external APIs directly — goes through `store/` and `lib/websocket.ts` |
| `store/` (frontend) | Live state derived from WebSocket messages | Never contains business/negotiation logic — that lives entirely in the backend |

---

## Data Flow

```
// Conjunction detection → negotiation → resolution
1. celestrak.py fetches/loads cached TLEs
2. monitor_agent.py propagates via sgp4, detects conjunctions below threshold
3. monitor_agent.py → emits ConjunctionAlert → orchestrator.py
4. orchestrator.py → creates NegotiationSession, invokes two operator_agent.py instances
5. Each operator_agent.py → computes yield_score via cost_functions.py (deterministic)
                          → calls Anthropic API with yield_score as tool input → gets justification_text
6. operator_agent.py → emits NegotiationMessage → orchestrator.py → broadcast over WebSocket
7. orchestrator.py compares yield_scores after each round; on convergence or round cap →
   validation_agent.py re-runs sgp4 lookahead on proposed maneuver
8. validation_agent.py → approves | rejects_secondary_risk | approved_no_action
   → if rejected: loop back to step 5 with added constraint
   → if approved: orchestrator.py emits Resolution → broadcast → frontend updates globe to green
9. storage/db.py logs the full session for the History page
```

---

## Database Schema

**conjunctions**
| Column | Type | Notes |
|---|---|---|
| id | TEXT (PK) | UUID |
| primary_id | TEXT | NORAD catalog number |
| secondary_id | TEXT | NORAD catalog number |
| tca_utc | TEXT | ISO timestamp, time of closest approach |
| miss_distance_km | REAL | |
| relative_velocity_kmps | REAL | |
| status | TEXT | `alerted \| negotiating \| resolved \| escalated \| stood_down` |
| created_at | TEXT | ISO timestamp |

**negotiation_messages**
| Column | Type | Notes |
|---|---|---|
| id | TEXT (PK) | UUID |
| conjunction_id | TEXT (FK → conjunctions.id) | |
| agent_id | TEXT | `operator_A \| operator_B \| validation` |
| round | INTEGER | |
| yield_score | REAL | nullable for validation-agent rows |
| justification_text | TEXT | |
| proposed_action | TEXT | `maneuver \| stand_down \| reject \| approve` |
| created_at | TEXT | ISO timestamp |

**resolutions**
| Column | Type | Notes |
|---|---|---|
| id | TEXT (PK) | UUID |
| conjunction_id | TEXT (FK → conjunctions.id) | |
| maneuvering_agent | TEXT | which satellite moves |
| maneuver_type | TEXT | |
| delta_v_mps | REAL | |
| execution_time_utc | TEXT | |
| expected_min_distance_km | REAL | |
| residual_risk | REAL | |
| rationale_text | TEXT | |
| status | TEXT | `approved \| approved_no_action \| no_safe_maneuver_found` |

---

## Storage

No file/blob storage needed for MVP. Cached TLE/NOAA snapshots are plain JSON files under `backend/app/data/cache/`, committed to the repo well before the demo per the risk-mitigation plan.

---

## Authentication

None for MVP — this is a public demo dashboard with no per-user data. If added later, a simple session-based auth would gate nothing except potential future "save my view" features; it is explicitly out of scope for the hackathon build.

---

## Client Pattern

```typescript
// frontend/src/lib/websocket.ts
export function useAegisSocket(url: string) {
  // connects, handles auto-reconnect, discards out-of-sequence messages,
  // requests a full state snapshot on reconnect (never assumes delta continuity)
}
```

```python
# backend/app/orchestrator/websocket_manager.py
# broadcasts include a monotonically increasing sequence number per session;
# on new client connection, always send a full snapshot before streaming deltas
```

---

## Key Integration Patterns

**CelesTrak** — no auth, simple GET:
```
GET https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=json
```
Cache the response; treat as the source of truth for the curated demo object set.

**NOAA SWPC (Phase 2)** — no auth:
```
GET https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json
```

**Anthropic API** — tool-calling pattern: the operator agent's LLM call includes a `compute_yield_score` tool definition; the agent runs the deterministic function itself and passes the result into the prompt/tool-result, then asks the LLM only to narrate/justify — the LLM never independently produces the yield_score value.

---

## Invariants

1. Any number that affects a safety decision (Δv, miss distance, yield_score) comes from deterministic Python code, never directly from LLM output.
2. `agents/` never talks to the WebSocket layer directly — it emits events through `orchestrator/`.
3. Frontend `components/` never call external APIs directly — all data comes through `store/` fed by the WebSocket client.
4. Every negotiation round is capped (default 3); non-convergence escalates to a deterministic tie-break rule, never an infinite loop.
5. The Validation Agent can approve "no action" as a valid outcome — approve/reject of a burn is not the only two options.
6. On WebSocket reconnect, the frontend always requests a full state snapshot rather than assuming delta continuity.
7. All timestamps are UTC end-to-end, frontend and backend.
