import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { LayoutGroup, motion, useReducedMotion } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';

import { useNegotiationStore } from '../../store/useNegotiationStore';
import type { BackgroundPoint } from './backgroundSatellites';
import { fetchBackgroundSatellites } from './backgroundSatellites';
import { Globe, type GlobeHandle, type GlobeMode } from './Globe';
import { MOCK_TRACKED_OBJECTS } from './mockTrackedObjects';
import type { ConjunctionAlert, ManeuverTrajectoryResult, TrackedObject } from './types';

// Keep the WebGL surface to one geometry change. A stop in an intermediate
// layout makes the renderer resize twice and reads as a visible snap.
const HERO_EXIT_MS = 180;
const GLOBE_REFIT_MS = 820;
const MONITOR_CHROME_DELAY_MS = 420;

export type GlobeStagePhase = 'hidden' | 'hero' | 'hero-exit' | 'monitor-enter' | 'monitor' | 'trajectory';

type StageRequest = {
  mode: GlobeStagePhase;
  trackedObjects?: TrackedObject[];
  conjunctionAlert?: ConjunctionAlert;
  trajectoryResult?: ManeuverTrajectoryResult;
};

type StageContextValue = {
  setGlobeStage: (request: StageRequest) => void;
  navigateToMonitor: () => void;
  phase: GlobeStagePhase;
  isGlobeInteractive: boolean;
  isMonitorChromeVisible: boolean;
};

const GlobeStageContext = createContext<StageContextValue | null>(null);

const STAGE_CLASS_NAMES: Record<GlobeStagePhase, string> = {
  hidden: 'absolute left-0 top-16 h-px w-px opacity-0',
  hero: 'absolute left-0 top-16 h-[clamp(560px,82vh,860px)] w-screen opacity-100',
  'hero-exit': 'absolute left-0 top-16 h-[clamp(560px,82vh,860px)] w-screen opacity-100',
  'monitor-enter': 'absolute left-0 top-16 h-[calc(100dvh-4rem)] w-screen opacity-100',
  monitor: 'absolute left-0 top-16 h-[calc(100dvh-4rem)] w-screen opacity-100',
  trajectory: 'absolute left-0 top-16 h-[calc(100dvh-4rem)] w-screen opacity-100',
};

const CAMERA_TARGETS: Record<GlobeStagePhase, { lat: number; lng: number; altitude: number }> = {
  hidden: { lat: 20, lng: 10, altitude: 2.8 },
  hero: { lat: 20, lng: 10, altitude: 2.45 },
  'hero-exit': { lat: 20, lng: 10, altitude: 2.45 },
  'monitor-enter': { lat: 20, lng: 10, altitude: 1.42 },
  monitor: { lat: 20, lng: 10, altitude: 1.42 },
  trajectory: { lat: 12, lng: 0, altitude: 1.7 },
};

function routeStage(pathname: string): GlobeStagePhase {
  if (pathname === '/') return 'hero';
  if (pathname === '/monitor') return 'monitor';
  if (pathname.endsWith('/trajectory')) return 'trajectory';
  return 'hidden';
}

function globeMode(mode: GlobeStagePhase, hasAlert: boolean): GlobeMode {
  if (mode === 'hero' || mode === 'hero-exit') return 'landing';
  if (mode === 'monitor-enter') return 'transition';
  if (mode === 'trajectory') return 'trajectory';
  return hasAlert ? 'conjunction' : 'live';
}

// eslint-disable-next-line react-refresh/only-export-components
export function useGlobeStage() {
  const context = useContext(GlobeStageContext);
  if (!context) throw new Error('useGlobeStage must be used inside GlobeStageProvider.');
  return context;
}

