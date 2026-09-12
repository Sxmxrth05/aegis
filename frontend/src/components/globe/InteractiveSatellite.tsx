import { animate, stagger } from 'animejs';
import { useCallback, useEffect, useRef, useState } from 'react';
import satACubeSat from '../../assets/satellite-cubesat.png';
import satBOrbiter from '../../assets/satellite-orbiter.png';

export type SatId = 'SAT-A' | 'SAT-B';
export type ScanMode = 'TELEMETRY' | 'SCAN' | 'CONJUNCTION';

interface Hotspot {
  id: string;
  name: string;
  subsystem: string;
  detail: string;
  metric: string;
  x: number; // percentage
  y: number; // percentage
}

const HOTSPOTS_SAT_A: Hotspot[] = [
  {
    id: 'optics',
    name: 'OPTICAL APERTURE // STAR TRACKER',
    subsystem: 'Attitude Determination',
    detail: 'Autonomous celestial navigation sensor for sub-arcsecond orbital positioning.',
    metric: 'FOV: 18.4° // TRACKING',
    x: 48,
    y: 62,
  },
  {
    id: 'solar',
    name: 'TRIPLE-JUNCTION GAAS ARRAY',
    subsystem: 'Power Generation',
    detail: 'Deployable ultra-light solar wings providing continuous operational power.',
    metric: 'OUTPUT: 128W // 28.4V',
    x: 77,
    y: 22,
  },
  {
    id: 'thruster',
    name: 'MICRO-PROPULSION CLUSTER',
    subsystem: 'Orbit Control',
    detail: 'Cold-gas micro-thrusters reserved for collision-avoidance delta-v burns.',
    metric: 'RESERVE: 42.6 M/S Δv',
    x: 52,
    y: 84,
  },
  {
    id: 'comm',
    name: 'INTER-OPERATOR DATA BUS',
    subsystem: 'Communications',
    detail: 'S-band secure transponder for peer-to-peer Aegis coordination proposals.',
    metric: 'FREQ: 2.2 GHZ // SYNCED',
    x: 27,
    y: 44,
  },
];

const HOTSPOTS_SAT_B: Hotspot[] = [
  {
    id: 'dish',
    name: 'STEERABLE S-BAND DISH',
    subsystem: 'Ground Communications',
    detail: 'High-gain tracking antenna for operator downlink and telemetry monitoring.',
    metric: 'GAIN: 24 DBI // ACTIVE',
    x: 62,
    y: 62,
  },
  {
    id: 'sensor',
    name: 'ATMOSPHERIC SOUNDER',
    subsystem: 'Primary Mission Payload',
    detail: 'Continuous multispectral Earth atmospheric and ocean monitoring.',
    metric: 'BAND: 12 CHANNELS // NOMINAL',
    x: 64,
    y: 32,
  },
  {
    id: 'wing',
    name: 'SOLAR GENERATOR ARRAY',
    subsystem: 'Power Architecture',
    detail: 'Dual articulated photovoltaic panels with sun-tracking drive.',
    metric: 'OUTPUT: 340W // 32.0V',
    x: 38,
    y: 45,
  },
  {
    id: 'engine',
    name: 'HYDRAZINE ORBIT ENGINE',
    subsystem: 'Maneuver Actuation',
    detail: 'Main propulsion engine for orbital station-keeping and emergency avoidance.',
    metric: 'RESERVE: 88.2 M/S Δv',
    x: 82,
    y: 66,
  },
];

