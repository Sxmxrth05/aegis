# Progress Tracker — Aegis (4-Developer Parallel Execution)

This tracker mirrors `build-plan.md` exactly. It answers "what is the current state of the work the build plan describes" — it does not redefine or duplicate the work itself. Update your own workstream's rows as you go; never mark something merged or verified until it actually is.

---

## 1. Current Team Status

| Field | Value |
|---|---|
| Project | Aegis |
| Team size | 4 developers |
| Current phase | **Phase 0 — Shared Foundation & Contracts** |
| Current checkpoint target | Checkpoint 1 — Live Conjunction Pipeline (not yet reached) |
| Overall status | 🟡 In progress — repo skeleton, schemas, WebSocket envelope, shared constants, and the Resolution fixture are on `main`; still waiting on Dev A's `TrackedObject`/`ConjunctionAlert` fixture and Dev C's `NegotiationMessage` transcript fixture (exists on `dev-c`, not yet merged) before Phase 0 fully closes |
| Last completed milestone | `foundation/contracts` merged to `main` (commit `3818c17`, reviewed/approved by Dev C): Pydantic schemas, WebSocket envelope contract, shared constants, Resolution mock fixture |
| Current team objective | Get Dev A's and Dev C's remaining Phase 0 mock fixtures merged to `main` to close out Phase 0 |
| Next team milestone | Phase 0 exit → developers branch into Workstreams A–D |

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
| Mock fixture: `TrackedObject` / `ConjunctionAlert` JSON | Dev A | `[ ]` | Consumed immediately by Dev D |
| Mock fixture: sample `NegotiationMessage` transcript | Dev C | `[M]` | `backend/fixtures/negotiation_message_transcript.json` — 2 scenarios (clean + reject→re-negotiate), ready for Dev D |
| Mock fixture: sample `Resolution` | Dev B | `[M]` | Merged to `main` via `foundation/contracts` (commit `3818c17`), reviewed/approved by Dev C. `backend/app/data/fixtures/resolution.json` — validated against `schemas/negotiation.py`'s `Resolution` model; a `maneuver`/`approved` example with realistic yield-score/Δv/rationale text for Dev D to build the Negotiation Result screen against. |
| Ownership map | (this document + build-plan.md) | `[x]` | Established by build-plan.md |

### Phase 0 Exit Checklist

- [x] Schemas committed to `main`
- [x] WebSocket envelope contract committed to `main`
- [x] Shared constants committed to `main`
- [ ] All three mock fixtures committed to `main` — only the Resolution fixture (Dev B) is on `main` so far; Dev A's `TrackedObject`/`ConjunctionAlert` fixture and Dev C's `NegotiationMessage` transcript fixture (already on the `dev-c` branch) still need to be merged
- [x] Repo skeleton (backend + frontend) committed to `main`
- [ ] All four developers have pulled `main` and can branch out

**Phase 0 status: NOT COMPLETE — team may not yet diverge into Phase 1 workstreams.**

---

## 4. Phase 1 — Four Parallel Workstreams

### Workstream A — Orbital Physics & Conjunction Detection
**Owner:** Dev A / covered by Dev C
**Current task:** A3 — Pairwise distance + threshold/hysteresis logic, `data/scenario.py` seeded scenario
**Status:** A1 and A2 complete and cleaned up; proceeding to A3
**Blocked by:** Nothing
**Waiting on:** Nothing
**Next:** A3
**Merge status:** A1 and A2 merged to `main` with schema and httpx cleanup

| Task ID | Task | Status | Notes |
|---|---|---|---|
| A1 | `data/celestrak.py` — fetch + local JSON cache + fallback-to-cache | `[x]` | Merged to `main`. Refactored to use `httpx` (async client + sync helper, removing undeclared `requests` dependency) and `RawTLE` dataclass to eliminate schema collision with `schemas/tracked_object.py`. Verified with `test_celestrak_offline.py`. |
| A2 | `agents/monitor_agent.py` — SGP4 propagation via `sgp4` | `[x]` | Merged to `main`. `propagate()` constructs canonical Pydantic `TrackedObject` (`schemas/tracked_object.py`) with `timestamp_utc`, `position_km`, `velocity_kmps`. Verified against Vallado C++ ISS reference in `test_monitor_agent_validation.py`. |
| A3 | Pairwise distance + threshold/hysteresis logic, `data/scenario.py` seeded scenario | `[ ]` | Must guarantee ≥1 sub-threshold close approach |

