import { useState } from 'react';
import { Link } from 'react-router-dom';

import { MOCK_TRACKED_OBJECTS } from '../components/globe/mockTrackedObjects';
import type { ConjunctionStatus, TrackedObject } from '../components/globe/types';
import { NegotiationConsole } from '../components/negotiation/NegotiationConsole';
import { ResolutionCard } from '../components/negotiation/ResolutionCard';
import { buildNegotiationWsUrl, useAegisSocket } from '../lib/websocket';
import { useNegotiationStore } from '../store/useNegotiationStore';

const EARTH_RADIUS_KM = 6371;

const STATUS_STYLE: Record<ConjunctionStatus, string> = {
  alerted: 'border-danger/40 bg-danger-muted/40 text-danger-light',
  negotiating: 'border-warning/40 bg-warning-muted/40 text-warning-light',
  resolved: 'border-success/40 bg-success-muted/40 text-success-light',
  escalated: 'border-danger/40 bg-danger-muted/40 text-danger-light',
  stood_down: 'border-success/40 bg-success-muted/40 text-success-light',
};

function magnitude(vector: readonly [number, number, number]): number {
  return Math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2);
}

function altitudeKm(object: TrackedObject): number {
  return magnitude(object.position_km) - EARTH_RADIUS_KM;
}

function formatFullUtc(timestamp: string): string {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toISOString().replace('.000', '');
}

function ObjectPane({ role, object }: { role: 'PRIMARY' | 'SECONDARY'; object: TrackedObject | undefined }) {
  const tone = role === 'PRIMARY' ? 'text-accent-light' : 'text-success-light';

  return (
    <article className="min-w-0 border-b border-border p-5 last:border-b-0 sm:p-6 lg:border-b-0 lg:border-r lg:last:border-r-0">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className={`font-mono text-[9px] font-semibold uppercase tracking-[0.18em] ${tone}`}>{role} OBJECT</p>
          <h2 className="mt-2 truncate text-xl font-semibold tracking-tight text-text-primary">{object?.name ?? 'Unknown object'}</h2>
        </div>
        <span className="border border-border px-2 py-1 font-mono text-[9px] text-text-muted">
          NORAD {object?.norad_id ?? '—'}
        </span>
      </header>

      <dl className="mt-6 grid grid-cols-2 gap-px bg-border">
        <div className="bg-surface-muted p-3">
          <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Altitude</dt>
          <dd className="mt-1.5 font-mono text-sm tabular-nums text-text-primary">
            {object ? `${altitudeKm(object).toFixed(1)} km` : '—'}
          </dd>
        </div>
        <div className="bg-surface-muted p-3">
          <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Velocity</dt>
          <dd className="mt-1.5 font-mono text-sm tabular-nums text-text-primary">
            {object ? `${magnitude(object.velocity_kmps).toFixed(3)} km/s` : '—'}
          </dd>
        </div>
        <div className="bg-surface-muted p-3">
          <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Operator profile</dt>
          <dd className="mt-1.5 font-mono text-[10px] uppercase text-text-muted">not transmitted</dd>
        </div>
        <div className="bg-surface-muted p-3">
          <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Maneuverability</dt>
          <dd className="mt-1.5 font-mono text-[10px] uppercase text-text-muted">not transmitted</dd>
        </div>
      </dl>
    </article>
  );
}

