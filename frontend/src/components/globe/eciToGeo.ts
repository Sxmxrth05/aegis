import { eciToGeodetic, degreesLat, degreesLong, gstime } from 'satellite.js';

/**
 * Converts a TrackedObject's ECI position_km + timestamp_utc into the
 * lat/lng/alt react-globe.gl expects. satellite.js's eciToGeodetic only
 * needs a position vector + GMST — it doesn't require re-propagating from
 * the TLE, so this works directly on backend-supplied position_km.
 */
export function positionKmToGeo(
  positionKm: readonly [number, number, number],
  timestampUtc: string,
): { lat: number; lng: number; alt: number } {
  const date = new Date(timestampUtc);
  const gmst = gstime(date);
  const geodetic = eciToGeodetic({ x: positionKm[0], y: positionKm[1], z: positionKm[2] }, gmst);

  // react-globe.gl's pointAltitude is a fraction of Earth's radius, not km.
  const EARTH_RADIUS_KM = 6371;

  return {
    lat: degreesLat(geodetic.latitude),
    lng: degreesLong(geodetic.longitude),
    alt: geodetic.height / EARTH_RADIUS_KM,
  };
}
