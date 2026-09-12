import { useEffect, useMemo, useRef, useState } from 'react';
import ReactGlobe, { type GlobeMethods } from 'react-globe.gl';
import earthNightTexture from '../../assets/earth-night.jpg';

import { positionKmToGeo } from './eciToGeo';
import type { ConjunctionAlert, TrackedObject, ManeuverTrajectoryResult } from './types';

export type GlobeMode = 'live' | 'conjunction' | 'trajectory';

type Props = {
  trackedObjects: TrackedObject[];
  mode: GlobeMode;
  conjunctionAlert?: ConjunctionAlert;
  trajectoryResult?: ManeuverTrajectoryResult;
  className?: string;
};

type GlobePoint = {
  norad_id: string;
  name: string;
  lat: number;
  lng: number;
  alt: number;
  isFlagged: boolean;
};

type GlobeRing = {
  lat: number;
  lng: number;
};

// Matches the accent/danger tokens in ui-tokens.md — same color language as
// D3's Badge (accent = active, danger = hazard/debris).
const ACCENT_COLOR = '#3b82f6';
const DANGER_COLOR = '#ef4444';

export function Globe({ trackedObjects, mode, conjunctionAlert, trajectoryResult, className = '' }: Props) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  // react-globe.gl sizes itself off explicit width/height, not its parent —
  // fill whatever container the caller gives it (full-bleed on Monitor, a
  // smaller docked panel elsewhere) rather than requiring pixel props.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const flaggedIds = useMemo(() => {
    if (!conjunctionAlert) return new Set<string>();
    return new Set([conjunctionAlert.primary_id, conjunctionAlert.secondary_id]);
  }, [conjunctionAlert]);

  const points = useMemo<GlobePoint[]>(
    () =>
      trackedObjects.map((obj) => {
        const geo = positionKmToGeo(obj.position_km, obj.timestamp_utc);
        return {
          norad_id: obj.norad_id,
          name: obj.name,
          ...geo,
          isFlagged: flaggedIds.has(obj.norad_id),
        };
      }),
    [trackedObjects, flaggedIds],
  );

  // 'trajectory' mode currently renders the same as 'live' — before/after
  // maneuver arcs depend on Dev A's Phase 2 propagation arrays, not yet
  // available. The mode prop is wired now so Trajectory.tsx can reuse this
  // same Globe instance later without a prop-shape change (invariant: one
  // configurable Globe, not three).
  const rings = useMemo<GlobeRing[]>(() => {
    if (mode !== 'conjunction' || !conjunctionAlert) return [];
    return points.filter((p) => p.isFlagged).map(({ lat, lng }) => ({ lat, lng }));
  }, [mode, conjunctionAlert, points]);

  const pathsData = useMemo(() => {
    if (mode !== 'trajectory' || !trajectoryResult) return [];
    const convert = (path: [number, number, number][]) => path.map(([lng, lat, alt]) => ({ lat, lng, alt }));
    return [
      { coords: convert(trajectoryResult.nominal_path_primary), color: '#9ca3b8' }, // text-secondary
      { coords: convert(trajectoryResult.nominal_path_secondary), color: '#9ca3b8' },
      { coords: convert(trajectoryResult.maneuvered_path), color: '#3b82f6' } // accent
    ];
  }, [mode, trajectoryResult]);

  return (
    <div ref={containerRef} className={`relative h-full w-full ${className}`}>
      <ReactGlobe
        ref={globeRef}
        width={size.width || undefined}
        height={size.height || undefined}
        globeImageUrl={earthNightTexture}
        backgroundColor="rgba(0,0,0,0)"
        atmosphereColor="#3b82f6"
        atmosphereAltitude={0.18}
        pointsData={points}
        pointLat="lat"
        pointLng="lng"
        pointAltitude="alt"
        pointColor={(p) => ((p as GlobePoint).isFlagged ? DANGER_COLOR : ACCENT_COLOR)}
        pointRadius={(p) => ((p as GlobePoint).isFlagged ? 0.6 : 0.35)}
        pointResolution={32}
        pointLabel={(p) => `${(p as GlobePoint).name} (${(p as GlobePoint).norad_id})`}
        ringsData={rings}
        ringLat="lat"
        ringLng="lng"
        ringColor={() => (t: number) => `rgba(239, 68, 68, ${1 - t})`}
        ringResolution={128}
        ringMaxRadius={3}
        ringPropagationSpeed={2}
        ringRepeatPeriod={1600}
        pathsData={pathsData}
        pathPoints="coords"
        pathPointLat="lat"
        pathPointLng="lng"
        pathPointAlt="alt"
        pathColor="color"
        pathDashLength={0.1}
        pathDashGap={0.05}
        pathDashAnimateTime={3000}
      />
    </div>
  );
}
