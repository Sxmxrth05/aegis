# Build Plan — Aegis (4-Developer Parallel Execution)

## Execution Strategy Overview

This plan replaces the single-developer sequential build plan with a **dependency-aware, four-developer parallel plan**. Work is divided by **system ownership boundary** (not by frontend/backend split, and not by equal task count), chosen to minimize blocking and merge conflicts:

| Owner | Workstream | Core boundary |
|---|---|---|
| **Dev A** | Orbital Physics & Conjunction Detection | Pure, deterministic, no I/O to UI or LLM — TLE data in, `ConjunctionAlert`-shaped data out |
| **Dev B** | Orchestrator, Schemas & Realtime Backbone | The system's spine — owns contracts, session state, sequencing, broadcast |
| **Dev C** | Agent Intelligence — Cost, Narration & Validation | Everything touching yield_score math, the LLM, and the safety re-check |
| **Dev D** | Frontend Experience & WebSocket Client | All UI surfaces, built mock-first against agreed contracts |

This mirrors the architecture's own boundaries (`architecture.md` §System Boundaries): agents never touch the WebSocket, the orchestrator owns state/sequencing, the frontend never calls external APIs directly. Splitting developers along these exact seams means each person's files rarely overlap with anyone else's, and each can build/test independently using mocks where the real dependency isn't ready yet.

**Two integration checkpoints** structure the timeline: Checkpoint 1 proves the live data → detection → realtime → globe pipeline; Checkpoint 2 proves the full negotiation → validation → resolution → trajectory → history loop. A final hardening phase follows before demo day. Phase 7 (stretch) remains untouched by this restructuring — optional, one-at-a-time, only after Phase 6 is solid, exactly as in the original plan.

---

## Phase 0 — Shared Foundation & Contracts

**Goal:** everything four people need to agree on before writing divergent code. Target: a short joint session (not a solo task) — ideally under an hour — before branching out. Owned collaboratively, but each artifact has a single writer to avoid conflicting edits.

| Artifact | Written by | Consumed by | Contents |
|---|---|---|---|
| Repo skeleton | Dev B (backend half), Dev D (frontend half) | Everyone | `/backend/app/{agents,data,schemas,orchestrator,storage}`, `/frontend/src/{components,pages,store,lib}` per `architecture.md` |
| Pydantic schemas | Dev B | A, C, D | `TrackedObject`, `ConjunctionAlert`, `NegotiationMessage`, `Resolution` — field names/types locked here, matching `architecture.md` DB schema |
| WebSocket envelope contract | Dev B | A (indirect), C (indirect), D | `{type, sequence, payload}`; event types: `snapshot`, `conjunction_alert`, `negotiation_message`, `resolution`, `error`; reconnect-always-requests-snapshot rule (invariant 6) |
| Shared constants | Dev B (file owner) | A, C | `CONJUNCTION_THRESHOLD_KM`, `HYSTERESIS_CLEAR_KM`, `MAX_NEGOTIATION_ROUNDS`, `VALIDATION_LOOKAHEAD_HOURS` in `cost_functions.py`-adjacent constants module |
| Mock fixtures | A drafts TrackedObject/ConjunctionAlert JSON; C drafts a sample NegotiationMessage transcript; B drafts a sample Resolution | D (immediately, for mock-first UI) | Static JSON matching the locked schemas above |
| Ownership map | This document | Everyone | See workstream tables below |

**Exit condition for Phase 0:** schemas + WS envelope committed to `main`, mock fixtures committed, every developer has pulled `main` and can start their branch. No implementation logic is written in Phase 0 — only contracts and fixtures.

---

## Phase 1 — Parallel Workstreams (pre-Checkpoint 1)

Maps to original Phase 1–2 features (01–07). Everyone can start immediately after Phase 0 lands.

### Workstream A — Orbital Physics & Conjunction Detection
**Owner:** Dev A

