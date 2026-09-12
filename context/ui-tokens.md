# UI Tokens

This file defines the starting design tokens for Aegis's dark, space-mission-control aesthetic (see the reference mockup: dark navy backgrounds, glowing blue/red/amber status colors, a clean 3D globe as the centerpiece). These are a strong, ready-to-use foundation, **not a rigid spec** — treat them as sensible defaults you can refine, extend, or adjust as components come together. If a value feels off once it's on screen, change it; the goal is a polished, premium-feeling product that matches the reference mockup's spirit, not exact pixel matching.

---

## How to Use

Define tokens as CSS variables in `globals.css`, then reference them via Tailwind's `@theme` directive (Tailwind v4) or a `tailwind.config` theme extension (v3) so they're usable as utility classes (e.g. `bg-surface`, `text-primary`, `border-border`). Prefer tokens over raw hex values in components for consistency, but don't stress over 100% compliance if a one-off value genuinely looks better somewhere — this is a hackathon demo, ship what looks good.

```css
/* Preferred */
<div className="bg-surface border border-border text-text-primary">

/* Fine if it looks better */
<div style={{ background: 'radial-gradient(...)' }}>
```

---

## globals.css — Starting Token Set

```css
:root {
  /* Font */
  --font-sans: 'Inter', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace; /* for stat numbers, IDs, timestamps */

  /* Backgrounds */
  --color-background: #0a0e17;
  --color-surface: #10151f;
  --color-surface-secondary: #161c2a;
  --color-surface-tertiary: #1c2333;
  --color-surface-muted: #0d1219;

  /* Borders */
  --color-border: #232a3b;
  --color-border-light: #2e3750;
  --color-border-muted: #171d2b;

  /* Text */
  --color-text-primary: #f2f4f8;
  --color-text-secondary: #9ca3b8;
  --color-text-muted: #5c6478;

  /* Primary accent — active satellites, primary CTAs */
  --color-accent: #3b82f6;
  --color-accent-dark: #2563eb;
  --color-accent-light: #60a5fa;
  --color-accent-muted: #1e3a5f;
  --color-accent-foreground: #ffffff;

  /* Semantic — status colors matching the mockup's legend */
  --color-danger: #ef4444;        /* debris, hazard, rejected */
  --color-danger-light: #fca5a5;
  --color-danger-muted: #3a1a1a;

  --color-warning: #f59e0b;       /* selected, pending, caution */
  --color-warning-light: #fcd34d;
  --color-warning-muted: #3a2e0f;

  --color-success: #22c55e;       /* resolved, safe, approved */
  --color-success-light: #86efac;
  --color-success-muted: #143120;

  --color-info: #3b82f6;          /* mirrors accent for informational states */

  /* Overlays */
  --color-overlay: rgba(10, 14, 23, 0.85);

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;
}
```

---

## Color Usage Guide (loose guidance, not law)

| Context | Suggested tokens |
|---|---|
| Page background | `background` → `surface` for panels/cards |
| Panel/card borders | `border` (default), `border-light` on hover |
| Primary text | `text-primary` |
| Secondary/labels | `text-secondary` |
| Muted/timestamps | `text-muted` |
| Active satellites, primary buttons, selected states | `accent` family |
| Debris, hazard markers, rejected/escalated status | `danger` family |
| Selected object, pending/caution states | `warning` family |
| Resolved, safe, approved status | `success` family |

Feel free to introduce additional shades or a glow/shadow treatment on markers and status dots to get that "mission control" feel from the mockup — subtle box-shadow glows on colored dots/badges read well against the dark background.

---

## Typography

| Element | Size | Weight | Color |
|---|---|---|---|
| Page hero heading | 40–56px | 700 | `text-primary` |
| Section heading | 20–24px | 600 | `text-primary` |
| Body | 14–15px | 400 | `text-secondary` |
| Labels/eyebrow | 11–12px, uppercase, letter-spacing | 600 | `text-muted` |
| Stat numbers | 24–32px | 700 | `text-primary`, consider `font-mono` |
| Timestamps/IDs | 12–13px | 400 | `text-muted`, `font-mono` |

Use Inter (or a similar clean geometric sans) for UI text; a monospace face for stat numbers, satellite IDs, and timestamps adds to the technical/mission-control feel — this is a suggestion, not a requirement.

---

## Spacing (common values, adjust as needed)

| Token | Value |
|---|---|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 48px |

---

## Component Starting Points

- **Cards** — `bg-surface`, `border border-border`, `rounded-lg` (16px), generous internal padding (~20-24px). Color introduced via small badges/status dots inside, not full-card colored backgrounds.
- **Buttons (primary)** — `bg-accent`, white text, `rounded-md`, medium padding. Hover: `bg-accent-dark` or a subtle brightness/glow shift.
- **Buttons (secondary/ghost)** — `border border-border`, transparent background, `text-secondary`, hover to `border-light` + `text-primary`.
- **Badges** — small `rounded-full` pills, colored via the semantic `-muted` background + matching `-light` text for a soft glow look (e.g. `bg-success-muted text-success-light` for "Resolved").
- **Status dots/markers on the globe** — solid semantic color, small glow/shadow for visibility against the dark globe.
- **Tables** — `border-muted` row dividers, subtle `surface-secondary` row hover, no heavy alternating stripes needed.

These are a starting recipe, not a locked spec — use your judgment to make each component feel polished once you see it rendered.

---

## Loose Guidance (not hard invariants)

- Prefer tokens over raw hex values where convenient, but don't block progress chasing 100% token purity.
- Avoid full-bleed colored card backgrounds (keep the dark, calm base; let status color show through badges/dots/accents instead) — this is the one visual rule worth holding onto, since it's core to the mockup's mission-control feel.
- Everything else here is a helpful default — override freely if it makes the UI look better.
