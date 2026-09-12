# AGENTS.md

This is Aegis — an autonomous multi-agent orbital collision de-confliction system (FastAPI + WebSocket backend, React/Vite + react-globe.gl frontend).

## Before Writing Any Code

Read these files, in this exact order:

1. `context/project-overview.md`
2. `context/architecture.md`
3. `context/ui-tokens.md`
4. `context/ui-rules.md`
5. `context/ui-registry.md`
6. `context/code-standards.md`
7. `context/library-docs.md`
8. `context/build-plan.md`
9. `context/progress-tracker.md`

Always check `progress-tracker.md` first within that read to see what's already done and what's next — don't re-build or duplicate completed features.

## Non-Negotiable Rules

- Any number that affects a safety decision (Δv, miss distance, yield_score) comes from deterministic Python code, never directly from LLM output. The LLM only narrates and calls tools. (See `architecture.md` §Invariants.)
- Update `progress-tracker.md` after every completed feature — mark it `[x]`, update "Current Status," and add a one-line decision/note if anything non-obvious came up.
- Update `ui-registry.md` after building any new UI component — check it first for a similar existing pattern before building something new.
- Before using any third-party library, check `library-docs.md` for the project-specific pattern before defaulting to general/training knowledge.
- Follow `build-plan.md`'s phase order — build one feature at a time, verify it works (visually or via a quick script), then move to the next. Don't jump ahead into Phase 7 stretch features before Phase 6 is solid end-to-end.
- Design tokens/rules in `ui-tokens.md`/`ui-rules.md` are strong defaults, not rigid law — deviate where it visibly improves the result, especially to match the reference mockup's polish.
- No full colored-background cards — this is the one hard visual rule (see `ui-rules.md`).
- Cached/offline fallback paths (CelesTrak, NOAA) are the actual demo-day path, not edge-case handling — treat them as first-class, not optional.

## Tech Stack Quick Reference

- **Backend:** FastAPI, WebSockets, `sgp4`, Pydantic, Anthropic API (`anthropic` SDK)
- **Frontend:** React + Vite, `react-globe.gl`, `satellite.js` (optional), Tailwind CSS, Zustand
- **Data:** CelesTrak (TLE, no auth), NOAA SWPC (Kp-index, Phase 2, no auth)
- **Persistence:** SQLite / local JSON cache — no external DB service

## If Something Breaks

If the same problem persists after one corrective attempt, stop and re-read `architecture.md`'s data flow and invariants sections before trying again — don't keep patching blindly.

Keep this file itself short. Detail lives in the numbered context files above.