#### Completion Criteria
- [x] Standalone script runs end-to-end offline (cached data only)
- [ ] `detect_conjunctions()` returns schema-valid `ConjunctionAlert` objects
- [ ] Scripted scenario reliably yields ≥1 alert below threshold

---

### Workstream B — Orchestrator, Schemas & Realtime Backbone
**Owner:** Dev B
**Current task:** —
**Status:** Not started
**Blocked by:** Phase 0 exit (own schemas/contracts)
**Waiting on:** Dev A's `detect_conjunctions()` (can stub with hardcoded alert to unblock early)
**Next:** B1
**Merge status:** Nothing merged

| Task ID | Task | Status | Notes |
|---|---|---|---|
| B1 | `main.py` — FastAPI skeleton, health-check route, WS route stub (echo) | `[M]` | `/health` and `/ws/echo` scaffolded and pushed to `main` |
| B2 | `orchestrator/websocket_manager.py` — connection mgmt, sequence numbers, snapshot-on-reconnect | `[ ]` | Enforces invariant 6 |
| B3 | `orchestrator/orchestrator.py` (Monitor slice) — wraps Dev A's output as `ConjunctionAlert` events, broadcasts | `[M]` | Merged to `main` via `dev-b/monitor-broadcast` (commit `74cd70c`, rebased onto Dev A's PR #1). `Orchestrator.detect_conjunctions()` currently returns a single hardcoded, schema-valid `ConjunctionAlert` fixture (pending Dev A's real `detect_conjunctions()` from A3 — swap point marked with a `TODO(Dev A)` comment at that exact line). Wired to a new `/ws/monitor` route in `main.py`: connect → snapshot (empty `conjunctions` list) → broadcast the alert. Verified manually with a Python `websockets` client: snapshot arrives first at `sequence: 1`, alert follows at `sequence: 2` with the correct envelope shape. |

#### Completion Criteria
- [ ] WS client (e.g. `wscat`) confirms sequence numbers increment
- [ ] Snapshot arrives first on new connection
- [ ] Real (non-mocked) `ConjunctionAlert` from Dev A flows through the socket to a connected client

---

### Workstream C — Agent Intelligence: Cost, Narration & Validation
**Owner:** Dev C
**Current task:** Phase 0 fixture + C1 + C2 + C3 all complete
**Status:** All three modules independently testable and passing
**Blocked by:** Nothing — C2/C3 wiring to live orchestrator blocked until Checkpoint 1 (expected)
**Waiting on:** Dev A's real `propagate()` (stub in place; DI pattern ready for swap)
**Next:** Await Checkpoint 1 merge session; then wire into live orchestrator (Phase 2 C tasks)
**Merge status:** Ready to merge on branch `dev-c`
**Notes:** Next.js scaffold removed from root as out-of-scope for Dev C (frontend owned by Dev D with React+Vite). Explicit ACK given on Dev B's `backend/app/constants.py` as single source of truth for shared constants.

| Task ID | Task | Status | Notes |
|---|---|---|---|
| C1 | `agents/cost_functions.py` — `yield_score` from MVI + fuel/Δv | `[x]` | 27/27 unit tests passing; `compute_yield_score`, `compute_delta_v_cost`, `pick_maneuvering_agent`, all constants |
| C2 | `agents/operator_agent.py` skeleton — Anthropic call, Pydantic-validated, retry-then-template-fallback | `[x]` | Standalone script verified; `build_negotiation_message()` ready for orchestrator |
| C3 | `agents/validation_agent.py` skeleton — 6h re-propagation check | `[x]` | All 3 outcomes tested (approve / reject_secondary_risk / approved_no_action); stub `propagate()` injected via DI |

#### Completion Criteria
- [x] Unit tests for `cost_functions.py` pass (27/27)
- [x] Standalone script calls `operator_agent.py` with fixture input and prints narration
- [x] Standalone validation run succeeds against a fixture tracked-object set (all 3 paths)
- [x] All three modules testable without a live orchestrator or WebSocket connection

---

