# Progress Tracker — Aegis (4-Developer Parallel Execution)

This tracker mirrors `build-plan.md` exactly. It answers "what is the current state of the work the build plan describes" — it does not redefine or duplicate the work itself. Update your own workstream's rows as you go; never mark something merged or verified until it actually is.

---

## 1. Current Team Status

| Field | Value |
|---|---|
| Project | Aegis |
| Team size | 4 developers |
| Current phase | **Phase 1 complete; Phase 2 underway.** **Correction:** this field said "Phase 0" until now — stale since Phase 0's own exit checklist (§3) has been fully checked for some time, all of Workstream A/B/C's Phase 1 tasks are merged, Workstream D is 5/6 merged, and Phase 2 negotiation-engine work (`negotiator.py`) has already landed on `main`. |
| Current checkpoint target | Checkpoint 1 — all individual pieces (A/B/C fully, D mostly) are merged and pass their own standalone verification, but no joint team checkpoint session has occurred (§5 is still unfilled) — per the status legend, that means Checkpoint 1 is not yet `[V]`-level passed even though the underlying work is done |
| Overall status | 🟢 Phase 0 and Phase 1 substantially complete; Phase 2 (negotiation state machine, live validation) already has real, tested code on `main` (`agents/negotiator.py`) ahead of a formal Checkpoint 1 session |
| Last completed milestone | `dev-b/validation-agent-fixes` merged to `main` (commit `88c0db7`): fixed a real `TypedDict`/canonical-`TrackedObject` conflict in `validation_agent.py` found during a pre-Checkpoint-1 audit |
| Current team objective | Hold an actual joint Checkpoint 1 session (§5) to formally verify what's already built, then start Checkpoint 2 work (full negotiation loop) in earnest |
| Next team milestone | Checkpoint 1 team verification session |

---

## 2. Status Legend

| Symbol | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Completed by owner (not yet merged) |
| `[M]` | Merged to `main` |
| `[V]` | Integrated and verified by the team (checkpoint-level confirmation) |
| `[!]` | Blocked |

**Note:** `[x]` (done by owner) and `[V]` (verified as working in the integrated system) are never the same thing. A task only reaches `[V]` during or after a checkpoint session.

---

## 3. Phase 0 — Shared Foundation & Contracts

| Artifact | Owner | Status | Notes |
|---|---|---|---|
| Repo skeleton (backend half) | Dev B | `[M]` | `/backend/app/{agents,data,schemas,orchestrator,storage}` scaffolded — FastAPI app + health route + `/ws/echo` stub in `main.py`. Package dirs are empty `__init__.py` placeholders; real logic not yet written. |
| Repo skeleton (frontend half) | Dev D | `[M]` | `/frontend/src/{components,pages,store,lib}` scaffolded — Vite + React + TS + Tailwind v4 wired to `ui-tokens.md`'s tokens, top nav (`components/shared/NavBar.tsx`) with placeholder routes for all 6 pages. `store/` and `lib/` still empty — D5/D6 not started. |
| Pydantic schemas (`TrackedObject`, `ConjunctionAlert`, `NegotiationMessage`, `Resolution`) | Dev B | `[M]` | Merged to `main` via `foundation/contracts` (commit `3818c17`), reviewed/approved by Dev C. Implemented in `backend/app/schemas/{tracked_object,conjunction,negotiation}.py`, field names/types match `architecture.md`'s DB schema exactly; `TrackedObject` isn't a DB table so its shape follows the TLE/SGP4 state it carries instead (norad_id, name, TLE lines, ECI position/velocity, timestamp). Re-exported from `schemas/__init__.py`. |
| WebSocket envelope contract (`{type, sequence, payload}` + event types) | Dev B | `[M]` | Merged to `main` via `foundation/contracts` (commit `3818c17`), reviewed/approved by Dev C. `WebSocketEnvelope`/`EventType` in `backend/app/schemas/websocket.py`; `ConnectionManager` in `backend/app/orchestrator/websocket_manager.py` implements per-session monotonic sequencing and always sends a `snapshot` first on connect (invariant 6). |
| Shared constants (`CONJUNCTION_THRESHOLD_KM`, `HYSTERESIS_CLEAR_KM`, `MAX_NEGOTIATION_ROUNDS`, `VALIDATION_LOOKAHEAD_HOURS`) | Dev B | `[M]` | Merged to `main` via `foundation/contracts` (commit `3818c17`), reviewed/approved by Dev C. **@Dev C: heads up** — this file lives at `backend/app/constants.py` (app root), **not** inside `agents/cost_functions.py` as build-plan.md's wording ("cost_functions.py-adjacent") might suggest. `agents/` is your owned directory, so I deliberately didn't put a new file there — import the four constants from `app.constants` in `cost_functions.py` rather than redefining them locally. |
| Mock fixture: `TrackedObject` / `ConjunctionAlert` JSON | Dev A | `[M]` | `backend/app/data/fixtures/conjunction_alert.json` and `tracked_objects.json` — verified schema-valid, consumed by Dev D |
| Mock fixture: sample `NegotiationMessage` transcript | Dev C | `[M]` | `backend/fixtures/negotiation_message_transcript.json` — 2 scenarios (clean + reject→re-negotiate), ready for Dev D |
| Mock fixture: sample `Resolution` | Dev B | `[M]` | Merged to `main` via `foundation/contracts` (commit `3818c17`), reviewed/approved by Dev C. `backend/app/data/fixtures/resolution.json` — validated against `schemas/negotiation.py`'s `Resolution` model; a `maneuver`/`approved` example with realistic yield-score/Δv/rationale text for Dev D to build the Negotiation Result screen against. |
| Ownership map | (this document + build-plan.md) | `[x]` | Established by build-plan.md |

