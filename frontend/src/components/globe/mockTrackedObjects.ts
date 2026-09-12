import type { TrackedObject } from './types';

/**
 * Hand-written mock TrackedObjects, matching backend/app/schemas/tracked_object.py's
 * Pydantic schema exactly (norad_id, name, tle_line1, tle_line2, timestamp_utc,
 * position_km, velocity_kmps).
 *
 * These aren't fabricated numbers — position_km/velocity_kmps were produced by
 * actually running satellite.js's SGP4 propagation against each object's real TLE
 * at the fixed timestamp below, so the state vectors are physically consistent.
 *
 * TODO(Dev A): replace this array with the real Phase 0 TrackedObject mock
 * fixture (or live data via lib/websocket.ts) once it lands — Globe's
 * `trackedObjects` prop shape won't need to change.
 */
export const MOCK_TRACKED_OBJECTS: TrackedObject[] = [
  {
    norad_id: '25544',
    name: 'ISS (ZARYA)',
    tle_line1: '1 25544U 98067A   26014.25000000  .00016717  00000-0  10270-3 0  9000',
    tle_line2: '2 25544  51.6400 208.9163 0006317  69.9862  25.2906 15.50377579100000',
    timestamp_utc: '2026-01-14T06:00:00.000Z',
    position_km: [2577.608, -3366.514, 5294.249],
    velocity_kmps: [6.472113, 4.076564, -0.554895],
  },
  {
    norad_id: '48274',
    name: 'CSS (TIANHE)',
    tle_line1: '1 48274U 21035A   26014.30000000  .00021000  00000-0  22000-3 0  9001',
    tle_line2: '2 48274  41.4700 120.5000 0002000  90.0000 270.1000 15.61000000100000',
    timestamp_utc: '2026-01-14T06:00:00.000Z',
    position_km: [-4940.837, -1409.384, 4385.342],
    velocity_kmps: [2.895302, -7.049348, 0.993401],
  },
  {
    norad_id: '44713',
    name: 'STARLINK-1007',
    tle_line1: '1 44713U 19074A   26014.40000000  .00002000  00000-0  15000-3 0  9002',
    tle_line2: '2 44713  53.0000  60.0000 0001200  80.0000 280.1000 15.06000000100000',
    timestamp_utc: '2026-01-14T06:00:00.000Z',
    position_km: [3419.274, -2418.406, -5524.09],
    velocity_kmps: [3.952255, 6.453008, -0.378761],
  },
  {
    norad_id: '36086',
    name: 'POISK',
    tle_line1: '1 36086U 09049A   26014.20000000  .00010000  00000-0  90000-4 0  9003',
    tle_line2: '2 36086  51.6400 210.0000 0006000  75.0000  20.0000 15.50000000100000',
    timestamp_utc: '2026-01-14T06:00:00.000Z',
    position_km: [-5213.496, -4157.61, 1290.823],
    velocity_kmps: [3.911567, -3.075879, 5.830827],
  },
  {
    norad_id: '68689',
    name: 'CYGNUS NG-24 (DEBRIS-TAGGED)',
    tle_line1: '1 68689U 24160A   26014.10000000  .00030000  00000-0  35000-3 0  9004',
    tle_line2: '2 68689  51.6400 205.0000 0005500  60.0000  35.0000 15.51000000100000',
    timestamp_utc: '2026-01-14T06:00:00.000Z',
    position_km: [4236.171, 4444.603, -2919.122],
    velocity_kmps: [-5.451392, 1.903278, -5.025646],
  },
];
