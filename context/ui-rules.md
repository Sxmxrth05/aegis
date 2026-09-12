# UI Rules

A lightweight companion to `ui-tokens.md` — practical starting patterns for building Aegis's screens, not a rigid rulebook. Use good judgment; deviate where it makes the product look and feel better, especially anywhere it helps you get closer to the reference mockup's polished, mission-control aesthetic.

---

## Font

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```
Apply `font-sans` (Inter) as the base body font; reach for `font-mono` on stat numbers, satellite IDs, and timestamps where it helps the technical feel.

---

## Layout

Suggested starting points — adjust per screen as needed:
- Max content width: ~1440px for dashboard screens, centered
- Main content padding: 24-32px
- Gap between major sections/cards: 16-24px
- Top nav height: ~64px, persistent across pages
- Globe-centric screens (Monitor, Negotiate, Trajectory) can go full-bleed/full-width for the globe itself, with side panels overlaying or docked

---

## Navigation

Top nav bar, dark `surface` background, subtle bottom border. Active page: `text-primary` + accent underline or subtle background pill. Inactive: `text-secondary`, hover to `text-primary`. A small live-status indicator (dot + "Live" label in `success` or `text-muted`) on the right, as in the mockup.

---

## Cards

Dark `surface` background, `border border-border`, rounded corners (~16px), no colored backgrounds — introduce color via badges, status dots, or small accent bars inside the card rather than tinting the whole card.

---

## Typography Hierarchy

Follow `ui-tokens.md`'s typography table as a starting point. Section headings should read clearly against the dark background; body text can sit a shade dimmer (`text-secondary`) to create hierarchy without needing heavier font weights everywhere.

---

## Badges & Status Indicators

Small rounded pills using the semantic `-muted` background + `-light` text combo for a soft glow look. Match the mockup's legend: blue/accent = active, red/danger = debris or hazard, amber/warning = selected or pending, green/success = resolved.

---

## Buttons

Primary: solid accent background, white text. Secondary/ghost: bordered, transparent background. Keep these consistent across screens once you land on a look you like — it's fine to iterate on the exact recipe early and lock it in once it feels right.

---

## Form Inputs (search/filter fields)

Dark `surface-secondary` background, `border border-border`, subtle accent-colored focus ring. Placeholder text in `text-muted`.

---

## Tables (History page)

Subtle row dividers (`border-muted`), gentle row hover highlight, status shown via badge in the last column rather than colored row backgrounds.

---

## The Globe

This is the centerpiece — give it room to breathe. Points layer for satellites/debris (color-coded per the legend), arcs for orbit paths, rings/pulses for conjunction alerts and hazard markers. A floating legend panel (as in the mockup) helps orient the viewer. Feel free to experiment with subtle atmosphere/glow effects on the globe itself if react-globe.gl's options make that easy — it's a strong visual payoff for relatively little effort.

---

## Empty States

Keep simple: muted icon or illustration, one line of `text-secondary` explaining the empty state, and a CTA button where relevant (e.g. "No conjunctions detected — Monitor is scanning").

---

## Loose Guidance, Not Hard Rules

The one thing worth holding firm on: **no full colored-background cards** — keep the dark base and introduce color through accents, since that's core to the mission-control look. Everything else in this file is a helpful starting point. If something looks better with a tweak once it's actually on screen, make the tweak — matching the feel and quality of the reference mockup matters more than matching this document to the letter.