**Goal:** deterministic pipeline from raw TLE data to a `ConjunctionAlert`, provable with zero UI or backend server involved.

**Tasks** *(old features 03, 04, 05)*
- A1: `data/celestrak.py` — fetch + local JSON cache + fallback-to-cache-on-failure
- A2: `agents/monitor_agent.py` — SGP4 propagation via `sgp4`, validated against a known satellite's expected position
- A3: Pairwise distance calc, threshold + hysteresis logic, `data/scenario.py` seeded scenario guaranteeing ≥1 sub-threshold close approach; emits `ConjunctionAlert`-shaped objects

**Primary ownership:** `backend/app/data/`, `backend/app/agents/monitor_agent.py`

**Dependencies:** locked `ConjunctionAlert`/`TrackedObject` schema (Phase 0)

**Interfaces provided:** `fetch_tle_group()`, `propagate()`, `detect_conjunctions()` — plain Python functions returning schema-shaped dicts; no network/WS/LLM calls inside these. `propagate()` is also the interface Dev C's validation agent will reuse.

**Interfaces consumed:** none beyond the schema

**Mock strategy:** none needed for A's own work; A instead *produces* the mock fixture Dev D uses in Phase 0/1

**Verification:** standalone script prints the curated demo object set and confirms the scripted scenario always yields ≥1 alert below threshold

**Completion criteria:** script runs end-to-end offline (cached data only), `detect_conjunctions()` returns schema-valid `ConjunctionAlert` objects

---

### Workstream B — Orchestrator, Schemas & Realtime Backbone
**Owner:** Dev B

**Goal:** the live spine — FastAPI app, WebSocket transport, and the wiring that turns Dev A's detection output into a broadcast event.

**Tasks** *(old features 01-backend, 07-logic, plus Phase 0 schema ownership)*
- B1: `main.py` — FastAPI skeleton, health-check route, WS route stub (echo)
- B2: `orchestrator/websocket_manager.py` — connection management, monotonic sequence numbers, reconnect → full-snapshot-first behavior (invariant 6)
- B3: `orchestrator/orchestrator.py` (Monitor slice only) — calls Dev A's `detect_conjunctions()`, wraps results as `ConjunctionAlert` events, broadcasts

**Primary ownership:** `backend/app/main.py`, `backend/app/orchestrator/`, `backend/app/schemas/`

**Dependencies:** Dev A's `detect_conjunctions()` (can stub with a single hardcoded alert to unblock B2/B3 early)

**Interfaces provided:** live `ws://.../ws/monitor` broadcasting schema-valid events; snapshot-on-connect

**Interfaces consumed:** Dev A's detection function (swapped in from mock to real near end of phase)

**Mock strategy:** hardcode one `ConjunctionAlert` payload to build/test B2/B3 before A3 is finished

**Verification:** connect a WS client (or `wscat`) and confirm sequence numbers increment and a snapshot arrives first on connect

**Completion criteria:** real (non-mocked) `ConjunctionAlert` from Dev A flows through the socket to any connected client

---

### Workstream C — Agent Intelligence: Cost, Narration & Validation
**Owner:** Dev C

**Goal:** build and unit-test the deterministic cost math, the LLM narration call, and the validation re-check — all independently of the orchestrator being finished.

**Tasks** *(old features 08, plus early start on 10 and 14)*
- C1: `agents/cost_functions.py` — `yield_score` from MVI + fuel/Δv, unit-tested against hardcoded scenarios
- C2 *(early start)*: `agents/operator_agent.py` skeleton — Anthropic call per `library-docs.md` pattern, Pydantic-validated output, retry-once-then-template-fallback; tested against C1's fixture yield_scores, no orchestrator dependency required yet
- C3 *(early start)*: `agents/validation_agent.py` skeleton — 6h re-propagation check logic against a fixture tracked-object set, using a stubbed `propagate()` until Dev A's is ready