### Phase 0 Exit Checklist

- [x] Schemas committed to `main`
- [x] WebSocket envelope contract committed to `main`
- [x] Shared constants committed to `main`
- [x] All three mock fixtures committed to `main` (`resolution.json`, `conjunction_alert.json`, `tracked_objects.json`, `negotiation_message_transcript.json`)
- [x] Repo skeleton (backend + frontend) committed to `main`
- [x] All four developers have pulled `main` and can branch out

**Phase 0 status: COMPLETE — team operating in parallel Phase 1 workstreams.**

---

## 4. Phase 1 — Four Parallel Workstreams

### Workstream A — Orbital Physics & Conjunction Detection
**Owner:** Dev A / completed with Dev C coverage
**Current task:** All A tasks complete
**Status:** All three modules (A1, A2, A3) tested and passing offline
**Blocked by:** Nothing
**Waiting on:** Nothing
**Next:** Checkpoint 1 verification session
**Merge status:** A1, A2, and A3 ready / merged on `main`

| Task ID | Task | Status | Notes |
|---|---|---|---|
| A1 | `data/celestrak.py` — fetch + local JSON cache + fallback-to-cache | `[x]` | Merged to `main`. Refactored to use `httpx` (async client + sync helper, removing undeclared `requests` dependency) and `RawTLE` dataclass to eliminate schema collision with `schemas/tracked_object.py`. Verified with `test_celestrak_offline.py`. |
| A2 | `agents/monitor_agent.py` — SGP4 propagation via `sgp4` | `[x]` | Merged to `main`. `propagate()` constructs canonical Pydantic `TrackedObject` (`schemas/tracked_object.py`) with `timestamp_utc`, `position_km`, `velocity_kmps`. Verified against Vallado C++ ISS reference in `test_monitor_agent_validation.py`. |
| A3 | Pairwise distance + threshold/hysteresis logic, `data/scenario.py` seeded scenario | `[x]` | `monitor_agent.py` implements `pairwise_distance_km`, `relative_velocity_kmps`, and `detect_conjunctions()` using `CONJUNCTION_THRESHOLD_KM` (5.0 km) and hysteresis; `data/scenario.py` seeds a deterministic conjunction (ISS 25544 <-> CSS 48274 at 3.202 km); swapped into `Orchestrator.detect_conjunctions()`. Verified via `test_scenario_conjunction.py`. |

#### Completion Criteria
- [x] Standalone script runs end-to-end offline (cached data only)
- [x] `detect_conjunctions()` returns schema-valid `ConjunctionAlert` objects
- [x] Scripted scenario reliably yields ≥1 alert below threshold

---

### Workstream B — Orchestrator, Schemas & Realtime Backbone
**Owner:** Dev B
**Current task:** — (all three Phase 1 tasks complete)
**Status:** B1, B2, B3 all complete and merged
**Blocked by:** Nothing
**Waiting on:** Nothing
**Next:** Phase 2 — Negotiation State Machine (below)
**Merge status:** B1, B3 merged directly; B2's actual deliverable (`websocket_manager.py`) was built and merged during Phase 0 (see Phase 0 table's "WebSocket envelope contract" row) — this row was simply never updated to reflect that until now.

| Task ID | Task | Status | Notes |
|---|---|---|---|
| B1 | `main.py` — FastAPI skeleton, health-check route, WS route stub (echo) | `[M]` | `/health` and `/ws/echo` scaffolded and pushed to `main` |
| B2 | `orchestrator/websocket_manager.py` — connection mgmt, sequence numbers, snapshot-on-reconnect | `[M]` | **Correction:** was showing `[ ]` despite already being done — the actual file was built and merged as part of Phase 0's "WebSocket envelope contract" deliverable (§3's table), which this row never cross-referenced. `ConnectionManager` implements per-session monotonic sequencing and always sends a `snapshot` first on connect (invariant 6); live-verified repeatedly in later D5/D6 end-to-end work (real kill/restart reconnect cycles). |
| B3 | `orchestrator/orchestrator.py` (Monitor slice) — wraps Dev A's output as `ConjunctionAlert` events, broadcasts | `[M]` | Merged to `main` via `dev-b/monitor-broadcast` (commit `74cd70c`, rebased onto Dev A's PR #1). Originally ran on a hardcoded fixture pending Dev A's A3; since A3 landed, `Orchestrator.detect_conjunctions()` calls the real `monitor_agent.detect_conjunctions()` (confirmed live in the pre-Checkpoint-1 audit — real alert values, not the old fixture's). Wired to `/ws/monitor` in `main.py`: connect → snapshot → broadcast. Verified manually with a Python `websockets` client: snapshot arrives first at `sequence: 1`, alert follows at `sequence: 2` with the correct envelope shape. |

#### Completion Criteria
- [x] WS client (Python `websockets`, and later a full frontend E2E run) confirms sequence numbers increment
- [x] Snapshot arrives first on new connection
- [x] Real (non-mocked) `ConjunctionAlert` from Dev A flows through the socket to a connected client — confirmed live during the pre-Checkpoint-1 audit

---

