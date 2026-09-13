/**
 * Background satellite layer — decorative density only.
 *
 * Fetches 20 real objects from CelesTrak's "visual" group (brightest/most
 * tracked objects, separate from the monitored LOCKED_OBJECTS "stations"
 * group). Used exclusively for the cosmetic background cloud on the Monitor
 * globe. These objects are NEVER:
 *   - passed to detect_conjunctions()
 *   - counted in Monitor's Tracking Register
 *   - rendered with HUD labels (avoids the label-overlap bug)
 *
 * Rendered via a named Three.js Points mesh added directly to globe.scene()
 * so they are completely outside react-globe.gl's pointsData pipeline.
 *
 * Owner: Dev C  |  Branch: dev-c/globe-background-satellites
 */

import {
  degreesLat,
  degreesLong,
  gstime,
  eciToGeodetic,
  twoline2satrec,
  propagate,
} from 'satellite.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type BackgroundPoint = {
  /** Fractional altitude above Earth surface (React-Globe.gl units: Earth radii). */
  lat: number;
  lng: number;
  /** Fractional altitude above Earth surface (react-globe.gl: fraction of Earth radius). */
  alt: number;
};

// ---------------------------------------------------------------------------
// CelesTrak endpoint — "visual" group (brightest objects, ~150 entries)
// This is intentionally a DIFFERENT group from the "stations" group used
// by the monitored 20-object set (LOCKED_OBJECTS in celestrak.py).
// ---------------------------------------------------------------------------

const PROXY_VISUAL_TLE_URL =
  '/celestrak/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle';
const DIRECT_VISUAL_TLE_URL =
  'https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle';

const REQUEST_TIMEOUT_MS = 20000;

// ---------------------------------------------------------------------------
// Static fallback — 20 NORAD IDs spread across orbital regimes + approximate
// positions. Used when the live fetch fails so the background layer degrades
// gracefully instead of crashing. Positions are geodetic approximations
// (not SGP4-propagated) — acceptable for a purely cosmetic background cloud.
// ---------------------------------------------------------------------------

const STATIC_FALLBACK_POINTS: BackgroundPoint[] = [
  // LEO — ISS-adjacent plane
  { lat: 41.2, lng: -73.5, alt: 0.063 },
  { lat: -28.7, lng: 134.8, alt: 0.068 },
  { lat: 15.3, lng: 42.1, alt: 0.059 },
  { lat: -52.1, lng: -65.4, alt: 0.071 },
  { lat: 62.4, lng: 105.3, alt: 0.065 },
  // Mid-inclination LEO
  { lat: 20.5, lng: 160.2, alt: 0.055 },
  { lat: -10.3, lng: -30.1, alt: 0.058 },
  { lat: 35.7, lng: 78.4, alt: 0.062 },
  { lat: -40.2, lng: 20.5, alt: 0.057 },
  { lat: 50.1, lng: -140.6, alt: 0.060 },
  // Sun-synchronous / polar
  { lat: 78.5, lng: 30.2, alt: 0.088 },
  { lat: -75.3, lng: -55.1, alt: 0.085 },
  { lat: 82.4, lng: 170.5, alt: 0.090 },
  { lat: -68.1, lng: 95.3, alt: 0.087 },
  { lat: 70.2, lng: -110.3, alt: 0.089 },
  // Higher LEO / sparse MEO boundary
  { lat: 5.8, lng: -80.2, alt: 0.105 },
  { lat: -22.4, lng: 55.3, alt: 0.100 },
  { lat: 48.6, lng: -20.1, alt: 0.098 },
  { lat: -35.5, lng: 145.7, alt: 0.102 },
  { lat: 25.1, lng: -155.4, alt: 0.096 },
];

// How many objects we want from the live fetch.
// Spread across the result set using a deterministic stride so we don't
// just grab the first N objects (which tend to cluster in one orbital plane).
const TARGET_COUNT = 20;

// ---------------------------------------------------------------------------
// TLE parsing helpers
// ---------------------------------------------------------------------------

/**
 * Parse raw CelesTrak TLE text into a list of [name, line1, line2] triples.
 * Only keeps structurally valid 3-line blocks.
 */