### Workstream D — Frontend Experience & WebSocket Client
**Owner:** Dev D
**Current task:** —
**Status:** Not started
**Blocked by:** Phase 0 exit (mock fixtures, WS envelope contract)
**Waiting on:** Dev A's mock fixture, Dev B's WS contract (frontend can mock B's server locally until it exists)
**Next:** D1
**Merge status:** Nothing merged

| Task ID | Task | Status | Notes |
|---|---|---|---|
| D1 | Vite + React shell, Tailwind w/ `ui-tokens.md`, top nav w/ placeholder routes | `[M]` | Scaffolded and pushed to `main`; still needs real per-page content and a11y pass. **Correction:** the original "Tailwind wired" claim here was inaccurate — `tailwindcss` was a devDependency but the `@tailwindcss/vite` plugin was never installed or added to `vite.config.ts`'s `plugins` array, so no Tailwind utility classes were ever actually being generated. Every page, including `NavBar.tsx`, has been rendering completely unstyled since D1 landed. Fixed as of `dev-d/shared-primitives` (commit below): installed `@tailwindcss/vite`, added it to `vite.config.ts`. Verified with a screenshot of `/monitor` via headless Chromium — NavBar, page text, and all D3 components now render with correct token colors. |
| D2 | Landing page (static) — hero, stat cards, CTA buttons | `[ ]` | |
| D3 | Shared primitives (buttons/cards/badges) | `[M]` | Dev B (covering Dev D). Merged to `main` via `dev-d/shared-primitives`. Built `Button.tsx` (`variant?: 'primary' \| 'secondary'`), `Card.tsx` (`bg-surface border border-border rounded-lg p-6`, no colored backgrounds), `Badge.tsx` (`status: 'active' \| 'danger' \| 'warning' \| 'success'`, muted-bg + light-text pill per status) in `frontend/src/components/shared/`. Logged in `ui-registry.md` under a new "Shared Primitives" section with exact class recipes. Verified by temporarily wiring all three (plus all four badge statuses) into `/monitor`, screenshotting via headless Chromium, confirming correct dark-theme rendering with zero console errors, then removing the test block. |
| D4 | Globe component (`components/globe/`) — one configurable component | `[x]` | Dev B (covering Dev D). Not yet merged. `Globe.tsx` — single `react-globe.gl` instance driven by props (`trackedObjects`, `mode: 'live' \| 'conjunction' \| 'trajectory'`, optional `conjunctionAlert`), auto-sizes to its parent container via `ResizeObserver`. ECI→lat/lng/alt conversion in `eciToGeo.ts` via `satellite.js`. Colors match D3's `Badge` semantics (accent=active, danger=hazard, pulsing ring on the flagged pair in `'conjunction'` mode). **Currently running on 5 hand-written mock `TrackedObject`s in `globe/mockTrackedObjects.ts`** — pending Dev A's Phase 0 fixture (still outstanding); these aren't fabricated numbers, each one's `position_km`/`velocity_kmps` came from actually SGP4-propagating a real TLE via `satellite.js` at a fixed timestamp, and a `TODO(Dev A)` comment marks the swap point. `'trajectory'` mode is accepted but renders like `'live'` for now, pending Dev A's Phase 2 propagation arrays. Wired into `pages/Monitor.tsx` (`'live'` mode) with a floating legend `Card`. Along the way, fixed two toolchain issues that were blocking this: `three-globe`'s texture path isn't importable via its `exports` map (copied `earth-night.jpg` into `frontend/src/assets/` instead) and `satellite.js`'s WASM build needs `esnext` as the esbuild target (set in `vite.config.ts`'s `build.target` / `optimizeDeps.esbuildOptions.target`). Verified via headless-Chromium screenshot of `/monitor`: globe renders with the dark earth-night texture, satellite points visible, legend counts correct, zero console errors. Logged in `ui-registry.md`. |
| D5 | `lib/websocket.ts` — connect, auto-reconnect, out-of-sequence discard, snapshot-on-reconnect | `[ ]` | Testable against B1's echo stub |
| D6 | `store/useNegotiationStore.ts` skeleton wired to D5 | `[ ]` | |

#### Completion Criteria
- [ ] Globe renders mock satellite list correctly with legend/colors matching `ui-tokens.md`
- [ ] App shell, nav, landing, and mock-fed Globe visually match reference mockup's polish
- [ ] `lib/websocket.ts` successfully round-trips against B1's echo stub

---

## 5. CHECKPOINT 1 — Live Conjunction Pipeline

### Checkpoint State: **NOT READY**

### Pre-Checkpoint Readiness

| Workstream | Required work complete? | Independently verified? | Branch ready? | Dependencies resolved? | Ready to merge? |
|---|---|---|---|---|---|
| A — Orbital Physics | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| B — Orchestrator/Backbone | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| C — Agent Intelligence | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| D — Frontend | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |

### Merge Status

| Workstream | Individual status | Merge status | Integration status |
|---|---|---|---|
| A — Orbital Physics | Not started | `[ ]` | `[ ]` |
| B — Orchestrator/Backbone | Not started | `[ ]` | `[ ]` |
| C — Agent Intelligence | Not started | `[ ]` | `[ ]` |
| D — Frontend | Not started | `[ ]` | `[ ]` |

### Integration Verification (from build-plan.md — required to pass)

- [ ] Cached TLE data → SGP4 propagation → scripted scenario conjunction detection works
- [ ] Orchestrator wraps Dev A's output into a schema-valid `ConjunctionAlert` and broadcasts over the **real** WebSocket (not the echo stub)
- [ ] Frontend swaps mock Globe feed for `lib/websocket.ts` connected to the real server; hazard marker appears live when scripted scenario fires
- [ ] Reconnect test: killing/restoring client connection triggers a full snapshot (not assumed delta continuity — invariant 6)
- [ ] Dev C's `cost_functions.py`, `operator_agent.py`, `validation_agent.py` pass their standalone tests (NOT required to be wired into live orchestrator yet)

**Explicitly NOT required at this checkpoint:** negotiation console, live LLM narration, validation wired into orchestrator, resolution, trajectory, history.

### Checkpoint Decision Log

_No checkpoint session has occurred yet._

---

## 6. Phase 2 — Post-Checkpoint Parallel Work

**Note:** Ownership shifts here per build-plan.md — Dev A moves from orbital physics into Trajectory/History, reusing their orbital-data expertise. This section will not become active until Checkpoint 1 passes.

### Workstream A — Trajectory Data & History Persistence
**Owner:** Dev A
**Status:** Not started (blocked until Checkpoint 1 passes)
**Depends on:** Dev B's `Resolution` schema (locked in Phase 0)
**Next:** Before/after propagation arrays

| Task | Status | Notes |
|---|---|---|
| Before/after propagation arrays for maneuver preview | `[ ]` | Feeds Trajectory screen |
| `storage/db.py` — SQLite persistence of resolved/escalated sessions | `[ ]` | |

**Completion criteria:**
- [ ] Before/after arrays validated against a known maneuver scenario
- [ ] SQLite writes/reads verified via script

---

### Workstream B — Negotiation State Machine
**Owner:** Dev B
**Status:** Not started (blocked until Checkpoint 1 passes)
**Depends on:** Dev C's `cost_functions`/`operator_agent` interfaces (incremental integration allowed)
**Next:** Round-capped state machine

| Task | Status | Notes |
|---|---|---|
| `orchestrator.py` — round-capped `PROPOSAL → COUNTER_PROPOSAL → CONVERGED \| ESCALATED` | `[ ]` | Tie-break + timeout fallback (invariants 4, 5) |
| Wire validation reject outcome back into negotiation with added constraint | `[ ]` | |
| Emit `Resolution` on convergence + validation approval | `[ ]` | |

**Completion criteria:**
- [ ] Full scripted negotiation converges within round cap, or escalates deterministically — provable via script before frontend wiring

---

### Workstream C — Live Narration & Validation
**Owner:** Dev C
**Status:** Not started (blocked until Checkpoint 1 passes)
**Depends on:** Dev B's orchestrator hooks, Dev A's real `propagate()`
**Next:** Wire `operator_agent.py` into live rounds

| Task | Status | Notes |
|---|---|---|
| Wire `operator_agent.py` into live orchestrator rounds (replace fixture harness) | `[ ]` | |
| Wire `validation_agent.py` to Dev A's real `propagate()` (replace stub) | `[ ]` | |

**Completion criteria:**
- [ ] At least one live run where validation rejects a maneuver and forces re-negotiation

---

### Workstream D — Negotiation & Resolution UI
**Owner:** Dev D (opportunistic pairing with A/B once their Phase 2 tasks land)
**Status:** Not started (blocked until Checkpoint 1 passes)
**Depends on:** Mock transcript/resolution fixtures (Phase 0), then Dev B/C's live events
**Next:** Conjunction Details screen (mock-first)

| Task | Status | Notes |
|---|---|---|
| Conjunction Details screen | `[ ]` | Mock-first, then wired to real alert data (already flowing post-Checkpoint 1) |
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
| — | — | — | — | — |

**No implementation decisions have been recorded yet.**

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
