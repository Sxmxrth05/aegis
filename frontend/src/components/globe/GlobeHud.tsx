type HudMarkerMember = {
  noradId: string;
  name: string;
};

type HudMarker = {
  noradId: string;
  name: string;
  x: number;
  y: number;
  flagged: boolean;
  /** >1 when this marker represents several overlapping objects merged into
   * one combined label (see Globe.tsx's clusterHudPoints). */
  count: number;
  members: HudMarkerMember[];
};

export function GlobeHud({ markers }: { markers: HudMarker[] }) {
  return (
    <div className="globe-hud" aria-hidden="true">
      {markers.map((marker) => {
        const isCluster = marker.count > 1;
        return (
          <div
            key={marker.noradId}
            className={`globe-hud__marker ${marker.flagged ? 'globe-hud__marker--alert' : ''} ${isCluster ? 'globe-hud__marker--cluster' : ''}`}
            style={{ transform: `translate(${marker.x}px, ${marker.y}px)` }}
            title={isCluster ? marker.members.map((m) => `${m.name} (${m.noradId})`).join('\n') : undefined}
          >
            <span className="globe-hud__marker-dot" />
            <span className="globe-hud__marker-label">
              {isCluster ? `${marker.name} (${marker.count})` : marker.name}
              <small>{isCluster ? 'hover for members' : marker.noradId}</small>
            </span>
          </div>
        );
      })}
    </div>
  );
}