export function InteractiveSatellite() {
  const containerRef = useRef<HTMLDivElement>(null);
  const satelliteImgRef = useRef<HTMLImageElement>(null);
  const scanBeamRef = useRef<HTMLDivElement>(null);
  const hotspotsContainerRef = useRef<HTMLDivElement>(null);

  const [activeSat, setActiveSat] = useState<SatId>('SAT-A');
  const [activeMode, setActiveMode] = useState<ScanMode>('TELEMETRY');
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(HOTSPOTS_SAT_A[0]);
  const [hoveredHotspot, setHoveredHotspot] = useState<Hotspot | null>(null);
  const [mousePos, setMousePos] = useState({ relX: 0.5, relY: 0.5, x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  const [utcTime, setUtcTime] = useState('');

  // Live UTC time string
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Anime.js: Zero-G Orbital Floating Motion
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const imgEl = satelliteImgRef.current;
    if (!imgEl) return;

    const anim = animate(imgEl, {
      translateY: [-6, 6],
      rotateZ: [-0.8, 0.8],
      duration: 4500,
      alternate: true,
      loop: true,
      easing: 'easeInOutSine',
    });

    return () => {
      anim.pause();
    };
  }, [activeSat]);

  // Anime.js: Hotspot Points Stagger Entrance when switching satellites
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const container = hotspotsContainerRef.current;
    if (!container) return;

    const spots = Array.from(container.querySelectorAll('.satellite-hotspot'));
    animate(spots, {
      scale: [0, 1],
      opacity: [0, 1],
      delay: stagger(75),
      duration: 450,
      easing: 'easeOutBack',
    });
  }, [activeSat]);

  // Hotspots for current satellite
  const currentHotspots = activeSat === 'SAT-A' ? HOTSPOTS_SAT_A : HOTSPOTS_SAT_B;

  // Active satellite image
  const currentImage = activeSat === 'SAT-A' ? satACubeSat : satBOrbiter;

  // Switch satellite
  const handleSelectSat = (satId: SatId) => {
    setActiveSat(satId);
    setSelectedHotspot(satId === 'SAT-A' ? HOTSPOTS_SAT_A[0] : HOTSPOTS_SAT_B[0]);
  };

  // Interactive 3D Perspective Tilt on Mouse Move
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const relX = Math.max(0, Math.min(1, x / rect.width));
    const relY = Math.max(0, Math.min(1, y / rect.height));
    setMousePos({ relX, relY, x, y });
  }, []);

  // Calculate subtle rotation angles
  const rotX = isHovered ? (mousePos.relY - 0.5) * -12 : 0;
  const rotY = isHovered ? (mousePos.relX - 0.5) * 14 : 0;

  // Anime.js: Trigger Active Radar Scan
  const triggerScan = useCallback(() => {
    setActiveMode('SCAN');
    const beam = scanBeamRef.current;
    if (!beam) return;

    animate(beam, {
      translateY: ['-100%', '350%'],
      opacity: [0, 0.85, 0],
      duration: 2200,
      easing: 'linear',
    });
  }, []);

  const displayedHotspot = hoveredHotspot || selectedHotspot;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setHoveredHotspot(null);
      }}
      className="relative w-full overflow-hidden rounded-[3px] border border-border bg-[#070b12] text-text-primary shadow-[0_12px_36px_-8px_rgba(10,14,23,0.95)] select-none"
    >
      {/* ─── Top Instrument Header ───────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/80 bg-[#0a0e17]/95 px-3 py-2 font-mono text-[9px] uppercase tracking-[0.16em]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          <span className="font-semibold text-text-primary">
            SPACECRAFT TELEMETRY // {activeSat === 'SAT-A' ? 'CUBESAT-01' : 'ORBITER-02'}
          </span>
          <span className="hidden sm:inline text-text-muted/60">•</span>
          <span className="hidden sm:inline text-accent-light">
            {activeSat === 'SAT-A' ? 'OPERATOR-ALPHA' : 'OPERATOR-BETA'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-text-muted">
          <span className="hidden md:inline">{utcTime}</span>
          <span className="hidden md:inline text-border">|</span>
          <span className="border border-border/70 px-1.5 py-0.5 text-text-primary">
            ALT 550 KM // 7.6 KM/S
          </span>
        </div>
      </div>

      {/* ─── Interactive Viewport Container ──────────────────── */}
      <div className="relative h-[360px] sm:h-[420px] lg:h-[460px] w-full overflow-hidden bg-gradient-to-b from-[#060910] via-[#090d18] to-[#060910]">
        {/* Dynamic 3D Tilt Wrapper */}
        <div
          className="relative h-full w-full transition-transform duration-200 ease-out"
          style={{
            transform: `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale3d(1.01, 1.01, 1.01)`,
            transformStyle: 'preserve-3d',
          }}
        >
          {/* Deep Space Star Dust Background */}
          <div className="absolute inset-0 pointer-events-none opacity-40">
            <div
              className="h-full w-full"
              style={{
                backgroundImage:
                  'radial-gradient(1px 1px at 15% 25%, #ffffff 0, transparent 100%), radial-gradient(1px 1px at 80% 15%, #93c5fd 0, transparent 100%), radial-gradient(1px 1px at 35% 85%, #60a5fa 0, transparent 100%), radial-gradient(1px 1px at 70% 70%, #ffffff 0, transparent 100%)',
                backgroundSize: '180px 180px',
              }}
            />
          </div>

          {/* Earth Atmosphere Rim Glow */}
          <div
            className="pointer-events-none absolute -bottom-28 -left-10 -right-10 h-48 opacity-70"
            style={{
              background: 'radial-gradient(ellipse at 50% 100%, rgba(59,130,246,0.35) 0%, rgba(30,58,138,0.15) 50%, transparent 75%)',
              filter: 'blur(16px)',
            }}
          />

          {/* Main Spacecraft Image with Zero-G Anime.js Floating Animation */}
          <img
            ref={satelliteImgRef}
            src={currentImage}
            alt={activeSat === 'SAT-A' ? 'SAT-A CubeSat' : 'SAT-B Orbiter'}
            className="absolute inset-0 h-full w-full object-contain p-4 sm:p-6 filter contrast-[1.06] transition-opacity duration-300 pointer-events-none"
            loading="eager"
          />

          {/* Radar / Lidar Scan Beam Animation powered by Anime.js */}
          <div
            ref={scanBeamRef}
            className="pointer-events-none absolute inset-0 overflow-hidden opacity-0"
          >
            <div
              className="h-28 w-full"
              style={{
                background:
                  'linear-gradient(to bottom, transparent, rgba(59, 130, 246, 0.08) 40%, rgba(96, 165, 250, 0.45) 50%, rgba(59, 130, 246, 0.08) 60%, transparent)',
              }}
            />
          </div>

          {/* Conjunction Risk Proximity Field Overlay */}
          {activeMode === 'CONJUNCTION' && (
            <div className="pointer-events-none absolute inset-0">
              <div className="absolute inset-0 border-2 border-danger/40 animate-pulse bg-danger/5" />
              <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-danger/60 animate-ping"
                style={{ width: '220px', height: '220px' }}
              />
            </div>
          )}

          {/* Subsystem Interactive Inspection Hotspots (staggered by Anime.js) */}
          <div ref={hotspotsContainerRef} className="absolute inset-0 pointer-events-auto">
            {currentHotspots.map((spot) => {
              const isSelected = selectedHotspot?.id === spot.id;
              const isHover = hoveredHotspot?.id === spot.id;

              return (
                <div
                  key={spot.id}
                  style={{ left: `${spot.x}%`, top: `${spot.y}%` }}
                  className="satellite-hotspot absolute -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer"
                  onClick={() => setSelectedHotspot(spot)}
                  onMouseEnter={() => setHoveredHotspot(spot)}
                  onMouseLeave={() => setHoveredHotspot(null)}
                >
                  {/* Outer Target Ring */}
                  <div
                    className={`relative flex items-center justify-center rounded-full transition-all duration-300 ${
                      isSelected
                        ? 'h-7 w-7 border-2 border-accent bg-accent/20 shadow-[0_0_14px_rgba(59,130,246,0.9)]'
                        : isHover
                          ? 'h-6 w-6 border border-accent-light bg-accent/15'
                          : 'h-4 w-4 border border-border-light bg-[#0a0e17]/80 hover:border-accent'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full transition-colors ${
                        isSelected ? 'bg-white' : 'bg-accent'
                      }`}
                    />
                  </div>

                  {/* Subsystem Label Tag */}
                  <div
                    className={`pointer-events-none absolute left-full ml-2 top-1/2 -translate-y-1/2 whitespace-nowrap font-mono text-[8px] uppercase tracking-[0.16em] px-1.5 py-0.5 border transition-all duration-200 ${
                      isSelected
                        ? 'border-accent bg-background/90 text-accent-light opacity-100'
                        : isHover
                          ? 'border-border bg-background/80 text-text-primary opacity-100'
                          : 'border-border/40 bg-background/60 text-text-muted opacity-0 sm:opacity-80'
                    }`}
                  >
                    {spot.name.split('//')[0].trim()}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Interactive Mouse Coordinate Reticle */}
          {isHovered && (
            <div
              className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 z-10 transition-transform duration-75"
              style={{ left: mousePos.x, top: mousePos.y }}
            >
              <div className="relative h-6 w-6 border border-accent/30 rounded-full flex items-center justify-center">
                <span className="h-0.5 w-0.5 bg-accent" />
              </div>
            </div>
          )}
        </div>

        {/* ─── Top Left: Selected Subsystem Telemetry Card ─────── */}
        {displayedHotspot && (
          <div className="absolute top-3 left-3 z-30 w-60 border border-border/90 bg-[#0a0e17]/95 p-3 backdrop-blur-md shadow-2xl transition-all">
            <div className="flex items-center justify-between border-b border-border/60 pb-1.5 font-mono text-[8.5px] uppercase tracking-[0.18em]">
              <span className="font-bold text-accent-light">{displayedHotspot.subsystem}</span>
              <span className="border border-accent/40 bg-accent/10 px-1 text-[7.5px] text-accent">
                INSPECT
              </span>
            </div>

            <p className="mt-2 font-mono text-[9px] font-semibold text-text-primary leading-tight">
              {displayedHotspot.name}
            </p>

            <p className="mt-1.5 text-[11px] leading-relaxed text-text-muted">
              {displayedHotspot.detail}
            </p>

            <div className="mt-2.5 border-t border-border/60 pt-1.5 font-mono text-[8.5px] uppercase tracking-[0.14em] text-accent-light flex justify-between items-center">
              <span>TELEMETRY:</span>
              <span className="font-bold text-text-primary">{displayedHotspot.metric}</span>
            </div>
          </div>
        )}

        {/* ─── Top Right: Satellite Selector & Modes ───────────── */}
        <div className="absolute top-3 right-3 z-30 flex flex-col items-end gap-1.5">
          {/* Satellite Switcher */}
          <div className="flex items-center gap-1 border border-border/80 bg-[#0a0e17]/95 p-1 font-mono text-[8.5px] uppercase tracking-[0.16em]">
            <span className="px-1 text-text-muted text-[7.5px]">TARGET:</span>
            <button
              onClick={() => handleSelectSat('SAT-A')}
              className={`px-2 py-1 transition ${
                activeSat === 'SAT-A'
                  ? 'bg-accent text-white font-bold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              SAT-A (CUBESAT)
            </button>
            <button
              onClick={() => handleSelectSat('SAT-B')}
              className={`px-2 py-1 transition ${
                activeSat === 'SAT-B'
                  ? 'bg-danger text-white font-bold shadow-[0_0_8px_rgba(239,68,68,0.4)]'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              SAT-B (ORBITER)
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center gap-1 border border-border/80 bg-[#0a0e17]/95 p-1 font-mono text-[8px] uppercase tracking-[0.14em]">
            <button
              onClick={() => setActiveMode('TELEMETRY')}
              className={`px-2 py-0.5 transition ${
                activeMode === 'TELEMETRY'
                  ? 'bg-border-light text-text-primary font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              TELEMETRY
            </button>
            <button
              onClick={() => {
                setActiveMode('SCAN');
                triggerScan();
              }}
              className={`px-2 py-0.5 transition ${
                activeMode === 'SCAN'
                  ? 'bg-accent text-white font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              SCAN
            </button>
            <button
              onClick={() => setActiveMode('CONJUNCTION')}
              className={`px-2 py-0.5 transition ${
                activeMode === 'CONJUNCTION'
                  ? 'bg-danger text-white font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              RISK MODE
            </button>
          </div>
        </div>

        {/* ─── Center/Bottom Floating Conjunction Alert ────────── */}
        <div
          className={`pointer-events-none absolute bottom-3 right-3 z-30 flex items-center gap-2.5 border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] backdrop-blur-sm transition-all ${
            activeMode === 'CONJUNCTION'
              ? 'border-danger bg-danger/20 text-danger-light shadow-[0_0_12px_rgba(239,68,68,0.5)]'
              : 'border-border/80 bg-[#0a0e17]/90 text-text-muted'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              activeMode === 'CONJUNCTION' ? 'bg-danger animate-ping' : 'bg-warning'
            }`}
          />
          <span>
            {activeSat === 'SAT-A' ? 'CONJUNCTION PROXIMITY:' : 'AVOIDANCE TRAJECTORY:'}{' '}
            <strong className="text-text-primary font-bold">1.2 KM (TCA: 35 MIN)</strong>
          </span>
        </div>
      </div>

      {/* ─── Bottom Technical Control Strip ──────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/80 bg-[#0a0e17] px-3.5 py-2.5 font-mono text-[9px] uppercase tracking-[0.14em]">
        <div className="flex items-center gap-4 text-text-muted">
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted/60">ORBIT:</span>
            <span className="text-text-primary">LEO // 550.0 KM</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted/60">INCLINATION:</span>
            <span className="text-text-primary">51.6°</span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5">
            <span className="text-text-muted/60">VELOCITY:</span>
            <span className="text-text-primary">7.58 KM/S</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={triggerScan}
            className="flex items-center gap-1.5 border border-accent/50 bg-accent/10 px-2.5 py-1 text-accent-light hover:bg-accent hover:text-white transition"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            TRIGGER RADAR SCAN
          </button>
        </div>
      </div>
    </div>
  );
}

export default InteractiveSatellite;