export function GlobeStageProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const globeRef = useRef<GlobeHandle>(null);
  const timersRef = useRef<number[]>([]);
  const [stage, setStage] = useState<StageRequest>(() => ({ mode: routeStage(location.pathname) }));
  const [isMonitorChromeVisible, setMonitorChromeVisible] = useState(() => routeStage(location.pathname) === 'monitor');
  const liveTrackedObjects = useNegotiationStore((state) => state.trackedObjects);
  const activeConjunctionAlert = useNegotiationStore((state) => state.activeConjunctionAlert);

  // Background satellite layer — cosmetic density cloud fetched once on mount.
  // Stored here (not in Monitor.tsx) because GlobeStage owns the Globe instance;
  // this also lets the background render on the Landing hero globe too.
  // Falls back silently to a static set if the fetch fails (see backgroundSatellites.ts).
  const [backgroundObjects, setBackgroundObjects] = useState<BackgroundPoint[]>([]);
  useEffect(() => {
    void fetchBackgroundSatellites().then(setBackgroundObjects);
  }, []); // run once on mount — background objects don't need live updates

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }, []);

  const moveCamera = useCallback((mode: GlobeStagePhase, durationMs: number) => {
    window.requestAnimationFrame(() => {
      globeRef.current?.pointOfView(CAMERA_TARGETS[mode], durationMs);
    });
  }, []);

  const setGlobeStage = useCallback((request: StageRequest) => {
    setStage(request);
    setMonitorChromeVisible(request.mode !== 'monitor-enter');
    moveCamera(request.mode, prefersReducedMotion ? 0 : GLOBE_REFIT_MS);
  }, [moveCamera, prefersReducedMotion]);

  const navigateToMonitor = useCallback(() => {
    if (location.pathname !== '/' || stage.mode !== 'hero') {
      navigate('/monitor');
      return;
    }

    clearTimers();
    window.scrollTo({ top: 0, behavior: 'auto' });

    if (prefersReducedMotion) {
      setStage({ mode: 'monitor' });
      setMonitorChromeVisible(true);
      moveCamera('monitor', 0);
      navigate('/monitor');
      return;
    }

    setMonitorChromeVisible(false);
    setStage({ mode: 'hero-exit' });
    timersRef.current.push(window.setTimeout(() => {
      setStage({ mode: 'monitor-enter' });
      moveCamera('monitor-enter', GLOBE_REFIT_MS);
      navigate('/monitor');
    }, HERO_EXIT_MS));
    timersRef.current.push(window.setTimeout(() => {
      setMonitorChromeVisible(true);
    }, HERO_EXIT_MS + MONITOR_CHROME_DELAY_MS));
    timersRef.current.push(window.setTimeout(() => {
      setStage({ mode: 'monitor' });
    }, HERO_EXIT_MS + GLOBE_REFIT_MS));
  }, [clearTimers, location.pathname, moveCamera, navigate, prefersReducedMotion, stage.mode]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  useEffect(() => {
    const destination = routeStage(location.pathname);
    if (destination === 'hidden') {
      clearTimers();
      setGlobeStage({ mode: 'hidden' });
    }
  }, [clearTimers, location.pathname, setGlobeStage]);

  const trackedObjects = stage.trackedObjects
    ?? (liveTrackedObjects.length > 0 ? liveTrackedObjects : MOCK_TRACKED_OBJECTS);
  const conjunctionAlert = stage.conjunctionAlert ?? activeConjunctionAlert ?? undefined;
  const isGlobeInteractive = stage.mode === 'monitor' || stage.mode === 'trajectory';
  const contextValue = useMemo(() => ({
    setGlobeStage,
    navigateToMonitor,
    phase: stage.mode,
    isGlobeInteractive,
    isMonitorChromeVisible,
  }), [isGlobeInteractive, isMonitorChromeVisible, navigateToMonitor, setGlobeStage, stage.mode]);

  const stageClassName = [
    isGlobeInteractive ? 'pointer-events-auto' : 'pointer-events-none',
    'z-0 overflow-hidden',
    STAGE_CLASS_NAMES[stage.mode],
  ].join(' ');

  return (
    <GlobeStageContext.Provider value={contextValue}>
      <div className="relative min-h-screen">
        <LayoutGroup id="aegis-globe-stage">
          <motion.div
            layout
            layoutId="globe-stage"
            aria-hidden={stage.mode === 'hidden'}
            className={stageClassName}
            transition={{
              layout: { duration: prefersReducedMotion ? 0 : GLOBE_REFIT_MS / 1000, ease: [0.22, 1, 0.36, 1] },
              opacity: { duration: prefersReducedMotion ? 0 : 0.18 },
            }}
          >
            <Globe
              ref={globeRef}
              trackedObjects={trackedObjects}
              mode={globeMode(stage.mode, Boolean(conjunctionAlert))}
              conjunctionAlert={conjunctionAlert}
              trajectoryResult={stage.trajectoryResult}
              backgroundObjects={backgroundObjects}
            />
            {stage.mode === 'monitor-enter' && (
              <motion.div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 z-[3] bg-[radial-gradient(ellipse_at_center,transparent_28%,rgba(5,9,17,0.38)_100%)]"
                initial={{ opacity: 0.85 }}
                animate={{ opacity: 0 }}
                transition={{ duration: GLOBE_REFIT_MS / 1000, ease: [0.22, 1, 0.36, 1] }}
              />
            )}
          </motion.div>
        </LayoutGroup>
        {children}
      </div>
    </GlobeStageContext.Provider>
  );
}