export default function Negotiate() {
  const activeConjunctionAlert = useNegotiationStore((state) => state.activeConjunctionAlert);
  const liveTrackedObjects = useNegotiationStore((state) => state.trackedObjects);
  const messages = useNegotiationStore((state) => state.messages);
  const resolution = useNegotiationStore((state) => state.resolution);
  const connectionStatus = useNegotiationStore((state) => state.connectionStatus);
  const trackedObjects = liveTrackedObjects.length > 0 ? liveTrackedObjects : MOCK_TRACKED_OBJECTS;
  const [negotiationStarted, setNegotiationStarted] = useState(false);

  const negotiationUrl = activeConjunctionAlert
    ? buildNegotiationWsUrl(activeConjunctionAlert.id)
    : undefined;

  useAegisSocket({
    url: negotiationUrl,
    enabled: negotiationStarted && !!negotiationUrl,
    updateStore: true,
  });

  if (!activeConjunctionAlert) {
    return (
      <main className="ops-grid min-h-[calc(100vh-4rem)] px-6 py-10 sm:px-8">
        <div className="mx-auto max-w-[1440px] border border-border bg-surface-muted/75">
          <div className="grid min-h-72 place-items-center p-8 text-center">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-warning-light">Queue empty / monitor active</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">No conjunction selected</h1>
              <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-text-secondary">
                The negotiation desk remains armed until the monitor publishes a conjunction alert.
              </p>
              <Link
                to="/monitor"
                className="mt-7 inline-block border border-border-light px-4 py-2.5 font-mono text-xs uppercase tracking-wider text-text-primary transition hover:border-accent hover:text-accent-light focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Return to monitor
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  const primaryObject = trackedObjects.find((object) => object.norad_id === activeConjunctionAlert.primary_id);
  const secondaryObject = trackedObjects.find((object) => object.norad_id === activeConjunctionAlert.secondary_id);
  const sourceLabel = liveTrackedObjects.length > 0 ? 'LIVE WS' : 'CACHED FALLBACK';
  const negotiationState = resolution
    ? 'RESOLVED'
    : messages.length > 0
      ? 'PROCESSING'
      : negotiationStarted
        ? 'CONNECTED'
        : 'ARMED';

  return (
    <main className="ops-grid min-h-[calc(100vh-4rem)] bg-background px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1440px]">
        <header className="grid gap-5 border-b border-border pb-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">
              <span>incident / {activeConjunctionAlert.id.slice(0, 8)}</span>
              <span aria-hidden="true" className="h-px w-6 bg-border-light" />
              <span>source / {sourceLabel}</span>
              <span aria-hidden="true" className="h-px w-6 bg-border-light" />
              <span>transport / {connectionStatus}</span>
            </div>
            <h1 className="mt-3 text-3xl font-semibold uppercase tracking-[-0.025em] text-text-primary sm:text-4xl">
              Conjunction resolution desk
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className={`border px-2.5 py-1.5 font-mono text-[9px] font-semibold uppercase tracking-wider ${STATUS_STYLE[activeConjunctionAlert.status]}`}>
              {activeConjunctionAlert.status.replace('_', ' ')}
            </span>
            <span className="border border-border bg-surface-muted px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-wider text-text-secondary">
              state / {negotiationState}
            </span>
          </div>
        </header>

        <section className="mt-5 grid border border-border bg-surface-muted/80 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_18rem]" aria-label="Conjunction object and risk data">
          <ObjectPane role="PRIMARY" object={primaryObject} />
          <ObjectPane role="SECONDARY" object={secondaryObject} />

          <aside className="bg-surface/55 p-5 sm:p-6">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-danger-light">Risk geometry</p>
            <dl className="mt-5 divide-y divide-border">
              <div className="py-3 first:pt-0">
                <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Predicted miss</dt>
                <dd className="mt-1 font-mono text-2xl font-semibold tabular-nums text-danger-light">
                  {activeConjunctionAlert.miss_distance_km.toFixed(3)} <span className="text-xs font-normal">km</span>
                </dd>
              </div>
              <div className="py-3">
                <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Relative velocity</dt>
                <dd className="mt-1 font-mono text-sm tabular-nums text-text-primary">
                  {activeConjunctionAlert.relative_velocity_kmps.toFixed(3)} km/s
                </dd>
              </div>
              <div className="py-3 last:pb-0">
                <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">Time of closest approach</dt>
                <dd className="mt-1 break-words font-mono text-[10px] leading-5 text-text-secondary">
                  {formatFullUtc(activeConjunctionAlert.tca_utc)}
                </dd>
              </div>
            </dl>
          </aside>
        </section>

        <section className="mt-3 grid border border-border bg-surface/65 md:grid-cols-[minmax(0,1fr)_auto] md:items-center" aria-label="Negotiation control">
          <div className="border-b border-border px-4 py-3 md:border-b-0 md:border-r sm:px-5">
            <div className="flex items-center gap-3">
              <span className={`h-1.5 w-1.5 ${negotiationStarted ? 'bg-success shadow-[0_0_7px_var(--color-success)]' : 'bg-warning'}`} />
              <p className="font-mono text-[10px] uppercase tracking-wider text-text-primary">
                {negotiationStarted ? 'Negotiation channel open' : 'Negotiation channel armed'}
              </p>
            </div>
            <p className="mt-1 truncate font-mono text-[9px] text-text-muted">
              {negotiationStarted ? `/ws/negotiation/${activeConjunctionAlert.id}` : 'Operator agents idle — explicit trigger required'}
            </p>
          </div>
          <button
            type="button"
            disabled={negotiationStarted}
            onClick={() => setNegotiationStarted(true)}
            className="h-full min-h-14 bg-accent px-6 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-white transition duration-200 hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-tertiary disabled:text-text-muted"
          >
            {negotiationStarted ? 'Session in progress' : 'Execute negotiation →'}
          </button>
        </section>

        <NegotiationConsole messages={messages} />
        <ResolutionCard resolution={resolution} />
      </div>
    </main>
  );
}
