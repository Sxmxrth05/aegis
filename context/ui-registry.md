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
← Agent fills this in when built

### Globe Component
*(configurable — live view / conjunction highlight / before-after trajectory modes)*
← Agent fills this in when built

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

## Patterns & Conventions

Pre-populated starting points from `ui-tokens.md` / `ui-rules.md` — refine as you go:

- **Page layout:** max-width ~1440px centered, 24-32px padding, globe-centric screens may go full-bleed
- **Typography:** hero 40-56px/700, section heading 20-24px/600, body 14-15px/400, stat numbers 24-32px/700 (consider font-mono)
- **Responsive:** design desktop-first for the demo (judges will view on a laptop/projector); a basic responsive pass is a nice-to-have, not a priority
- **Status color legend (consistent everywhere):** accent/blue = active, danger/red = debris/hazard, warning/amber = selected/pending, success/green = resolved

*(Add any custom classes or patterns that emerge across multiple components here as you build.)*
