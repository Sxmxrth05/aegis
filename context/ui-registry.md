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
← Agent fills this in when built

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

### Conjunction Details
*(side-by-side satellite stat cards, TCA/distance/probability panel)*
← Agent fills this in when built

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

## Patterns & Conventions

Pre-populated starting points from `ui-tokens.md` / `ui-rules.md` — refine as you go:

- **Page layout:** max-width ~1440px centered, 24-32px padding, globe-centric screens may go full-bleed
- **Typography:** hero 40-56px/700, section heading 20-24px/600, body 14-15px/400, stat numbers 24-32px/700 (consider font-mono)
- **Responsive:** design desktop-first for the demo (judges will view on a laptop/projector); a basic responsive pass is a nice-to-have, not a priority
- **Status color legend (consistent everywhere):** accent/blue = active, danger/red = debris/hazard, warning/amber = selected/pending, success/green = resolved

*(Add any custom classes or patterns that emerge across multiple components here as you build.)*
