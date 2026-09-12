# Library Docs

How Aegis specifically uses each of its dependencies. This documents project-specific patterns and gotchas — not general library tutorials. Check here before reaching for a library's general-purpose API if the pattern you need is already defined below.

---

## Before Using Any Library

Check this file first for the project-specific pattern. If it's not covered here, use the library's standard approach and add a short entry once you've worked out the pattern, so the next session/component benefits.

---

## CelesTrak (TLE data)

**Check first:** `backend/app/data/celestrak.py`

### Fetching the demo object set
```python
import httpx

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"

async def fetch_tle_group(group: str = "starlink") -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CELESTRAK_URL, params={"GROUP": group, "FORMAT": "json"})
        resp.raise_for_status()
        return resp.json()
```

**Rules:**
- Always cache the response to `data/cache/tle_snapshot.json` on successful fetch.
- On fetch failure, fall back to the last cached snapshot — never let the demo hard-depend on live network.
- No auth required — do not add API key handling for this endpoint.

---

## sgp4 (orbital propagation)

**Check first:** `backend/app/agents/monitor_agent.py`

### Propagating a TLE to ECI position
```python
from sgp4.api import Satrec, jday
from datetime import datetime

def propagate(tle_line1: str, tle_line2: str, when: datetime):
    sat = Satrec.twoline2rv(tle_line1, tle_line2)
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second)
    error, position, velocity = sat.sgp4(jd, fr)
    if error != 0:
        raise ValueError(f"SGP4 propagation error code {error}")
    return position, velocity  # km, km/s, in TEME frame
```

**Rules:**
- Check `error != 0` every call — never propagate a satellite with a nonzero error code.
- Discard/flag TLEs older than ~5 days (check the epoch field) before using them for conjunction math.
- This is CPU-bound and synchronous — for the demo's small curated object set this is fine to call directly; do not try to parallelize/optimize this for the hackathon.

---

## satellite.js (frontend propagation, optional)

**Check first:** `frontend/src/lib/propagate.ts`

Use this only if you want smooth client-side orbit animation between backend updates. If the backend already streams position updates frequently enough over WebSocket, this may not be needed — don't build it speculatively.

```typescript
import * as satellite from 'satellite.js';

export function propagateToLatLngAlt(tleLine1: string, tleLine2: string, date: Date) {
  const satrec = satellite.twoline2satrec(tleLine1, tleLine2);
  const posVel = satellite.propagate(satrec, date);
  const gmst = satellite.gstime(date);
  const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
  return {
    lat: satellite.degreesLat(geodetic.latitude),
    lng: satellite.degreesLong(geodetic.longitude),
    alt: geodetic.height,
  };
}
```

---

## react-globe.gl

**Check first:** `frontend/src/components/globe/`

### Basic usage pattern
```tsx
import Globe from 'react-globe.gl';

<Globe
  globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
  pointsData={satellites}
  pointLat="lat"
  pointLng="lng"
  pointColor="statusColor"
  arcsData={orbitPaths}
  ringsData={conjunctionAlerts}
/>
```

**Rules:**
- Build **one** configurable Globe component and drive it via props for all three modes (live view, conjunction highlight, before/after trajectory) rather than three separate globes — see `architecture.md` folder structure.
- Keep the rendered object count limited to the curated demo set — don't attempt to render the full TLE catalog.
- `earth-night.jpg` (bundled example texture) matches the dark aesthetic well; no need to source a custom texture unless there's spare time.

---

## Anthropic SDK (Claude)

**Check first:** `backend/app/agents/operator_agent.py`

### Tool-calling pattern for deterministic yield_score
```python
import anthropic

client = anthropic.Anthropic()

async def get_agent_justification(agent_state: dict, yield_score: float) -> str:
    # yield_score is computed BEFORE this call, by cost_functions.py — never by the LLM
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                f"You are the negotiation agent for {agent_state['operator']}. "
                f"Your computed yield_score is {yield_score:.2f} "
                f"(mission priority {agent_state['mvi']}, fuel margin {agent_state['fuel_margin_pct']}%). "
                "Write a 1-2 sentence justification for this position, in plain operational language."
            ),
        }],
    )
    return response.content[0].text
```

**Rules:**
- The LLM only ever narrates a number that's already been computed — never ask it to compute or return the yield_score/Δv itself.
- Validate/sanity-check the response length before displaying (guard against overly long or malformed output); on failure, fall back to a simple templated justification string so the negotiation still proceeds.
- Keep `max_tokens` low (200-400) — this is narration, not analysis, and keeps demo latency down.

---

## FastAPI WebSockets

**Check first:** `backend/app/orchestrator/websocket_manager.py`

**Rules:**
- Every broadcast message includes a monotonically increasing `sequence` field; frontend discards/reorders anything arriving out of sequence.
- On new client connection, always send a full current-state snapshot before streaming further deltas.
- Wrap all WebSocket sends in try/except — a failed send to one disconnected client must not crash the broadcast loop for others.

---

## Zustand

**Check first:** `frontend/src/store/useNegotiationStore.ts`

```typescript
import { create } from 'zustand';

export const useNegotiationStore = create<NegotiationState>((set) => ({
  satellites: [],
  activeConjunction: null,
  messages: [],
  updateFromSocket: (event) => set((state) => ({ /* merge event into state */ })),
}));
```

**Rules:**
- One store for live negotiation/globe state is enough for this app's scope — don't over-split into many small stores.
- All WebSocket message handling funnels through a single `updateFromSocket`-style action so state updates stay predictable.

---

## Tailwind CSS

**Check first:** `ui-tokens.md`, `ui-rules.md`

Standard Tailwind v4 `@theme` directive usage, referencing the CSS variables defined in `globals.css`. No project-specific gotchas beyond what's already covered in the design token files.
