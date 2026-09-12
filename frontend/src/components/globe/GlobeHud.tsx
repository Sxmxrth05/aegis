type HudMarker = {
  noradId: string;
  name: string;
  x: number;
  y: number;
  flagged: boolean;
};

export function GlobeHud({ markers }: { markers: HudMarker[] }) {
  return (
    <div className="globe-hud" aria-hidden="true">
      <svg className="globe-hud__frame" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path d="M1 10V1h9M90 1h9v9M99 90v9h-9M10 99H1v-9" />
        <path className="globe-hud__hairline" d="M50 0v8M50 92v8M0 50h8M92 50h8" />
      </svg>
      <div className="globe-hud__reticle">ECI → GEO</div>
      {markers.map((marker) => (
        <div
          key={marker.noradId}
          className={`globe-hud__marker ${marker.flagged ? 'globe-hud__marker--alert' : ''}`}
          style={{ transform: `translate(${marker.x}px, ${marker.y}px)` }}
        >
          <span className="globe-hud__marker-dot" />
          <span className="globe-hud__marker-label">{marker.name}<small>{marker.noradId}</small></span>
        </div>
      ))}
    </div>
  );
}