function parseTleText(raw: string): Array<[string, string, string]> {
  const lines = raw.split('\n').map((l) => l.trim()).filter(Boolean);
  const triples: Array<[string, string, string]> = [];

  for (let i = 0; i + 2 < lines.length; i += 3) {
    const name = lines[i];
    const line1 = lines[i + 1];
    const line2 = lines[i + 2];
    if (line1?.startsWith('1 ') && line2?.startsWith('2 ')) {
      triples.push([name, line1, line2]);
    }
  }

  return triples;
}

/**
 * Propagate a single TLE to the given epoch and return a BackgroundPoint,
 * or null if propagation fails (bad TLE, sub-orbital decay, etc.).
 */
function propagateTle(
  line1: string,
  line2: string,
  epoch: Date,
): BackgroundPoint | null {
  try {
    const satrec = twoline2satrec(line1, line2);
    const result = propagate(satrec, epoch);

    const position = result?.position;
    if (!position || typeof position === 'boolean') return null;

    // position is in km (ECI frame) — same conversion as eciToGeo.ts
    const gmst = gstime(epoch);
    const geo = eciToGeodetic(position as { x: number; y: number; z: number }, gmst);

    const EARTH_RADIUS_KM = 6371;
    const altFraction = (geo.height as number) / EARTH_RADIUS_KM;

    // Discard objects with unrealistic altitudes (sub-orbital or very high MEO+)
    if (altFraction < 0.01 || altFraction > 2.5) return null;

    return {
      lat: degreesLat(geo.latitude),
      lng: degreesLong(geo.longitude),
      alt: altFraction,
    };
  } catch {
    return null;
  }
}

/**
 * Select ~TARGET_COUNT objects from a list using a deterministic stride so
 * we sample broadly across orbital planes rather than clustering at the top.
 */
function selectSpread<T>(items: T[], count: number): T[] {
  if (items.length <= count) return items;
  const stride = Math.floor(items.length / count);
  return Array.from({ length: count }, (_, i) => items[i * stride]);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Fetch 20 real objects from CelesTrak's "visual" group, propagate each to
 * the current time, and return a BackgroundPoint[].
 *
 * Falls back to STATIC_FALLBACK_POINTS if the live fetch fails or returns
 * fewer than 5 valid points. Never throws — the caller can treat an empty
 * or static-fallback result as graceful degradation.
 */
export async function fetchBackgroundSatellites(): Promise<BackgroundPoint[]> {
  const epoch = new Date();

  try {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let raw: string = '';
    try {
      // 1. Try proxy URL first (fast, bypasses local browser CORS/DNS latency)
      try {
        const resp = await fetch(PROXY_VISUAL_TLE_URL, {
          signal: controller.signal,
          headers: { 'Accept': 'text/plain' },
        });
        if (resp.ok) {
          raw = await resp.text();
        }
      } catch {
        // Fall back to direct URL
      }

      // 2. Fall back to direct CelesTrak URL if proxy didn't return text
      if (!raw || raw.length < 100) {
        const resp = await fetch(DIRECT_VISUAL_TLE_URL, {
          signal: controller.signal,
          headers: { 'Accept': 'text/plain' },
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        raw = await resp.text();
      }
    } finally {
      window.clearTimeout(timeoutId);
    }

    const triples = parseTleText(raw);
    if (triples.length < 5) {
      throw new Error(`Too few TLE objects returned (${triples.length})`);
    }

    // Select a spread of candidate triples, propagate, drop failures.
    const candidates = selectSpread(triples, TARGET_COUNT * 3);
    const points: BackgroundPoint[] = [];

    for (const [, line1, line2] of candidates) {
      if (points.length >= TARGET_COUNT) break;
      const pt = propagateTle(line1, line2, epoch);
      if (pt) points.push(pt);
    }

    if (points.length < 5) {
      throw new Error(`Too few valid propagations (${points.length})`);
    }

    if (import.meta.env.DEV) {
      console.info(`[aegis] Successfully loaded and propagated ${points.length} background satellites from CelesTrak (visual group)`);
    }

    return points;
  } catch (err) {
    // Silent graceful degradation — background layer is cosmetic, never critical.
    // Log only in development so production stays clean.
    if (import.meta.env.DEV) {
      console.debug('[aegis] Background satellite fetch fell back to static positions:', err);
    }
    return STATIC_FALLBACK_POINTS;
  }
}