**Primary ownership:** `backend/app/agents/cost_functions.py`, `operator_agent.py`, `validation_agent.py`

**Dependencies:** none blocking for C1; C2/C3 can run entirely on fixtures/stubs until Checkpoint 1

**Interfaces provided:** `compute_yield_score()`, `get_agent_justification()`, `run_validation_check()` — all pure/testable functions

**Interfaces consumed:** Dev A's real `propagate()` (swapped in for the stub post-Checkpoint 1)

**Mock strategy:** stub `propagate()` returning fixed positions; use C1's own yield_scores as LLM prompt input

**Verification:** unit tests for `cost_functions.py`; a standalone script calling `operator_agent.py` with fixture input and printing narration; a standalone validation run against a fixture tracked-object set

**Completion criteria:** all three modules independently testable and passing without any live orchestrator or WebSocket connection

---

### Workstream D — Frontend Experience & WebSocket Client
**Owner:** Dev D

**Goal:** ship the app shell and the Monitor screen fully mock-driven, then swap the mock feed for the live socket at Checkpoint 1.

**Tasks** *(old features 01-frontend, 02, 06)*
- D1: Vite + React shell, Tailwind configured with `ui-tokens.md` tokens, top nav with placeholder routes per `ui-rules.md`
- D2: Landing page (static) — hero, stat cards, CTA buttons
- D3: Shared primitives (buttons/cards/badges) per `ui-tokens.md`/`ui-rules.md`; logged in `ui-registry.md` as built
- D4: Globe component (`components/globe/`) — one configurable component, first driven by Dev A's mock `TrackedObject` fixture to validate points/colors/legend
- D5: `lib/websocket.ts` — connect, auto-reconnect, out-of-sequence discard, snapshot-on-reconnect request, built against Dev B's WS envelope contract (testable against B1's early echo stub)
- D6: `store/useNegotiationStore.ts` skeleton wired to D5's client

**Primary ownership:** `frontend/src/` in full

**Dependencies:** Phase 0 mock fixtures (A's), WS envelope contract (B's)

**Interfaces provided:** Globe component reusable by later Trajectory screen (invariant 12: one Globe, not three)

**Interfaces consumed:** Dev B's WS contract (mocked locally until real server is ready), Dev A's fixture data

**Mock strategy:** entire Monitor screen built and demo-able on static/mock data before any backend server exists

**Verification:** Globe renders the mock satellite list correctly with legend/colors matching `ui-tokens.md`

**Completion criteria:** app shell, nav, landing, and mock-fed Globe all visually match the reference mockup's polish; `lib/websocket.ts` successfully round-trips against B1's echo stub

---

## CHECKPOINT 1 — Live Conjunction Pipeline

**This is a real synchronization point, not "merge everything."** All four branches merge to `main` and the team verifies, together, in one session:

**Must be working:**
1. Cached TLE data (Dev A) → SGP4 propagation → scripted scenario conjunction detection
2. Dev B's orchestrator wraps A's output into a schema-valid `ConjunctionAlert` and broadcasts it over the real WebSocket (not the echo stub)
3. Dev D's frontend swaps its mock Globe feed for `lib/websocket.ts` connected to the real server; a hazard marker appears live when the scripted scenario fires
4. Reconnect test: killing and restoring the client connection triggers a full snapshot, not an assumed delta continuity (invariant 6)
5. Dev C's `cost_functions.py`, `operator_agent.py`, and `validation_agent.py` pass their standalone tests (they are **not** required to be wired into the live orchestrator yet)

**Explicitly NOT required yet:** negotiation console, LLM narration in the live flow, validation wired into orchestrator, resolution, trajectory, history. These remain mocked or unbuilt — that's expected.

**If one workstream is behind:** the checkpoint still proceeds for the other three; the lagging piece is finished against `main` with the others available to pair rather than blocking the whole team. Historically the highest-risk slip point is A3/B3 (scenario tuning), so budget slack there first.

