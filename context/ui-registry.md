# UI Registry

A living catalogue of components as they get built, so later screens stay visually consistent with earlier ones. Update this after building each component — but don't let it slow you down; a quick note is enough, this isn't meant to be exhaustive documentation.

---

## How to Use

1. Before building a new component, skim this file for something similar already built.
2. If something similar exists, reuse its general approach (doesn't need to match exactly — use judgment).
3. Once you build something new, add a short entry below so the next component/session can reference it.

---

## Components

### Landing Page
*(hero section, stat cards, CTA buttons)*
Built in `frontend/src/pages/Landing.tsx` — three sections:
- **Hero:** eyebrow label (uppercase tracking-widest `text-muted`), 56px/700 heading with an inline `text-accent` span + `textShadow` glow, 2-line sub-heading in `text-secondary`, two `Button` CTAs (`Link` + `Button` primary/secondary), a decorative `radial-gradient` overlay (pointer-events-none, purely visual, does not tint a card). Background glow uses an inline `style` radial-gradient on the section, not a colored `Card`.
- **Stat cards:** 4-column responsive grid of `Card` components. Each card: `Badge` (status-color semantic), `font-mono text-3xl` stat value, label in `text-primary`, sub-label in `text-muted`. No colored card backgrounds — color comes through the Badge only.
- **How it works:** 4-column grid of `Card` components. Each: `font-mono text-xs text-accent` step number, `text-base font-semibold` heading, `text-sm text-secondary` body copy.
- **Demo CTA banner:** `rounded-xl border border-border` div with a `linear-gradient` inline style (not a colored Card — uses `bg-surface-secondary` as base, gradient is a subtle blue tint overlay). Two CTA buttons centred.
- **Footer:** `border-t border-border` bar, `text-xs text-muted` attribution copy.
- All CTAs: `Link` from `react-router-dom` wrapping `Button` — `/monitor` and `/negotiate`.

### Shared Nav
*(top navigation bar, used across all pages)*
Built in `frontend/src/components/shared/NavBar.tsx` — 64px `bg-surface` bar with `border-b border-border`, logo/wordmark left, `NavLink`s center-right (active: `text-text-primary` + medium weight; inactive: `text-text-secondary` hover `text-text-primary`), live-status dot (`bg-success` with a soft glow) + "Live" label on the right. Currently a static placeholder — not yet wired to real WebSocket connection status.

### Globe Component
*(configurable — live view / conjunction highlight / before-after trajectory modes)*
Built in `frontend/src/components/globe/Globe.tsx` — one `react-globe.gl` instance, driven entirely by props (never rebuilt per screen, per architecture.md invariant 9):
- `trackedObjects: TrackedObject[]` (type in `globe/types.ts`, mirrors `schemas/tracked_object.py` field-for-field), `mode: 'live' | 'conjunction' | 'trajectory'`, optional `conjunctionAlert` (mirrors `schemas/conjunction.py`).
- ECI `position_km` → lat/lng/alt conversion lives in `globe/eciToGeo.ts`, using `satellite.js`'s `eciToGeodetic`/`gstime` directly (no re-propagation needed — it just needs a position + timestamp).
- Auto-sizes to its parent via a `ResizeObserver` (`globe/Globe.tsx`) rather than taking pixel `width`/`height` props — wrap it in a sized container (Monitor uses `h-[calc(100vh-4rem)] w-full` for full-bleed).
- Colors: accent (`#3b82f6`) for normal points, danger (`#ef4444`) for anything matching `conjunctionAlert`'s `primary_id`/`secondary_id` — same semantic mapping as D3's `Badge`. In `'conjunction'` mode the flagged pair also gets a pulsing danger ring.
- `'trajectory'` mode is accepted but currently renders identically to `'live'` — before/after maneuver arcs depend on Dev A's Phase 2 propagation arrays, not yet available. Wiring the prop now means `Trajectory.tsx` can reuse this same instance later with no shape change.
- Globe texture (`earth-night.jpg`) is copied into `frontend/src/assets/` rather than imported from `three-globe`'s package directly — `three-globe`'s `exports` map blocks deep subpath imports in this version, and a local copy is also better for the offline demo path than the alternative unpkg CDN URL.
- Mock data: `globe/mockTrackedObjects.ts` has 5 hand-written `TrackedObject`s, physically real (each one's `position_km`/`velocity_kmps` came from actually running `satellite.js`'s SGP4 propagation against a real TLE at a fixed timestamp, not fabricated numbers). `TODO(Dev A)` comment marks where to swap in the real Phase 0 fixture or live data once available.
- **Vite config note:** `satellite.js` ships a WASM build using top-level await, which esbuild's default target can't pre-bundle. `vite.config.ts` now sets `build.target`/`optimizeDeps.esbuildOptions.target` to `'esnext'` to fix this — needed by any future code importing `satellite.js`, not just Globe.
- Wired into `pages/Monitor.tsx` in `'live'` mode with a floating legend `Card` (object counts + accent/danger color key), verified via headless-Chromium screenshot.
- **Hazard ring/marker recipe:** `ringColor` must be a function of the ring's progress `t` (`(t) => \`rgba(239, 68, 68, ${1 - t})\``), not a flat color string — otherwise every overlapping ring generation renders at full opacity instead of fading. Keep `ringRepeatPeriod` >= one ring's full lifetime (`ringMaxRadius / ringPropagationSpeed * 1000`, currently 3/2*1000=1500ms vs. a 1600ms repeat) so generations never overlap. Points render as `CylinderGeometry` pins — set `pointResolution={32}` (three-globe's default of 12 facets visibly at this scale). Skipping any of these three produces a jagged/scratchy hazard indicator instead of a clean pulsing ring.

### Conjunction Details
*(side-by-side satellite stat cards, TCA/distance/probability panel)*
Built in `frontend/src/pages/Negotiate.tsx`, replacing the placeholder route. All built from D3's `Card`/`Badge`/`Button` primitives, no new component files:
- Reads `activeConjunctionAlert`/`trackedObjects` from `useNegotiationStore` — same store Monitor.tsx reads, not a separate fetch. Honest empty state (`Card` with explanatory text) when there's no active alert yet, rather than fabricating one.
- **Two satellite stat cards** (`SatelliteCard`, a local component in the same file): `name`/`norad_id` direct from `TrackedObject`; `Altitude` and `Velocity` are real, computed client-side from `position_km`/`velocity_kmps` (vector magnitude, altitude = `|position_km| - 6371`) — not fabricated, not from the backend directly. `Operator`, `Fuel Δv margin`, `Mission priority`, `Maneuverability` are shown as `TBD` (muted, `font-mono`) with a one-line caption explaining why — these concepts exist in the backend (`OperatorProfile`'s `mvi`/`fuel_margin_pct`/`delta_v_mps`) but aren't part of any payload the frontend currently receives pre-negotiation, so labeling them TBD is the honest choice per this project's "never fabricate a number" ethos.
- **Conjunction Assessment card**: `tca_utc`, `miss_distance_km`, `relative_velocity_kmps` direct from `ConjunctionAlert`; `Collision probability` shown as `TBD` — no such field exists in the schema.
- Status `Badge` mapped from `ConjunctionStatus`: `alerted`/`escalated` → danger, `negotiating` → warning, `resolved`/`stood_down` → success.
- **"Start Agent Negotiation" button**: on click, opens a second, page-local WebSocket to `/ws/negotiation/{conjunctionId}` (see Data Layer section below for the `useAegisSocket` variant this needed) — every incoming envelope is `console.log`'d and counted; no transcript UI yet (that's the Negotiation Console, a separate task). Button disables and relabels once started.

### Negotiation Console
*(two-column live transcript, round-stage tracker)*
← Agent fills this in when built

### Negotiation Result
*(agreed plan card, rationale block, mini trajectory preview)*
← Agent fills this in when built

### Trajectory Simulation
*(globe in before/after mode, timeline scrubber)*
← Agent fills this in when built

### History Table
*(filterable table of past conjunctions and outcomes)*
← Agent fills this in when built

### About Page
*(static content, tech stack summary, roadmap)*
← Agent fills this in when built

---

## Shared Primitives

### Button
`frontend/src/components/shared/Button.tsx` — thin wrapper over `<button>` (spreads all native `ButtonHTMLAttributes`, so `onClick`/`type`/`disabled` etc. pass through untouched). `variant?: 'primary' | 'secondary'`, default `'primary'`.
- Base: `inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none`
- Primary: `bg-accent text-accent-foreground hover:bg-accent-dark`
- Secondary/ghost: `border border-border bg-transparent text-text-secondary hover:border-border-light hover:text-text-primary`

### Card
`frontend/src/components/shared/Card.tsx` — thin wrapper over `<div>` (spreads native `HTMLAttributes<HTMLDivElement>`).
- Recipe: `bg-surface border border-border rounded-lg p-6`
- No colored backgrounds by design — introduce color via a `Badge`/status dot/small accent bar placed inside, never by tinting the card itself (the one hard visual rule in `ui-rules.md`).

### Badge
`frontend/src/components/shared/Badge.tsx` — thin wrapper over `<span>`. Required `status: 'active' | 'danger' | 'warning' | 'success'`.
- Base: `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium`
- `active` → `bg-accent-muted text-accent-light`
- `danger` → `bg-danger-muted text-danger-light`
- `warning` → `bg-warning-muted text-warning-light`
- `success` → `bg-success-muted text-success-light`

All three accept `className` for one-off overrides and are otherwise deliberately unstyled beyond the above — build screen-specific layout (flex/grid, gaps, spacing) at the call site, not inside the primitive.

**Verified against the dark theme:** screenshotted at `/monitor` (Vite dev server + headless Chromium) — primary/secondary buttons, a card, and all four badge statuses render with correct token colors and no console errors.

---

## Data Layer (store / lib)

Not a visual component, but logged here per the usual pattern since every screen depends on it.

### WebSocket Store
`frontend/src/store/useNegotiationStore.ts` — the single Zustand store for all live state (per code-standards.md: one store, not split per feature). Holds `trackedObjects`, `activeConjunctionAlert`, `connectionStatus: 'connecting' | 'connected' | 'reconnecting' | 'disconnected'`. All WebSocket handling funnels through one `updateFromSocket(envelope)` action that switches on `envelope.type` (`snapshot` replaces `trackedObjects`/`activeConjunctionAlert` wholesale; `conjunction_alert` sets `activeConjunctionAlert`; `negotiation_message`/`resolution` are accepted but no-op until Phase 2 defines what they update; `error` logs). Also exports the `EventType`/`WebSocketEnvelope` types mirroring `schemas/websocket.py`.

### WebSocket Client
`frontend/src/lib/websocket.ts` — `useAegisSocket()` hook, named to match `architecture.md`'s Client Pattern snippet. Connects to Dev B's live `/ws/monitor`, mounted once in `App.tsx` (not per-page) so the connection and its status survive route changes — components read live state via the store, not by calling this hook themselves. Enforces: snapshot must be the first message per connection (anything else first is logged and dropped, not applied); messages with `sequence <= last seen` are discarded; on close, auto-reconnects forever at a fixed 2s interval with no retry cap, setting `connectionStatus` straight to `'reconnecting'` and holding it there for the whole outage — never `'disconnected'`, which is reserved for a possible future explicit/user-initiated disconnect and isn't reachable from the retry loop (demo-safety requirement: a backend blip during a live demo must never look like the connection gave up); every fresh connection resets local sequence-tracking state so a stale message from a dead socket can never be compared against the new one's sequence (architecture.md invariant 6 — never assume delta continuity, trust whatever snapshot arrives next).

**Consumers:** `NavBar.tsx`'s live-status pill now reads real `connectionStatus` (4-state color/label map: connecting=warning, connected=success "Live", reconnecting=warning+pulse, disconnected=danger) instead of being static. `Monitor.tsx` reads live `trackedObjects`/`activeConjunctionAlert`; falls back to D4's `mockTrackedObjects.ts` whenever the live array is empty (true today, since the backend snapshot doesn't carry tracked-object state yet) so the globe stays populated either way.

**Verified end-to-end:** with the real backend running, the globe correctly received B3's live `conjunction_alert` and switched to `'conjunction'` mode with a hazard ring on the matching mock satellites. Killing the backend mid-session showed `Reconnecting` (not a freeze); restarting it produced a fresh `Live` state with the alert re-applied from the new snapshot — confirmed via headless-Chromium screenshots at each stage.

**`useAegisSocket()` options (added for the Conjunction Details screen):** now takes an options object — `{ url?, enabled?, onEnvelope?, updateStore? }` — all optional, so the existing no-arg call in `App.tsx` is unaffected. `enabled` (default `true`) lets a connection be created on a user action instead of on mount — pass `false` until then, since hooks must still be called unconditionally on every render. `updateStore` (default `true`) controls whether this connection writes into the shared store at all; the one persistent `/ws/monitor` connection in `App.tsx` keeps `updateStore: true` (it owns `connectionStatus` for NavBar's pill), while a secondary connection — e.g. `Negotiate.tsx`'s per-negotiation socket to `/ws/negotiation/{id}` — passes `updateStore: false` so it can't cross-talk with the global store or make NavBar's status flicker based on an unrelated connection. `onEnvelope` receives every in-order, post-snapshot envelope regardless of `updateStore`; it's held in a `ref` internally so passing a fresh inline arrow function each render doesn't tear down and reconnect the socket. Also added `buildNegotiationWsUrl(conjunctionId)`, which derives the negotiation URL from wherever `VITE_WS_URL`/the hardcoded default points the monitor socket, so both routes share one source of truth for host/port.

---

## Patterns & Conventions

Pre-populated starting points from `ui-tokens.md` / `ui-rules.md` — refine as you go:

- **Page layout:** max-width ~1440px centered, 24-32px padding, globe-centric screens may go full-bleed
- **Typography:** hero 40-56px/700, section heading 20-24px/600, body 14-15px/400, stat numbers 24-32px/700 (consider font-mono)
- **Responsive:** design desktop-first for the demo (judges will view on a laptop/projector); a basic responsive pass is a nice-to-have, not a priority
- **Status color legend (consistent everywhere):** accent/blue = active, danger/red = debris/hazard, warning/amber = selected/pending, success/green = resolved

*(Add any custom classes or patterns that emerge across multiple components here as you build.)*
