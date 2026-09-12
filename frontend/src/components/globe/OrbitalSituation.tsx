import 'cesium/Build/Cesium/Widgets/widgets.css';
import * as Cesium from 'cesium';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Viewer,
  Entity,
  PointGraphics,
  LabelGraphics,
  PolylineGraphics,
  Clock,
  type CesiumComponentRef,
} from 'resium';

/* ─── CONSTANTS & ORBITAL CONSTANTS ────────────────────────── */

const EARTH_RADIUS = 6378137.0; // meters
const ALT_A = 550000.0; // 550 km
const ALT_B = 548000.0; // 548 km
const ALT_REF = 620000.0; // 620 km

const RAD_A = EARTH_RADIUS + ALT_A;
const RAD_B = EARTH_RADIUS + ALT_B;
const RAD_REF = EARTH_RADIUS + ALT_REF;

const INC_A = (51.6 * Math.PI) / 180;
const RAAN_A = (10.0 * Math.PI) / 180;

const INC_B = (53.4 * Math.PI) / 180;
const RAAN_B = (34.0 * Math.PI) / 180;

const INC_REF = (72.0 * Math.PI) / 180;
const RAAN_REF = (140.0 * Math.PI) / 180;

const PERIOD_A = 5735; // ~95.6 min
const PERIOD_B = 5730; // ~95.5 min
const PERIOD_REF = 5820; // ~97 min

// Conjunction time chosen at 35 min into simulation
const CONJUNCTION_TIME_OFFSET = 35 * 60; // 2100 seconds

/* compute Cartesian3 orbit position at time t (seconds from start) */
function computeOrbitPosition(
  r: number,
  inc: number,
  raan: number,
  period: number,
  phaseOffset: number,
  t: number,
): Cesium.Cartesian3 {
  const u = (2 * Math.PI * t) / period + phaseOffset;
  const x = r * (Math.cos(raan) * Math.cos(u) - Math.sin(raan) * Math.sin(u) * Math.cos(inc));
  const y = r * (Math.sin(raan) * Math.cos(u) + Math.cos(raan) * Math.sin(u) * Math.cos(inc));
  const z = r * (Math.sin(u) * Math.sin(inc));
  return new Cesium.Cartesian3(x, y, z);
}

/* compute orbital track polyline positions (full loop) */
function generateOrbitLoop(r: number, inc: number, raan: number, points = 128): Cesium.Cartesian3[] {
  const coords: Cesium.Cartesian3[] = [];
  for (let i = 0; i <= points; i++) {
    const u = (2 * Math.PI * i) / points;
    const x = r * (Math.cos(raan) * Math.cos(u) - Math.sin(raan) * Math.sin(u) * Math.cos(inc));
    const y = r * (Math.sin(raan) * Math.cos(u) + Math.cos(raan) * Math.sin(u) * Math.cos(inc));
    const z = r * (Math.sin(u) * Math.sin(inc));
    coords.push(new Cesium.Cartesian3(x, y, z));
  }
  return coords;
}

export type ViewMode = 'ORBIT' | 'RISK';
export type SelectedSat = 'SAT-A' | 'SAT-B' | null;