**How the team decides the checkpoint has passed:** run the scripted scenario end-to-end on a shared machine, confirm the hazard marker appears live and reconnect shows a snapshot, then tag the commit (e.g. `checkpoint-1`) on `main`.

---

## Phase 2 — Parallel Workstreams (post-Checkpoint 1)

Maps to original Phase 3–5 features (09–18). Ownership shifts slightly: Dev A's physics work is essentially done, so Dev A moves into the Trajectory/History area, which reuses their orbital-data expertise. This keeps load balanced without arbitrarily splitting frontend work.

### Workstream A — Trajectory Data & History Persistence
**Owner:** Dev A · *(old features 17-logic, 18-logic)*
- Before/after propagation arrays for the maneuver preview (feeds Trajectory screen)
- `storage/db.py` — SQLite persistence of resolved/escalated sessions

**Depends on:** Dev B's `Resolution` schema (locked in Phase 0)

**Provides:** trajectory data interface for Dev D's Trajectory screen; `db.py` query functions for Dev D's History table

**Mock strategy:** none needed — A works from real propagation output

**Completion criteria:** before/after arrays validated against a known maneuver scenario; SQLite writes/reads verified via script

### Workstream B — Negotiation State Machine
**Owner:** Dev B · *(old feature 09, validation loop-back wiring)*
- `orchestrator.py` — round-capped `PROPOSAL → COUNTER_PROPOSAL → CONVERGED | ESCALATED`, tie-break and timeout fallback (invariants 4, 5)
- Wires Dev C's validation agent's reject outcome back into negotiation with an added constraint
- Emits `Resolution` on convergence + validation approval

**Depends on:** Dev C's `cost_functions`/`operator_agent` interfaces (can integrate incrementally — orchestrator can call C's real functions as soon as C exposes them, no need to wait for C's full LLM polish)

**Provides:** live `NegotiationMessage`/`Resolution` broadcast events

**Completion criteria:** a full scripted negotiation converges within the round cap, or escalates deterministically — provable via script before frontend wiring

