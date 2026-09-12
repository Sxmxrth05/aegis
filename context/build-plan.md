# Build Plan

## Core Principle

Build UI with mock/static data first, verify it looks right, then wire it to the real backend. Never build a backend phase with nothing visible to check it against — every feature should be testable (visually or via a simple script) the moment it's done. This applies especially to the negotiation console and globe, where "does this look and feel right" matters as much as "does this work."

---

## Phase 1 — Foundation

### 01 Project Skeleton
**UI:** Vite + React app shell, Tailwind configured with tokens from `ui-tokens.md`, top nav bar (per `ui-rules.md`) with placeholder page routes for Monitor/Negotiate/History/About.
**Logic:** FastAPI app skeleton (`main.py`), health-check route, WebSocket route stub that echoes a test message.

### 02 Landing Page (static)
**UI:** Hero section, stat cards (hardcoded placeholder numbers), "Watch Demo" / "Explore Live Map" buttons. Matches the reference mockup's landing screen.
**Logic:** None — pure static page.

---

## Phase 2 — Conjunction Monitor (real data, no LLM)

### 03 TLE Ingestion + Caching
**Logic:** `data/celestrak.py` fetch function, local JSON cache, fallback-to-cache-on-failure logic. Test via a simple script that prints the curated demo object set.

### 04 SGP4 Propagation
**Logic:** `agents/monitor_agent.py` propagation function using `sgp4`. Validate against a known satellite's expected position as a sanity check.

### 05 Conjunction Detection + Scripted Scenario
**Logic:** Pairwise distance calculation over the curated object set; threshold + hysteresis logic; `data/scenario.py` seeded scenario generator guaranteeing at least one sub-threshold close approach. Emits `ConjunctionAlert` events.

### 06 Live Globe (mock data)
**UI:** `components/globe/` — the one configurable Globe component, first wired to a hardcoded/mock satellite list to verify the visual (points, colors, legend panel) before connecting to real data. Matches the mockup's "Live Orbital View" screen.

### 07 Wire Monitor to Globe (real data)
**Logic + UI:** Connect the WebSocket so real `ConjunctionAlert` events from step 05 update the Globe from step 06 live — hazard marker appears when the scripted scenario fires.

---

## Phase 3 — Operator Agents & Negotiation

### 08 Deterministic Cost Function
**Logic:** `agents/cost_functions.py` — `yield_score` calculation from MVI + fuel/Δv, unit-testable in isolation with a few hardcoded input scenarios.

### 09 Negotiation State Machine
**Logic:** `orchestrator/orchestrator.py` — round-capped `PROPOSAL → COUNTER_PROPOSAL → CONVERGED | ESCALATED` flow, calling `cost_functions.py` for each agent's turn. Tie-break and timeout fallback rules included.

### 10 LLM Narration Layer
**Logic:** `agents/operator_agent.py` — Anthropic API call per the pattern in `library-docs.md`, producing `justification_text` alongside each deterministic `yield_score`. Schema-validate output; fall back to templated text on failure.

### 11 Negotiation Console (mock transcript)
**UI:** `components/negotiation/` — two-column transcript layout, round-stage tracker, built first against a hardcoded sample transcript to nail the visual (matches the mockup's "Negotiation in Progress" screen).

### 12 Wire Negotiation Console (live)
**Logic + UI:** Connect the console to real `NegotiationMessage` events streamed over WebSocket from steps 09-10.

### 13 Conjunction Details Screen
**UI:** Side-by-side satellite stat cards, TCA/distance/probability panel, "Start Agent Negotiation" button (matches mockup screen 3). Feeds into step 12's flow.

---

## Phase 4 — Validation & Resolution

### 14 Validation Agent
**Logic:** `agents/validation_agent.py` — short-horizon (6h) re-propagation check against the tracked set for a proposed maneuver; approve / reject_secondary_risk / approved_no_action outcomes; reject-loop-back to negotiation with an added constraint.

### 15 Negotiation Result Screen
**UI:** Agreed plan card, human-readable rationale block, mini before/after trajectory preview (matches mockup screen 5). Build against mock resolution data first, then wire to real `Resolution` events.

### 16 "No Safe Maneuver Found" State
**UI + Logic:** Explicit escalation state, presented as an honest outcome rather than hidden — both in the console and the result screen.

---

## Phase 5 — Trajectory Simulation & History

### 17 Trajectory Simulation Screen
**UI:** Globe component in before/after toggle mode + timeline scrubber (matches mockup screen 6). Reuses the Globe component from step 06 with a new prop configuration — do not build a second globe.

### 18 History Log
**Logic:** `storage/db.py` — SQLite persistence of each resolved/escalated conjunction session.
**UI:** `components/history/` — filterable table (matches mockup screen 7).

---

## Phase 6 — Integration & Demo Hardening

### 19 End-to-End Run
**Logic:** Full scripted scenario run from TLE ingestion through resolution, with no manual intervention. Fix any breakage found here before moving on.

### 20 Demo-Day Fallback
**Logic:** Confirm the fully offline/cached path works with zero live network calls. Record a video backup of a full successful run.

### 21 About Page
**UI:** Mission framing, data sources, clearly-labeled roadmap of unbuilt Phase 2+ items (matches mockup screen 9).

---

## Phase 7 — Stretch Features (build one at a time, in this order, only after Phase 6 is solid)

22. Debris Cascade Potential (mass-based yield_score term)
23. Propulsion System Arbitration (thruster type/reaction time)
24. Space Weather Adaptation (live NOAA Kp-index buffer scaling)
25. Extended 48h Lookahead (after 6h version is solid)
26. TTNP (ground-station pass) latency factor
27. Negotiation console visual polish
28. Judge chaos-injection controls
29. Peer-to-Peer Orbit Credits ledger
30. Geopolitical/ITU spectrum hierarchy

---

## Feature Count

| Phase | Features | Total |
|---|---|---|
| 1 — Foundation | 2 | 2 |
| 2 — Conjunction Monitor | 5 | 7 |
| 3 — Operator Agents & Negotiation | 6 | 13 |
| 4 — Validation & Resolution | 3 | 16 |
| 5 — Trajectory Simulation & History | 2 | 18 |
| 6 — Integration & Demo Hardening | 3 | 21 |
| 7 — Stretch (optional) | 9 | 30 |