export function OrbitalSituation() {
  const viewerRef = useRef<CesiumComponentRef<Cesium.Viewer>>(null);

  // Time & simulation states
  const [isPlaying, setIsPlaying] = useState(true);
  const [speedMultiplier, setSpeedMultiplier] = useState(60);
  const [viewMode, setViewMode] = useState<ViewMode>('ORBIT');
  const [selectedSat, setSelectedSat] = useState<SelectedSat>('SAT-A');
  const [currentMissDistance, setCurrentMissDistance] = useState<number>(1.2);
  const [simTimeLabel, setSimTimeLabel] = useState<string>('T+00:00:00');

  // Simulation timeline boundaries (12h window)
  const startTime = useMemo(() => Cesium.JulianDate.fromDate(new Date('2026-09-12T12:00:00Z')), []);
  const stopTime = useMemo(() => Cesium.JulianDate.addHours(startTime, 12, new Cesium.JulianDate()), [startTime]);

  // Phase offsets calibrated so SAT-A and SAT-B meet at CONJUNCTION_TIME_OFFSET with ~1.2 km miss
  const phaseA = 0.52;
  const phaseB = 0.522; // slight offset produces ~1.2km miss distance

  // Precomputed orbit paths (polylines)
  const orbitPathA = useMemo(() => generateOrbitLoop(RAD_A, INC_A, RAAN_A), []);
  const orbitPathB = useMemo(() => generateOrbitLoop(RAD_B, INC_B, RAAN_B), []);
  const orbitPathRef = useMemo(() => generateOrbitLoop(RAD_REF, INC_REF, RAAN_REF), []);

  // Conjunction point in space
  const conjunctionPoint = useMemo(
    () => computeOrbitPosition(RAD_A, INC_A, RAAN_A, PERIOD_A, phaseA, CONJUNCTION_TIME_OFFSET),
    [],
  );

  // SampledPositionProperty for SAT-A
  const positionPropA = useMemo(() => {
    const prop = new Cesium.SampledPositionProperty();
    const step = 20; // sample every 20s
    for (let s = 0; s <= 12 * 3600; s += step) {
      const time = Cesium.JulianDate.addSeconds(startTime, s, new Cesium.JulianDate());
      const pos = computeOrbitPosition(RAD_A, INC_A, RAAN_A, PERIOD_A, phaseA, s);
      prop.addSample(time, pos);
    }
    return prop;
  }, [startTime]);

  // SampledPositionProperty for SAT-B
  const positionPropB = useMemo(() => {
    const prop = new Cesium.SampledPositionProperty();
    const step = 20;
    for (let s = 0; s <= 12 * 3600; s += step) {
      const time = Cesium.JulianDate.addSeconds(startTime, s, new Cesium.JulianDate());
      const pos = computeOrbitPosition(RAD_B, INC_B, RAAN_B, PERIOD_B, phaseB, s);
      prop.addSample(time, pos);
    }
    return prop;
  }, [startTime]);

  /* Viewer scene configuration on mount */
  const onViewerLoaded = useCallback((viewerInstance: Cesium.Viewer) => {
    if (!viewerInstance || viewerInstance.isDestroyed()) return;

    // Dark Earth / space technical styling
    const scene = viewerInstance.scene;
    const globe = scene.globe;

    scene.backgroundColor = Cesium.Color.fromCssColorString('#070b12');
    globe.baseColor = Cesium.Color.fromCssColorString('#0b1322');
    globe.enableLighting = false;
    globe.showAtmosphere = true;
    globe.atmosphereLightIntensity = 1.1;

    // Dim sun & moon glare for mission control instrument look
    if (scene.sun) scene.sun.show = false;
    if (scene.moon) scene.moon.show = false;
    if (scene.skyBox) scene.skyBox.show = false;

    // Initial camera position overlooking the conjunction area
    viewerInstance.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(-10, 24, 18500000),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-88),
        roll: 0.0,
      },
      duration: 0,
    });
  }, []);

  /* Track distance & clock updates */
  useEffect(() => {
    const viewer = viewerRef.current?.cesiumElement;
    if (!viewer || viewer.isDestroyed()) return;

    const clock = viewer.clock;
    clock.shouldAnimate = isPlaying;
    clock.multiplier = speedMultiplier;

    const removeListener = clock.onTick.addEventListener((clockInstance) => {
      const currentTime = clockInstance.currentTime;
      const secondsFromStart = Cesium.JulianDate.secondsDifference(currentTime, startTime);

      // Format simulation time
      const h = Math.floor(Math.abs(secondsFromStart) / 3600);
      const m = Math.floor((Math.abs(secondsFromStart) % 3600) / 60);
      const s = Math.floor(Math.abs(secondsFromStart) % 60);
      const sign = secondsFromStart >= 0 ? '+' : '-';
      setSimTimeLabel(`T${sign}${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);

      // Calculate instantaneous distance between SAT-A and SAT-B
      const posA = positionPropA.getValue(currentTime);
      const posB = positionPropB.getValue(currentTime);
      if (posA && posB) {
        const distKm = Cesium.Cartesian3.distance(posA, posB) / 1000;
        setCurrentMissDistance(Number(distKm.toFixed(1)));
      }
    });

    return () => {
      removeListener();
    };
  }, [isPlaying, speedMultiplier, startTime, positionPropA, positionPropB]);

  /* Camera smooth tracking */
  const handleTrackSatellite = useCallback(() => {
    const viewer = viewerRef.current?.cesiumElement;
    if (!viewer || viewer.isDestroyed()) return;

    const currentTime = viewer.clock.currentTime;
    let targetPos: Cesium.Cartesian3 | undefined;

    if (selectedSat === 'SAT-A') {
      targetPos = positionPropA.getValue(currentTime);
    } else if (selectedSat === 'SAT-B') {
      targetPos = positionPropB.getValue(currentTime);
    } else {
      targetPos = conjunctionPoint;
    }

    if (targetPos) {
      const carto = Cesium.Cartographic.fromCartesian(targetPos);
      const dest = Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, carto.height + 4200000);

      viewer.camera.flyTo({
        destination: dest,
        duration: 1.6,
        easingFunction: Cesium.EasingFunction.QUADRATIC_OUT,
      });
    }
  }, [selectedSat, positionPropA, positionPropB, conjunctionPoint]);

  /* Time scrub actions */
  const handleLive = () => {
    const viewer = viewerRef.current?.cesiumElement;
    if (!viewer || viewer.isDestroyed()) return;
    viewer.clock.currentTime = startTime;
    setSpeedMultiplier(10);
    setIsPlaying(true);
  };

  const handleAddHours = (hours: number) => {
    const viewer = viewerRef.current?.cesiumElement;
    if (!viewer || viewer.isDestroyed()) return;
    const newTime = Cesium.JulianDate.addHours(viewer.clock.currentTime, hours, new Cesium.JulianDate());
    viewer.clock.currentTime = newTime;
  };

  // Color logic based on viewMode
  const isRiskMode = viewMode === 'RISK';
  const isConjunctionClose = currentMissDistance < 15;

  return (
    <div className="relative w-full overflow-hidden rounded-[3px] border border-border bg-[#070b12] text-text-primary shadow-[0_12px_36px_-8px_rgba(10,14,23,0.95)]">
      {/* Top HUD Bar */}
      <div className="flex items-center justify-between border-b border-border/80 bg-[#0a0e17]/90 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          <span className="font-semibold text-text-primary">ORBITAL SITUATION // LEO SHELL-04</span>
        </div>
        <div className="flex items-center gap-3 text-text-muted">
          <span>{simTimeLabel}</span>
          <span className="hidden sm:inline text-border">|</span>
          <span className="hidden sm:inline">CONJUNCTION TCA: T+00:35:00</span>
        </div>
      </div>

      {/* 3D Cesium Container */}
      <div className="relative h-[340px] sm:h-[400px] lg:h-[430px] w-full bg-[#070b12]">
        <Viewer
          ref={viewerRef}
          full
          baseLayer={false}
          timeline={false}
          animation={false}
          baseLayerPicker={false}
          geocoder={false}
          homeButton={false}
          infoBox={false}
          navigationHelpButton={false}
          sceneModePicker={false}
          fullscreenButton={false}
          selectionIndicator={false}
          creditContainer={undefined}
          onReady={onViewerLoaded}
        >
          {/* Cesium Clock */}
          <Clock
            startTime={startTime}
            stopTime={stopTime}
            currentTime={startTime}
            clockRange={Cesium.ClockRange.LOOP_STOP}
            multiplier={speedMultiplier}
            shouldAnimate={isPlaying}
          />

          {/* SAT-A Orbit Polyline */}
          <Entity>
            <PolylineGraphics
              positions={orbitPathA}
              width={isRiskMode ? 1.2 : 1.6}
              material={
                isRiskMode
                  ? Cesium.Color.fromCssColorString('#3b82f6').withAlpha(0.4)
                  : Cesium.Color.fromCssColorString('#60a5fa').withAlpha(0.65)
              }
            />
          </Entity>

          {/* SAT-B Orbit Polyline */}
          <Entity>
            <PolylineGraphics
              positions={orbitPathB}
              width={isRiskMode ? 2.0 : 1.6}
              material={
                isRiskMode
                  ? Cesium.Color.fromCssColorString('#ef4444').withAlpha(0.85)
                  : Cesium.Color.fromCssColorString('#f87171').withAlpha(0.65)
              }
            />
          </Entity>

          {/* Unrelated Background Orbit Polyline (dimmed in RISK mode) */}
          <Entity>
            <PolylineGraphics
              positions={orbitPathRef}
              width={1.0}
              material={
                isRiskMode
                  ? Cesium.Color.fromCssColorString('#2a3449').withAlpha(0.12)
                  : Cesium.Color.fromCssColorString('#3b4b66').withAlpha(0.35)
              }
            />
          </Entity>

          {/* Conjunction Zone Entity */}
          <Entity position={conjunctionPoint}>
            <PointGraphics
              pixelSize={isRiskMode || isConjunctionClose ? 14 : 9}
              color={Cesium.Color.fromCssColorString('#ef4444').withAlpha(isRiskMode ? 0.95 : 0.7)}
              outlineColor={Cesium.Color.WHITE}
              outlineWidth={1}
            />
            <LabelGraphics
              text="CLOSE APPROACH\n1.2 KM"
              font="10px monospace"
              fillColor={Cesium.Color.fromCssColorString('#fca5a5')}
              outlineColor={Cesium.Color.fromCssColorString('#0a0e17')}
              outlineWidth={3}
              style={Cesium.LabelStyle.FILL_AND_OUTLINE}
              pixelOffset={new Cesium.Cartesian2(0, -22)}
              scale={isRiskMode ? 1.05 : 0.9}
            />
          </Entity>

          {/* SAT-A Satellite Entity */}
          <Entity
            id="SAT-A"
            position={positionPropA}
            onClick={() => setSelectedSat('SAT-A')}
          >
            <PointGraphics
              pixelSize={selectedSat === 'SAT-A' ? 14 : 10}
              color={Cesium.Color.fromCssColorString('#3b82f6')}
              outlineColor={selectedSat === 'SAT-A' ? Cesium.Color.WHITE : Cesium.Color.fromCssColorString('#93c5fd')}
              outlineWidth={selectedSat === 'SAT-A' ? 2 : 1}
            />
            <LabelGraphics
              text="SAT-A\n550 KM"
              font="10px monospace"
              fillColor={Cesium.Color.fromCssColorString('#93c5fd')}
              outlineColor={Cesium.Color.fromCssColorString('#070b12')}
              outlineWidth={3}
              style={Cesium.LabelStyle.FILL_AND_OUTLINE}
              pixelOffset={new Cesium.Cartesian2(0, -20)}
            />
          </Entity>

          {/* SAT-B Satellite Entity */}
          <Entity
            id="SAT-B"
            position={positionPropB}
            onClick={() => setSelectedSat('SAT-B')}
          >
            <PointGraphics
              pixelSize={selectedSat === 'SAT-B' ? 14 : 10}
              color={Cesium.Color.fromCssColorString('#ef4444')}
              outlineColor={selectedSat === 'SAT-B' ? Cesium.Color.WHITE : Cesium.Color.fromCssColorString('#fca5a5')}
              outlineWidth={selectedSat === 'SAT-B' ? 2 : 1}
            />
            <LabelGraphics
              text="SAT-B\n548 KM"
              font="10px monospace"
              fillColor={Cesium.Color.fromCssColorString('#fca5a5')}
              outlineColor={Cesium.Color.fromCssColorString('#070b12')}
              outlineWidth={3}
              style={Cesium.LabelStyle.FILL_AND_OUTLINE}
              pixelOffset={new Cesium.Cartesian2(0, -20)}
            />
          </Entity>
        </Viewer>

        {/* View Mode Switcher (Top Right Overlay) */}
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-[#0a0e17]/90 p-1 border border-border/80">
          <button
            onClick={() => setViewMode('ORBIT')}
            className={`px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.14em] transition ${
              viewMode === 'ORBIT'
                ? 'bg-accent text-white font-semibold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            ORBIT
          </button>
          <button
            onClick={() => setViewMode('RISK')}
            className={`px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.14em] transition ${
              viewMode === 'RISK'
                ? 'bg-danger text-white font-semibold shadow-[0_0_8px_rgba(239,68,68,0.5)]'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            RISK
          </button>
        </div>

        {/* Selected Satellite Telemetry Overlay Panel (Top Left) */}
        {selectedSat && (
          <div className="absolute top-3 left-3 z-10 w-52 border border-border/90 bg-[#0a0e17]/95 p-3 backdrop-blur-sm shadow-lg">
            <div className="flex items-center justify-between border-b border-border/60 pb-1.5 font-mono text-[9px] uppercase tracking-[0.18em]">
              <span className="font-bold text-accent-light">{selectedSat}</span>
              <span
                className={`text-[8px] font-semibold px-1 py-0.5 ${
                  selectedSat === 'SAT-A'
                    ? 'bg-accent/20 text-accent-light'
                    : 'bg-danger/20 text-danger-light'
                }`}
              >
                {selectedSat === 'SAT-A' ? 'TRACKED' : 'CONJUNCTION RISK'}
              </span>
            </div>
            <div className="mt-2 space-y-1 font-mono text-[8.5px] uppercase tracking-[0.12em] text-text-muted">
              <div className="flex justify-between">
                <span>ALTITUDE</span>
                <span className="text-text-primary">{selectedSat === 'SAT-A' ? '550 KM' : '548 KM'}</span>
              </div>
              <div className="flex justify-between">
                <span>VELOCITY</span>
                <span className="text-text-primary">7.6 KM/S</span>
              </div>
              <div className="flex justify-between">
                <span>STATUS</span>
                <span className={selectedSat === 'SAT-A' ? 'text-accent' : 'text-danger'}>
                  {selectedSat === 'SAT-A' ? 'NOMINAL TRACK' : 'CONJUNCTION ALERT'}
                </span>
              </div>
              <div className="flex justify-between border-t border-border/50 pt-1 text-text-muted">
                <span>RANGE TO TARGET</span>
                <span className={`font-semibold ${currentMissDistance < 5 ? 'text-danger' : 'text-accent'}`}>
                  {currentMissDistance} KM
                </span>
              </div>
            </div>
            <div className="mt-2.5 flex gap-1.5">
              <button
                onClick={handleTrackSatellite}
                className="w-full bg-border-light/40 hover:bg-accent hover:text-white px-2 py-1 font-mono text-[8px] uppercase tracking-[0.16em] text-text-primary transition"
              >
                TRACK SATELLITE
              </button>
            </div>
          </div>
        )}

        {/* Active Conjunction Indicator Badge (Center-Right Floating) */}
        <div className="pointer-events-none absolute bottom-12 right-3 z-10 flex items-center gap-2 border border-danger/40 bg-[#0a0e17]/90 px-2.5 py-1.5 font-mono text-[8.5px] uppercase tracking-[0.16em] text-danger-light">
          <span className="h-1.5 w-1.5 rounded-full bg-danger animate-ping" />
          <span>EST. MISS DISTANCE: <strong className="text-danger font-bold">{currentMissDistance} KM</strong></span>
        </div>
      </div>

      {/* Bottom Minimal Control Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/80 bg-[#0a0e17] px-3 py-2 font-mono text-[9px] tracking-[0.14em]">
        {/* Play/Pause & Speed */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1.5 border border-border px-2.5 py-1 text-text-primary hover:border-accent hover:text-accent transition uppercase"
          >
            {isPlaying ? (
              <>
                <span className="inline-block h-1.5 w-1.5 bg-accent" />
                PAUSE
              </>
            ) : (
              <>
                <span className="inline-block h-1.5 w-1.5 bg-success" />
                PLAY
              </>
            )}
          </button>

          <button
            onClick={handleLive}
            className="border border-border/70 px-2 py-1 text-text-muted hover:text-text-primary hover:border-border transition uppercase"
          >
            LIVE
          </button>
          <button
            onClick={() => handleAddHours(1)}
            className="border border-border/70 px-2 py-1 text-text-muted hover:text-text-primary hover:border-border transition uppercase"
          >
            +1H
          </button>
          <button
            onClick={() => handleAddHours(6)}
            className="border border-border/70 px-2 py-1 text-text-muted hover:text-text-primary hover:border-border transition uppercase"
          >
            +6H
          </button>
        </div>

        {/* Target Switcher */}
        <div className="flex items-center gap-1.5 text-text-muted">
          <span className="text-[8px] uppercase">TARGET:</span>
          <button
            onClick={() => setSelectedSat('SAT-A')}
            className={`px-1.5 py-0.5 border ${
              selectedSat === 'SAT-A'
                ? 'border-accent bg-accent/20 text-accent-light'
                : 'border-border/60 hover:text-text-primary'
            }`}
          >
            SAT-A
          </button>
          <button
            onClick={() => setSelectedSat('SAT-B')}
            className={`px-1.5 py-0.5 border ${
              selectedSat === 'SAT-B'
                ? 'border-danger bg-danger/20 text-danger-light'
                : 'border-border/60 hover:text-text-primary'
            }`}
          >
            SAT-B
          </button>
          <button
            onClick={handleTrackSatellite}
            className="ml-1 border border-accent/60 bg-accent/10 hover:bg-accent hover:text-white px-2 py-0.5 text-accent-light transition"
          >
            TRACK
          </button>
        </div>
      </div>
    </div>
  );
}

export default OrbitalSituation;