### Workstream C — Live Narration & Validation
**Owner:** Dev C · *(old features 10, 14, full wiring)*
- Wire `operator_agent.py` into live orchestrator rounds (replacing C2's fixture-driven test harness)
- Wire `validation_agent.py` to Dev A's real `propagate()` (replacing the stub) for the live 6h re-check

**Depends on:** Dev B's orchestrator hooks, Dev A's real `propagate()`

**Provides:** live justification text per round; approve / reject_secondary_risk / approved_no_action outcomes back to B's orchestrator

**Completion criteria:** at least one live run where validation rejects a maneuver and forces re-negotiation (per project success criteria)

### Workstream D — Negotiation & Resolution UI
**Owner:** Dev D · *(old features 11, 13, 15, 16, 18-UI; Trajectory UI shared with Dev A)*
- Conjunction Details screen (mock-first, then wired to real alert data — already flowing since Checkpoint 1)
- Negotiation Console — two-column transcript, round-stage tracker, built against a mock transcript first, then Dev B's live events
- Negotiation Result screen — agreed plan card, rationale, mini trajectory preview (mock resolution first)
- "No Safe Maneuver Found" state — explicit, honest UI treatment (invariant 9)
- History table (filterable), wired to Dev A's `db.py` queries once available
- **Trajectory Simulation screen** built jointly with Dev A: Dev D builds the before/after toggle + scrubber UI reusing the existing Globe component (invariant 12 — no second globe); Dev A supplies the data feed

**Note on load-balancing:** this phase is frontend-heavy by nature of the product (5+ screens). Once Dev A's and Dev B's Phase-2 tasks land, either can pick up a UI screen (e.g. Dev A pairs on Trajectory, Dev B pairs on Negotiation Result) rather than Dev D carrying all six alone — assign opportunistically once each dev's own workstream is complete.

**Mock strategy throughout:** every screen above ships against static mock data first (per `build-plan.md`'s core mock-first principle), then is wired to the corresponding live event once B/C land it — this is what lets Dev D keep moving without blocking on B/C's exact completion order.

---

## CHECKPOINT 2 — Full Negotiation Loop Live

All four branches merge again; verify together:

1. A conjunction alert (from Checkpoint 1's pipeline) triggers "Start Agent Negotiation"
2. Two operator agents exchange ≥2 rounds of proposals/counter-proposals with live LLM justification text, tied to real yield_scores (never LLM-invented numbers — invariant 1)
3. Validation agent rejects at least one proposed maneuver during the run, forcing a documented re-negotiation loop
4. On convergence + validation approval, a `Resolution` is emitted, the Globe updates to reflect the new trajectory, and the Result screen shows the agreed plan
5. The session is persisted and appears in the History table
6. The "no safe maneuver found" escalation path is demonstrated at least once (can be a separate scripted run)

**Exit condition:** this sequence runs from a single trigger with no manual intervention between steps, matching `project-overview.md`'s stated success criteria.

---

## Phase 3 — Final Integration & Demo Hardening

Maps to original features 19–21. All four developers converge on hardening their own area, plus shared end-to-end passes:

- **Dev A:** confirm zero-live-network demo path — cached TLE snapshot only, no CelesTrak calls required
- **Dev B:** confirm WebSocket resilience under forced disconnect/reconnect during an active negotiation; confirm all timestamps are UTC end-to-end (invariant 7)
- **Dev C:** confirm LLM fallback path (templated narration) works if the Anthropic API is unreachable, without breaking the negotiation flow
- **Dev D:** About page (mission framing, data sources, clearly-labeled roadmap of unbuilt Phase 2+ items); final visual QA pass against `ui-tokens.md`/`ui-rules.md` (no full colored-background cards — the one hard rule)
- **All:** joint end-to-end run (old feature 19) with no manual intervention; record the video backup of a full successful run (old feature 20)

**Definition of done for demo readiness:**
- Full flow (TLE → detection → negotiation → validation → resolution → trajectory → history) runs end-to-end off cached data
- A judge can trace any yield_score/Δv shown in the UI back to deterministic backend code
- At least one full run shows a validation rejection and re-negotiation
- Offline/cached path confirmed with zero live-network dependency
- Video backup recorded

---

## Git & Merge Strategy

Kept intentionally lightweight — four people, one hackathon, not an enterprise process.

- **`main`** is always demo-able. Nothing broken gets merged.
- Each developer works on short-lived branches prefixed by owner: `dev-a/...`, `dev-b/...`, `dev-c/...`, `dev-d/...` (e.g. `dev-a/tle-ingestion`, `dev-d/negotiation-console`).
- **Phase 0** contracts land through one short-lived `foundation/contracts` branch, reviewed by all four together, merged first. Everyone branches from `main` only after this merge.
- Merge to `main` per completed task, not per phase — small PRs, self-tested against the workstream's own "Verification" step before opening.
- **Checkpoints are explicit merge+test sessions**, not just merges: all four branches land on `main`, then the team runs the checkpoint's verification steps together on a shared machine before calling it passed.
- **File-level ownership avoids conflicts naturally**, since ownership boundaries equal directory boundaries:
  - `backend/app/data/`, `backend/app/agents/monitor_agent.py` → Dev A only
  - `backend/app/main.py`, `backend/app/orchestrator/`, `backend/app/schemas/` → Dev B only
  - `backend/app/agents/cost_functions.py`, `operator_agent.py`, `validation_agent.py` → Dev C only
  - `frontend/src/` → Dev D only
- **Controlled shared files** (single-owner edits, others request changes via a quick message rather than direct edit):
  - Schemas and shared constants → Dev B is the only merger
  - `ui-registry.md`, `ui-tokens.md` → append-only, updated by whoever builds the component, low conflict risk by nature
  - `AGENTS.md`, `progress-tracker.md` → each developer updates only the rows/sections for their own workstream when they complete a task; pull-and-rebase before pushing to avoid clobbering someone else's edit
  - `requirements.txt` / `package.json` → announce in the team channel before adding a new dependency (per `code-standards.md`'s lean-dependency rule), then whoever's blocked on it merges it
- Before merging into `main`, each developer pulls latest `main` and rebases their branch — this is the only conflict-prevention step required given how cleanly the directories are separated.

---

## Feature Number Mapping (old → new)

| Old # | Old feature | New owner | New phase |
|---|---|---|---|
| 01 (backend) | Project skeleton (FastAPI) | Dev B | Phase 1 (B1) |
| 01 (frontend) | Project skeleton (Vite/React) | Dev D | Phase 1 (D1) |
| 02 | Landing page | Dev D | Phase 1 (D2) |
| 03 | TLE ingestion + caching | Dev A | Phase 1 (A1) |
| 04 | SGP4 propagation | Dev A | Phase 1 (A2) |
| 05 | Conjunction detection + scripted scenario | Dev A | Phase 1 (A3) |
| 06 | Live Globe (mock data) | Dev D | Phase 1 (D4) |
| 07 | Wire Monitor to Globe (real data) | Dev B + Dev D | Checkpoint 1 |
| 08 | Deterministic cost function | Dev C | Phase 1 (C1) |
| 09 | Negotiation state machine | Dev B | Phase 2 |
| 10 | LLM narration layer | Dev C | Phase 1 start (C2) → Phase 2 wiring |
| 11 | Negotiation console (mock) | Dev D | Phase 2 |
| 12 | Wire negotiation console (live) | Dev D + Dev B | Checkpoint 2 |
| 13 | Conjunction details screen | Dev D | Phase 2 |
| 14 | Validation agent | Dev C | Phase 1 start (C3) → Phase 2 wiring |
| 15 | Negotiation result screen | Dev D | Phase 2 |
| 16 | "No safe maneuver found" state | Dev D | Phase 2 |
| 17 | Trajectory simulation screen | Dev A (data) + Dev D (UI) | Phase 2 |
| 18 | History log | Dev A (logic) + Dev D (UI) | Phase 2 |
| 19 | End-to-end run | All | Phase 3 |
| 20 | Demo-day fallback | All | Phase 3 |
| 21 | About page | Dev D | Phase 3 |
| 22–30 | Stretch (Phase 7) | Unassigned — opportunistic, one at a time, only after Phase 3 is solid | Post-demo-ready |

No original MVP functionality is dropped or descoped; Phase 7 remains exactly as optional as before.

---

## Preserved Invariants (unchanged, verified against this plan)

All 7 invariants from `architecture.md` hold under this restructuring:
1. Safety numbers only from deterministic Python (Dev A/C's functions; LLM only narrates) — unchanged
2. `agents/` never touches WebSocket directly — Dev A/C's modules only return data; Dev B's orchestrator is the sole broadcaster
3. Orchestrator owns session state/sequencing — entirely Dev B's workstream, not split
4. Frontend never calls external APIs directly — Dev D's `store/`+`lib/websocket.ts` remain the only path to backend data
5. Round-capped negotiation — Dev B's workstream, unchanged
6. Validation Agent as separate safety layer, "no action" a valid outcome — Dev C's workstream, unchanged, explicitly tested at Checkpoint 2
7. UTC timestamps end-to-end — called out explicitly in Phase 3 hardening
8. Cached/offline path is first-class — Dev A owns this from Phase 1 onward, re-verified in Phase 3
9. One configurable Globe component — explicitly enforced in Workstream D (Phase 1) and reused, not rebuilt, in the Phase 2 Trajectory screen
10. No full colored-background cards — called out in Phase 3 visual QA

Parallelizing did not require changing any existing architectural assumption.