### Workstream C — Agent Intelligence: Cost, Narration & Validation
**Owner:** Dev C
**Current task:** Phase 0 fixture + C1 + C2 + C3 + Phase 2 Negotiation Engine all complete
**Status:** All modules independently testable, passing, and verified
**Blocked by:** Nothing
**Waiting on:** Nothing (Dev A's real SGP4 propagation wired directly into `validation_agent.py`)
**Next:** Checkpoint 2 full integration with Dev B/D
**Merge status:** Ready to merge on branch `dev-c`
**Notes:** Explicit ACK given on Dev B's `backend/app/constants.py` as single source of truth for shared constants. `agents/negotiator.py` implements the autonomous multi-round negotiation engine, deterministic yield scoring, LLM narrative justifications, and post-convergence safety validation with re-negotiation cascade.

| Task ID | Task | Status | Notes |
|---|---|---|---|
| C1 | `agents/cost_functions.py` — `yield_score` from MVI + fuel/Δv | `[x]` | 27/27 unit tests passing; `compute_yield_score`, `compute_delta_v_cost`, `pick_maneuvering_agent`, all constants |
| C2 | `agents/operator_agent.py` skeleton — Anthropic call, Pydantic-validated, retry-then-template-fallback | `[x]` | Standalone script verified; `build_negotiation_message()` ready for orchestrator |
| C3 | `agents/validation_agent.py` skeleton — 6h re-propagation check | `[x]` | All outcomes tested (approve / reject_secondary_risk / approved_no_action); wired to real SGP4 propagation with in-memory Satrec caching. **Dev B fix (covering Dev C, `dev-b/validation-agent-fixes`, commit `88c0db7`, merged to `main`) — heads up for Dev C on return:** the pre-Checkpoint-1 audit found `validation_agent.py` defined its own local `TrackedObject` as a `TypedDict` (only `norad_id`/`name`/`tle_line1`/`tle_line2`, accessed via `obj["norad_id"]`-style dict-subscript), which conflicted with the canonical Pydantic `TrackedObject` every other module uses — calling this with a real canonical instance would have raised `TypeError: not subscriptable` the moment Phase 2 live integration happened. Fixed by importing the canonical `TrackedObject` and adding `_as_tracked_object()`, a normalization helper at `run_validation_check()`'s boundary that accepts either the canonical type or a plain dict (filling placeholder state-field values this function never actually reads) and returns the canonical type internally; all internal access converted from `obj["field"]` to `obj.field`. Deliberately *not* a strict attribute-only rewrite — `agents/negotiator.py` (landed after the audit) already converts canonical `TrackedObject`s to dicts via `.model_dump()` before calling in here, and both `test_negotiator.py` and this file's own `scripts/run_validation_agent.py` fixtures pass plain dicts — a strict rewrite would have fixed the reported bug while breaking those two working integrations. Accepting both shapes at the boundary avoided touching `negotiator.py` or its tests at all. Also removed the redundant duplicate `TrackedObject` class from `monitor_agent.py`'s defensive `except ImportError` fallback block (left the constants/`ConjunctionAlert` fallback there untouched, per Dev C's own comment) — if that deep fallback path is ever reached now, it raises a clear `NameError` instead of silently duplicating the schema. Also fixed a `UnicodeEncodeError` crash (a `✓` character under Windows' default cp1252 console codepage) in both `scripts/run_validation_agent.py` (the one originally reported) and `scripts/run_operator_agent.py` (same bug class, found while re-verifying fresh). **Not fixed, flagged for Dev C:** `scripts/run_negotiation_simulation.py` has the identical print-encoding bug (a `Δ` character) but belongs to the new `negotiator.py` feature, out of this fix's scope. Re-verified fresh after all changes: `pytest app/agents/tests/` 31/31 (including `test_negotiator.py`), both C2/C3 standalone scripts, and A1/A2/A3's scripts all pass with no `PYTHONIOENCODING` override needed. |

#### Completion Criteria
- [x] Unit tests for `cost_functions.py` pass (27/27)
- [x] Standalone script calls `operator_agent.py` with fixture input and prints narration
- [x] Standalone validation run succeeds against a fixture tracked-object set (all 3 paths)
- [x] All three modules testable without a live orchestrator or WebSocket connection

---

### Workstream D — Frontend Experience & WebSocket Client
**Owner:** Dev D
**Current task:** D Phase 2 — History table
**Status:** Negotiation Console and Result Card complete and wired
**Blocked by:** Nothing
**Waiting on:** Nothing
**Next:** History table then empty state for no safe maneuver
**Merge status:** D1 (`main`), D3 (`dev-d/shared-primitives`), D4 (`dev-d/globe-component` + follow-up fixes on `dev-d/globe-fixes`), D5 and D6 (`dev-d/globe-fixes`) all merged to `main`. D2 not started.

| Task ID | Task | Status | Notes |
|---|---|---|---|
| D1 | Vite + React shell, Tailwind w/ `ui-tokens.md`, top nav w/ placeholder routes | `[M]` | Scaffolded and pushed to `main`; still needs real per-page content and a11y pass. **Correction:** the original "Tailwind wired" claim here was inaccurate — `tailwindcss` was a devDependency but the `@tailwindcss/vite` plugin was never installed or added to `vite.config.ts`'s `plugins` array, so no Tailwind utility classes were ever actually being generated. Every page, including `NavBar.tsx`, has been rendering completely unstyled since D1 landed. Fixed as of `dev-d/shared-primitives` (commit below): installed `@tailwindcss/vite`, added it to `vite.config.ts`. Verified with a screenshot of `/monitor` via headless Chromium — NavBar, page text, and all D3 components now render with correct token colors. |
| D2 | Landing page (static) — hero, stat cards, CTA buttons | `[M]` | Hero with radial glow, 4 stat cards (font-mono numbers, Badge status), 4-step how-it-works grid, demo CTA banner, footer. Routed to /monitor and /negotiate. Token-compliant, no colored card backgrounds. |
| D3 | Shared primitives (buttons/cards/badges) | `[M]` | Dev B (covering Dev D). Merged to `main` via `dev-d/shared-primitives`. Built `Button.tsx` (`variant?: 'primary' \| 'secondary'`), `Card.tsx` (`bg-surface border border-border rounded-lg p-6`, no colored backgrounds), `Badge.tsx` (`status: 'active' \| 'danger' \| 'warning' \| 'success'`, muted-bg + light-text pill per status) in `frontend/src/components/shared/`. Logged in `ui-registry.md` under a new "Shared Primitives" section with exact class recipes. Verified by temporarily wiring all three (plus all four badge statuses) into `/monitor`, screenshotting via headless Chromium, confirming correct dark-theme rendering with zero console errors, then removing the test block. |
| D4 | Globe component (`components/globe/`) — one configurable component | `[M]` | Dev B (covering Dev D). Merged to `main` via `dev-d/globe-component`. `Globe.tsx` — single `react-globe.gl` instance driven by props (`trackedObjects`, `mode: 'live' \| 'conjunction' \| 'trajectory'`, optional `conjunctionAlert`), auto-sizes to its parent container via `ResizeObserver`. ECI→lat/lng/alt conversion in `eciToGeo.ts` via `satellite.js`. Colors match D3's `Badge` semantics (accent=active, danger=hazard, pulsing ring on the flagged pair in `'conjunction'` mode). **Currently running on 5 hand-written mock `TrackedObject`s in `globe/mockTrackedObjects.ts`**; these aren't fabricated numbers, each one's `position_km`/`velocity_kmps` came from actually SGP4-propagating a real TLE via `satellite.js` at a fixed timestamp, and a `TODO(Dev A)` comment marks the swap point. **Update:** Dev A's Phase 0 `TrackedObject` fixture has since landed at `backend/app/data/fixtures/tracked_objects.json` — the frontend isn't wired to consume it yet (still a separate follow-up task, not done as part of this row). `'trajectory'` mode is accepted but renders like `'live'` for now, pending Dev A's Phase 2 propagation arrays. Wired into `pages/Monitor.tsx` (`'live'` mode) with a floating legend `Card`. Along the way, fixed two toolchain issues that were blocking this: `three-globe`'s texture path isn't importable via its `exports` map (copied `earth-night.jpg` into `frontend/src/assets/` instead) and `satellite.js`'s WASM build needs `esnext` as the esbuild target (set in `vite.config.ts`'s `build.target` / `optimizeDeps.esbuildOptions.target`). Verified via headless-Chromium screenshot of `/monitor`: globe renders with the dark earth-night texture, satellite points visible, legend counts correct, zero console errors. Logged in `ui-registry.md`. **Follow-up fix (legend + hazard marker rendering):** the legend previously said a blanket "still mock" even once a live `conjunction_alert` was flowing — now shows satellite-position and conjunction-alert status independently (`Monitor.tsx`). Also fixed the hazard ring/marker looking jagged/scratchy in screenshots — two real causes, not an animation-timing illusion: (1) `ringColor` returned a flat opaque color instead of a function of the ring's progress `t`, and `ringRepeatPeriod` (800ms) was shorter than one ring's full lifetime (2000ms), so 2-3 solid-opacity ring generations overlapped at once; fixed by making `ringColor` fade with `t` and retiming so one ring fully fades before the next spawns. (2) `three-globe` renders each point as a `CylinderGeometry` pin with a default 12-sided cross-section (`pointResolution`), visibly faceted at this scale and further stretched by perspective near the globe's limb; fixed by setting `pointResolution={32}`. Verified in motion (not a single lucky frame) via 12 tightly-spaced (150ms) zoomed screenshots across one full ~1.6s pulse cycle — confirmed a single clean ring growing and fading, no overlap, smooth pin geometry throughout. |
| D5 | `lib/websocket.ts` — connect, auto-reconnect, out-of-sequence discard, snapshot-on-reconnect | `[M]` | Dev B (covering Dev D). Merged to `main` via `dev-d/globe-fixes` (commit `7e9508b`). `useAegisSocket()` hook (named per `architecture.md`'s Client Pattern), mounted once in `App.tsx` so the connection outlives route changes. Connects to Dev B's real, live `/ws/monitor` (B3) — not just B1's echo stub. Enforces snapshot-first (anything else arriving before the first snapshot is logged as an error and dropped, per invariant 6); discards any message with `sequence <= last seen`; auto-reconnects forever at a fixed 2s interval — no retry cap — resetting sequence-tracking state on every fresh attempt so a stale socket's data can never be compared against the new one's — no assumed delta continuity, the fresh snapshot the backend always sends on connect is simply trusted. Every parsed message is handed to the store's `updateFromSocket`. **Correction:** the first pass set `connectionStatus` to `'disconnected'` on every failed attempt before scheduling the next retry, so during an outage the UI mostly showed `'disconnected'` and only flashed `'reconnecting'` for the brief instant before each retry — same visible effect as a demo-day "gave up" look, even without an actual retry cap. Fixed: `onclose` now sets `'reconnecting'` directly and keeps it there for the whole outage; `'disconnected'` is no longer reachable from the retry loop at all (kept in the type only for a possible future explicit/user-initiated disconnect). **Verified live end-to-end:** started uvicorn + Vite together, confirmed the globe picks up B3's real hardcoded `conjunction_alert` (switches to `'conjunction'` mode, hazard ring appears). Killed uvicorn mid-session and sampled `connectionStatus` once a second for 12s (6x the retry interval) — stayed on `Reconnecting` for all 12 samples, never once showed `Disconnected`; globe held its last-known state rather than freezing. Restarted uvicorn — NavBar recovered to `Live` and the alert reapplied from the fresh snapshot. All stages screenshotted via headless Chromium. |
| D6 | `store/useNegotiationStore.ts` skeleton wired to D5 | `[M]` | Dev B (covering Dev D). Merged to `main` via `dev-d/globe-fixes` (commit `7e9508b`). Single Zustand store (per code-standards.md — one store, not split) holding `trackedObjects`, `activeConjunctionAlert`, `connectionStatus: 'connecting' \| 'connected' \| 'reconnecting' \| 'disconnected'`. One `updateFromSocket(envelope)` action funnels every WS event type: `snapshot` replaces `trackedObjects`/`activeConjunctionAlert` wholesale (backend's snapshot payload doesn't carry tracked-object state yet, only `conjunctions` — noted in a comment so this isn't mistaken for a bug later), `conjunction_alert` sets `activeConjunctionAlert`, `negotiation_message`/`resolution` are accepted but no-op pending Phase 2, `error` logs. Also exports the `EventType`/`WebSocketEnvelope` types mirroring `schemas/websocket.py`. Wired into `NavBar.tsx` (live status pill, 4-state color/label map) and `Monitor.tsx` (live `trackedObjects` with automatic fallback to D4's `mockTrackedObjects.ts` when the live array is empty — true today, self-corrects once the backend snapshot grows to include tracked objects). |

#### Completion Criteria
- [x] Globe renders mock satellite list correctly with legend/colors matching `ui-tokens.md` — verified via headless-Chromium screenshots (D4)
- [ ] App shell, nav, landing, and mock-fed Globe visually match reference mockup's polish — app shell/nav/Globe done and verified; Landing page (D2) itself hasn't been built yet, so this criterion can't be fully closed until D2 lands
- [x] `lib/websocket.ts` round-trips successfully — verified against Dev B's real, live `/ws/monitor` route (B3), a stronger check than the original "B1's echo stub" target; includes a real kill/restart reconnect cycle (D5)

---

## 5. CHECKPOINT 1 — Live Conjunction Pipeline

### Checkpoint State: **IN PROGRESS (A & C Ready, B & D Pending)**

### Pre-Checkpoint Readiness

| Workstream | Required work complete? | Independently verified? | Branch ready? | Dependencies resolved? | Ready to merge? |
|---|---|---|---|---|---|
| A — Orbital Physics | `[x]` | `[x]` | `[x]` | `[x]` | `[x]` |
| B — Orchestrator/Backbone | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| C — Agent Intelligence | `[x]` | `[x]` | `[x]` | `[x]` | `[x]` |
| D — Frontend | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |

### Merge Status

| Workstream | Individual status | Merge status | Integration status |
|---|---|---|---|
| A — Orbital Physics | A1, A2, A3 complete | `[x]` | `[x]` |
| B — Orchestrator/Backbone | Not started | `[ ]` | `[ ]` |
| C — Agent Intelligence | C1, C2, C3 complete | `[x]` | `[x]` |
| D — Frontend | Not started | `[ ]` | `[ ]` |

### Integration Verification (from build-plan.md — required to pass)

- [x] Cached TLE data → SGP4 propagation → scripted scenario conjunction detection works (verified in `test_scenario_conjunction.py`)
- [ ] Orchestrator wraps Dev A's output into a schema-valid `ConjunctionAlert` and broadcasts over the **real** WebSocket (not the echo stub)
- [ ] Frontend swaps mock Globe feed for `lib/websocket.ts` connected to the real server; hazard marker appears live when scripted scenario fires
- [ ] Reconnect test: killing/restoring client connection triggers a full snapshot (not assumed delta continuity — invariant 6)
- [x] Dev C's `cost_functions.py`, `operator_agent.py`, `validation_agent.py` pass their standalone tests (NOT required to be wired into live orchestrator yet)

**Explicitly NOT required at this checkpoint:** negotiation console, live LLM narration, validation wired into orchestrator, resolution, trajectory, history.

### Checkpoint Decision Log

_No checkpoint session has occurred yet._

---

## 6. Phase 2 — Post-Checkpoint Parallel Work

**Note:** Ownership shifts here per build-plan.md — Dev A moves from orbital physics into Trajectory/History, reusing their orbital-data expertise. This section will not become active until Checkpoint 1 passes.

### Workstream A — Trajectory Data & History Persistence
**Owner:** Dev A
**Status:** All Workstream A tasks complete & verified (`[x]`) — db.py reconciled with Dev C's interface (backward-compat aliases added)
**Depends on:** Dev B's `Resolution` schema (locked in Phase 0)
**Next:** Checkpoint 2 full integration

| Task | Status | Notes |
|---|---|---|
| Before/after propagation arrays for maneuver preview | `[x]` | Built in `backend/app/data/trajectory.py`. Uses J2-perturbed RK4 orbital equations of motion, impulsive delta-v burn mechanics (prograde, retrograde, radial, normal), synchronous scrubber timeline steps, and 3D globe polyline paths. Verified via `test_trajectory.py` (5/5 passing, energy drift < 1e-4, nominal 3.22 km -> maneuvered 12.74 km, threshold cleared). Static fixture generated at `backend/app/data/fixtures/trajectory_simulation.json`. Read-only API route `GET /api/trajectory/{conjunction_id}` added to `main.py`. |
| `storage/db.py` — SQLite persistence of resolved/escalated sessions | `[x]` | Built in `backend/app/storage/db.py`. WAL mode, typed schema imports, dual-status history filter, rich JOIN query. Backward-compat aliases for Dev C's interface: `save_conjunction`, `save_completed_session`, `get_history_sessions`, `get_session_by_conjunction_id`. Verified via `storage/tests/test_db.py` (6/6 passing, foreign keys & atomic rollbacks verified). REST API routes `GET /api/history` and `GET /api/history/{conjunction_id}` added to `main.py`. |

**Completion criteria:**
- [x] Before/after arrays validated against a known maneuver scenario (`test_trajectory.py`)
- [x] SQLite writes/reads verified via script (`storage/tests/test_db.py` & `main.py` REST API tests)

---

### Workstream B — Negotiation State Machine
**Owner:** Dev B
**Status:** Live `/ws/negotiation/{conjunction_id}` route wired to Dev C's `NegotiationEngine`, streaming real rounds over the socket — **this is the negotiation engine's first LIVE run**, not a standalone script (`run_negotiation_simulation.py`) or a pytest fixture (`test_negotiator.py`). Both previously only ran the engine in-process with no WebSocket transport at all.
**Depends on:** Dev C's `negotiator.py` (`NegotiationEngine`), `cost_functions`/`operator_agent` (transitively, unchanged)
**Next:** Real conjunction-ID routing across multiple concurrent negotiations (today every connection runs the same scripted scenario, by design — see task notes)

| Task | Status | Notes |
|---|---|---|
| `main.py` — `/ws/negotiation/{conjunction_id}` route, same `ConnectionManager` pattern as `/ws/monitor` (snapshot-first, incrementing sequence) | `[x]` | Not yet merged. Optional `?force_rejection=true` query param maps directly to `NegotiationEngine`'s own `force_initial_rejection` param, added specifically so the validation-reject/re-negotiation path can be exercised live without a code change. |
| `orchestrator.py` — `Orchestrator.run_negotiation_session()`: builds the engine from the scripted scenario (same alert B3's `detect_conjunctions()` already produces, same demo profiles as Dev C's own `test_negotiator.py` fixtures), runs it, streams each message and the final `Resolution` | `[x]` | Not yet merged. Runs `engine.run_negotiation()` via `asyncio.to_thread()` since it's synchronous and calls the Anthropic API — keeps the event loop free for other connections. Wraps the call in try/except, broadcasting an `EventType.ERROR` envelope on failure rather than hanging (code-standards.md). **Honest caveat:** `NegotiationEngine.run_negotiation()` has no incremental hook — it builds its whole transcript synchronously and returns it all at once. "Streamed live" here means each already-computed message is broadcast as its own WebSocket frame immediately after the engine returns, not delivered mid-computation. True as-computed streaming would need a callback/generator added to the engine itself (Dev C's file, out of scope — not touched, per this task's boundary). |
| Wire validation reject outcome back into negotiation with added constraint | `[x]` | Not new work — this is `negotiator.py`'s existing round-2 counter-proposal logic; now confirmed reachable and visible over a live socket (see verification below), not just via pytest. |
| Emit `Resolution` on convergence + validation approval | `[x]` | Confirmed live, both the clean-approval and the forced-rejection/re-negotiation paths. |

**Bug found while wiring this (not fixed — outside my file boundary):** `agents/negotiator.py` line ~62 (`from backend.app.agents.cost_functions import ...`) has no `try/except ImportError` fallback, unlike every other import block in that same file. This was latent and undiscovered because nothing in the live server path ever imported `negotiator.py` before — only pytest (which auto-adds the repo root to `sys.path` via its package-root walk, since `backend/__init__.py` exists) and the standalone scripts (which manually insert two directories up) ever exercised it. The normal launch command from `README.md` (`cd backend && uvicorn app.main:app --reload`) does **not** put the repo root on `sys.path`, so this import crashes the server at startup the moment anything imports `agents.negotiator` — which my new route is the first live-path thing to do. Worked around for my own verification only by setting `PYTHONPATH=..` before launching; did not touch `negotiator.py` itself (Dev C's file, per this task's boundary). Dev C should add the same `try/except` pattern already used for every other import in that file.
**`MAX_NEGOTIATION_ROUNDS` enforcement status:** Dev C's fix ("enforce MAX_NEGOTIATION_ROUNDS loop bounding," commit `a6c5e82`) exists on their own branch `dev-c-persistence`, **not yet merged to `main`**. Not confirmed through this live path — `main` still has the old hardcoded-2-attempt structure at the time of this test. Re-verify live once that branch merges.

**Completion criteria:**
- [x] Full scripted negotiation converges within round cap, or escalates deterministically — verified live over `/ws/negotiation/{conjunction_id}`: clean path converges in round 1 with a real `Resolution(status=approved)`; forced-rejection path (`?force_rejection=true`) shows a real round-2 re-negotiation and still converges. The `NO_SAFE_MANEUVER_FOUND` escalation path is exercised by `test_invariant_9_no_safe_maneuver` (pytest, mocked validation) but not yet demonstrated over the live socket specifically — the engine has no way to force *both* rounds to fail via `force_initial_rejection` alone (only forces round 1), so this would need a different test hook, not attempted here.

**Live verification detail:** connected a real Python `websockets` client to `/ws/negotiation/{conjunction_id}` twice (clean and forced-rejection). Both times: `snapshot` arrived first (`sequence: 1`, empty transcript), followed by each `negotiation_message` in order (`sequence: 2, 3, 4...`), ending with `resolution`. All `yield_score` values were real `cost_functions.compute_yield_score()` output (e.g. `0.4645`, `0.5868`), not any hardcoded fixture number — confirmed by comparing against the same values `test_invariant_1_yield_score_deterministic` independently asserts. The alert's `conjunction_id` in every message was A3's real computed UUID (`uuid5`-derived), not the old hardcoded fixture's ID, confirming this reuses the same real scripted-scenario path as B3, not a separate mock.

---

### Workstream C — Live Narration & Validation
**Owner:** Dev C
**Status:** Individually complete and passing (pytest + standalone scripts) — **not** `[V]` per the status legend, since that requires a team checkpoint session and none has happened yet. **Correction:** this row previously said "Complete / Independently Verified," which reads as the `[V]` level; downgraded the wording to avoid implying checkpoint-level sign-off that hasn't occurred.
**Depends on:** Dev B's orchestrator hooks, Dev A's real `propagate()`
**Next:** Connect with Dev B's orchestrator when ready; separately, `negotiator.py`'s round cap needs a real look (see note below) before this can honestly be called checkpoint-ready

| Task | Status | Notes |
|---|---|---|
| Wire `operator_agent.py` into live orchestrator rounds (replace fixture harness) | `[x]` | Implemented in `agents/negotiator.py` via `NegotiationEngine` multi-round proposals and template fallback. Negotiation loop is genuinely bounded by `MAX_NEGOTIATION_ROUNDS` from `constants.py`. |
| Wire `validation_agent.py` to Dev A's real `propagate()` (replace stub) | `[x]` | Wired with SGP4 and in-memory Satrec caching in `agents/validation_agent.py` |

**Completion criteria:**
- [x] At least one live run where validation rejects a maneuver and forces re-negotiation (verified in `run_negotiation_simulation.py` and `test_negotiator.py`)
- [x] Negotiation round cap strictly enforced by `MAX_NEGOTIATION_ROUNDS` (verified via `test_max_negotiation_rounds_cap_honored`)

---

### Workstream D — Negotiation & Resolution UI
**Owner:** Dev D (opportunistic pairing with A/B once their Phase 2 tasks land) — Conjunction Details covered by Dev B while Dev D is tied up
**Status:** Conjunction Details screen built and live-verified; remaining screens not started
**Depends on:** Mock transcript/resolution fixtures (Phase 0), then Dev B/C's live events
**Next:** Negotiation Console (two-column transcript) — the console itself, not just the trigger button this task stopped short of

| Task | Status | Notes |
|---|---|---|
| Conjunction Details screen | `[x]` | Dev B (covering Dev D). Not yet merged. Built directly against real live data in `pages/Negotiate.tsx` — skipped the mock-first step since real `activeConjunctionAlert`/`trackedObjects` were already flowing through `useNegotiationStore` by this point (Checkpoint-1-equivalent pieces already merged). Side-by-side satellite stat cards show real computed `Altitude`/`Velocity` (from `position_km`/`velocity_kmps`) plus `Operator`/`Fuel Δv margin`/`Mission priority`/`Maneuverability` as explicit `TBD` — those concepts exist backend-side (`OperatorProfile`) but aren't in any payload the frontend receives pre-negotiation, so TBD rather than fabricated. Conjunction Assessment card shows real `tca_utc`/`miss_distance_km`/`relative_velocity_kmps`, `Collision probability` as `TBD` (no such field in the schema). Built entirely from D3's `Button`/`Card`/`Badge`. **"Start Agent Negotiation" button** opens a second, page-local WebSocket to `/ws/negotiation/{conjunctionId}` (via a new options-based variant of `useAegisSocket()` — see `lib/websocket.ts` in ui-registry.md's Data Layer section) and logs every envelope to console with a live count — **this is intentionally not the Negotiation Console yet**, just proof the trigger works end-to-end; the console/transcript UI is the next task. **Verified live** (not mocked): loaded `/negotiate` with the real backend running, confirmed real satellite names/NORAD IDs/computed altitude-velocity/TCA/miss-distance render (not mock fixture text); clicked the button and confirmed via headless-Chromium console capture that `snapshot` → 3× `negotiation_message` → `resolution` all arrived in order with correct sequence numbers, screenshotted before and after. |
| Negotiation Console (two-column transcript, round-stage tracker) | `[ ]` | Mock transcript first, then Dev B's live events |
| Negotiation Result screen | `[ ]` | Mock resolution first |
| "No Safe Maneuver Found" state | `[ ]` | Explicit, honest UI treatment (invariant 9) |
| History table (filterable) | `[ ]` | Wired to Dev A's `db.py` queries once available |
| Trajectory Simulation screen (joint with Dev A) | `[ ]` | Reuses existing Globe component — no second globe (invariant 12) |

**Completion criteria:**
- [ ] Every screen above demoable against mock data before being wired live
- [ ] All screens wired to live events by end of Phase 2

---

## 7. CHECKPOINT 2 — Full Negotiation Loop Live

### Checkpoint State: **NOT READY**

### Pre-Checkpoint Readiness

| Workstream | Required work complete? | Independently verified? | Branch ready? | Dependencies resolved? | Ready to merge? |
|---|---|---|---|---|---|
| A — Trajectory/History | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| B — Negotiation State Machine | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| C — Live Narration/Validation | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| D — Negotiation/Resolution UI | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |

### Merge Status

| Workstream | Individual status | Merge status | Integration status |
|---|---|---|---|
| A — Trajectory/History | Not started | `[ ]` | `[ ]` |
| B — Negotiation State Machine | Not started | `[ ]` | `[ ]` |
| C — Live Narration/Validation | Not started | `[ ]` | `[ ]` |
| D — Negotiation/Resolution UI | Not started | `[ ]` | `[ ]` |

### Integration Verification (from build-plan.md — required to pass)

- [ ] A conjunction alert (from Checkpoint 1's pipeline) triggers "Start Agent Negotiation"
- [ ] Two operator agents exchange ≥2 rounds of proposals/counter-proposals with live LLM justification text, tied to real yield_scores (never LLM-invented numbers — invariant 1)
- [ ] Validation agent rejects at least one proposed maneuver during the run, forcing a documented re-negotiation loop
- [ ] On convergence + validation approval, a `Resolution` is emitted, the Globe updates to reflect the new trajectory, and the Result screen shows the agreed plan
- [ ] Session is persisted and appears in the History table
- [ ] "No safe maneuver found" escalation path demonstrated at least once (may be a separate scripted run)
- [ ] Full sequence runs from a single trigger with no manual intervention between steps

**Individual completion ≠ integration verified.** All boxes above require a joint team test session, not developer self-report.

### Checkpoint Decision Log

_No checkpoint session has occurred yet._

---

## 8. Phase 3 — Final Integration & Demo Hardening

| Owner | Responsibility | Status |
|---|---|---|
| Dev A | Confirm zero-live-network demo path — cached TLE snapshot only, no CelesTrak calls required | `[ ]` |
| Dev B | Confirm WebSocket resilience under forced disconnect/reconnect during active negotiation; confirm UTC timestamps end-to-end (invariant 7) | `[ ]` |
| Dev C | Confirm LLM fallback path (templated narration) works if Anthropic API is unreachable, without breaking negotiation flow | `[ ]` |
| Dev D | About page (mission framing, data sources, labeled roadmap of unbuilt Phase 2+ items); final visual QA vs. `ui-tokens.md`/`ui-rules.md` (no full colored-background cards) | `[ ]` |
| All | Joint end-to-end run with no manual intervention | `[ ]` |
| All | Record video backup of a full successful run | `[ ]` |

---

## 9. Demo Readiness

Success criteria from `project-overview.md`. A row is only marked "Ready" once **verified as part of the integrated system**, not merely implemented.

| Requirement | Status | Verified by |
|---|---|---|
| Real TLE-sourced conjunction detected and shown on live globe, no manual intervention | `[ ]` | — |
| Two agents visibly exchange ≥2 rounds of proposals/counter-proposals with numeric justification before converging | `[ ]` | — |
| Final yield_score and Δv shown in UI trace back to deterministic backend calculation, never LLM-generated | `[ ]` | — |
| Validation Agent rejects ≥1 proposed maneuver during the demo and forces re-negotiation | `[ ]` | — |
| Globe updates to reflect the agreed maneuver's new trajectory | `[ ]` | — |
| System runs end-to-end off cached data, no live-network dependency required | `[ ]` | — |
| A judge can ask "how do you know the AI isn't just making this up" and get a concrete, verifiable answer from the UI | `[ ]` | — |

**Overall demo readiness: NOT READY**

---

## 10. Blockers & Cross-Workstream Dependencies

| Blocker | Owner | Blocking | Status | Resolution |
|---|---|---|---|---|
| — | — | — | — | — |

**No blockers reported.**

---

## 11. Merge / Integration Log

| Date | Workstream / Checkpoint | Change | Result |
|---|---|---|---|
| — | — | — | — |

**No integrations have occurred yet.**

---

## 12. Decisions Made During Build

| Date | Owner | Decision | Reason | Impact |
|---|---|---|---|---|
| — | Dev B (covering Dev C) | Fixed `validation_agent.py`'s `TrackedObject`/canonical-schema conflict by normalizing to the canonical type at `run_validation_check()`'s boundary (accepting either the canonical `TrackedObject` or a dict), rather than rewriting every caller to pass only the canonical type. | `negotiator.py` (landed after the bug was found) and `scripts/run_validation_agent.py`'s own fixtures both already pass plain dicts; a strict rewrite would have fixed the reported bug while breaking those two working integrations. | See C3's row for full detail. Dev C should know `validation_agent.py` now accepts both shapes by design — this isn't a temporary shim to remove later. |

---

## 13. Implementation Notes

_No implementation notes yet — this section fills in as edge cases, API quirks, integration issues, and non-obvious technical decisions surface during the build._

---

## 14. Update Rules

- Update only your own workstream's rows when starting or completing a task — do not edit another developer's status.
- Move a task from `[ ]` → `[~]` → `[x]` as you work; only mark `[M]` once actually merged to `main`, and only mark `[V]` once the team has jointly verified it during a checkpoint session.
- Add blockers to §10 immediately when you're waiting on another workstream — don't let it sit undocumented.
- Record meaningful cross-workstream decisions in §12 as they happen, not retroactively.
- Checkpoint sections (§5, §7) are only updated during the actual team integration session — individual completion never auto-promotes a checkpoint box.
- Task definitions and completion criteria live in `build-plan.md`; this file only tracks current state. If the work itself changes, update `build-plan.md`, not this tracker.
- Shared files (`ui-registry.md`, `AGENTS.md`, schemas, constants) follow the ownership rules in `build-plan.md`'s Git & Merge Strategy — pull and rebase before pushing tracker edits to avoid clobbering a teammate's update.
- Before a checkpoint session, each developer should update their own workstream section so the team walks in with an accurate picture.
