# AGENTS.md

This is Aegis — an autonomous multi-agent orbital collision de-confliction system (FastAPI + WebSocket backend, React/Vite + react-globe.gl frontend), built by a 4-developer team working in parallel workstreams.

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

Always check `progress-tracker.md` first within that read to see what's already done, which workstream owns what, and what's next — don't re-build or duplicate completed features, and don't touch another developer's workstream files without checking `code-standards.md`'s ownership map first.

## Non-Negotiable Rules

- Any number that affects a safety decision (Δv, miss distance, yield_score) comes from deterministic Python code, never directly from LLM output. The LLM only narrates and calls tools. (See `architecture.md` §Invariants.)
- Update `progress-tracker.md` after every completed task — mark it `[x]`/`[M]`/`[V]` per its status legend, update your own workstream's rows only, and add a one-line decision/note if anything non-obvious came up.
- Update `ui-registry.md` after building any new UI component — check it first for a similar existing pattern before building something new.
- Before using any third-party library, check `library-docs.md` for the project-specific pattern before defaulting to general/training knowledge.
- Follow `build-plan.md`'s phase and workstream order — work within your own ownership boundary (see `code-standards.md` §File & Folder Ownership), verify each task before moving to the next, and don't merge past a Checkpoint until the checkpoint's integration verification actually passes as a team. Don't jump ahead into Phase 7 stretch features before Phase 3 (demo hardening) is solid end-to-end.
- Design tokens/rules in `ui-tokens.md`/`ui-rules.md` are strong defaults, not rigid law — deviate where it visibly improves the result, especially to match the reference mockup's polish.
- No full colored-background cards — this is the one hard visual rule (see `ui-rules.md`).
- Cached/offline fallback paths (CelesTrak, NOAA) are the actual demo-day path, not edge-case handling — treat them as first-class, not optional.

## Tech Stack Quick Reference

- **Backend:** FastAPI, WebSockets, `sgp4`, Pydantic, Anthropic API (`anthropic` SDK) — `backend/`
- **Frontend:** React + Vite, `react-globe.gl`, `satellite.js` (optional), Tailwind CSS, Zustand — `frontend/`
- **Data:** CelesTrak (TLE, no auth), NOAA SWPC (Kp-index, Phase 2, no auth)
- **Persistence:** SQLite / local JSON cache — no external DB service

## If Something Breaks

If the same problem persists after one corrective attempt, stop and re-read `architecture.md`'s data flow and invariants sections before trying again — don't keep patching blindly. If it's a cross-workstream integration issue, check `progress-tracker.md` §10 (Blockers) before assuming it's your own code.

Keep this file itself short. Detail lives in the numbered context files above.
