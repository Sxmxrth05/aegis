import { useState } from 'react';

import { Badge } from '../components/shared/Badge';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { MOCK_TRACKED_OBJECTS } from '../components/globe/mockTrackedObjects';
import type { ConjunctionStatus, TrackedObject } from '../components/globe/types';
import { buildNegotiationWsUrl, useAegisSocket } from '../lib/websocket';
import { useNegotiationStore, type WebSocketEnvelope } from '../store/useNegotiationStore';

const EARTH_RADIUS_KM = 6371;

function magnitude(vec: readonly [number, number, number]): number {
  return Math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2);
}

function altitudeKm(obj: TrackedObject): number {
  return magnitude(obj.position_km) - EARTH_RADIUS_KM;
}

const STATUS_BADGE: Record<ConjunctionStatus, 'active' | 'danger' | 'warning' | 'success'> = {
  alerted: 'danger',
  negotiating: 'warning',
  resolved: 'success',
  escalated: 'danger',
  stood_down: 'success',
};

function SatelliteCard({ label, obj }: { label: string; obj: TrackedObject | undefined }) {
  return (
    <Card className="flex-1">
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <h3 className="mt-1 text-lg font-semibold text-text-primary">{obj?.name ?? 'Unknown object'}</h3>
      <p className="text-xs font-mono text-text-muted">NORAD {obj?.norad_id ?? '—'}</p>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <dt className="text-text-secondary">Altitude</dt>
        <dd className="text-right font-mono text-text-primary">
          {obj ? `${altitudeKm(obj).toFixed(1)} km` : '—'}
        </dd>

        <dt className="text-text-secondary">Velocity</dt>
        <dd className="text-right font-mono text-text-primary">
          {obj ? `${magnitude(obj.velocity_kmps).toFixed(3)} km/s` : '—'}
        </dd>

        <dt className="text-text-secondary">Operator</dt>
        <dd className="text-right font-mono text-text-muted">TBD</dd>

        <dt className="text-text-secondary">Fuel Δv margin</dt>
        <dd className="text-right font-mono text-text-muted">TBD</dd>

        <dt className="text-text-secondary">Mission priority</dt>
        <dd className="text-right font-mono text-text-muted">TBD</dd>

        <dt className="text-text-secondary">Maneuverability</dt>
        <dd className="text-right font-mono text-text-muted">TBD</dd>
      </dl>
      <p className="mt-3 text-[11px] text-text-muted">
        Operator/fuel/priority/maneuverability aren't part of the current TrackedObject/ConjunctionAlert
        data the frontend receives — shown as TBD rather than invented.
      </p>
    </Card>
  );
}

export default function Negotiate() {
  const activeConjunctionAlert = useNegotiationStore((s) => s.activeConjunctionAlert);
  const liveTrackedObjects = useNegotiationStore((s) => s.trackedObjects);
  const trackedObjects = liveTrackedObjects.length > 0 ? liveTrackedObjects : MOCK_TRACKED_OBJECTS;

  const [negotiationStarted, setNegotiationStarted] = useState(false);
  const [messageCount, setMessageCount] = useState(0);

  const negotiationUrl = activeConjunctionAlert
    ? buildNegotiationWsUrl(activeConjunctionAlert.id)
    : undefined;

  // Page-local connection, not the app-wide /ws/monitor one — updateStore
  // is false so this never touches the global store or NavBar's status
  // pill. Per this task's scope: just prove the trigger works and data
  // flows, so every message is logged to console, not rendered as a
  // transcript yet (that's the Negotiation Console, a separate task).
  useAegisSocket({
    url: negotiationUrl,
    enabled: negotiationStarted && !!negotiationUrl,
    updateStore: false,
    onEnvelope: (envelope: WebSocketEnvelope) => {
      console.log('[negotiation]', envelope.type, envelope);
      setMessageCount((count) => count + 1);
    },
  });

  if (!activeConjunctionAlert) {
    return (
      <div className="max-w-[1440px] mx-auto px-8 py-8">
        <h2 className="text-2xl font-semibold text-text-primary">Conjunction Details</h2>
        <Card className="mt-6">
          <p className="text-sm text-text-secondary">
            No active conjunction alert right now — visit{' '}
            <span className="text-text-primary">Monitor</span> and wait for the live feed to detect
            one.
          </p>
        </Card>
      </div>
    );
  }

  const primaryObj = trackedObjects.find((o) => o.norad_id === activeConjunctionAlert.primary_id);
  const secondaryObj = trackedObjects.find((o) => o.norad_id === activeConjunctionAlert.secondary_id);
  const usingLiveObjects = liveTrackedObjects.length > 0;

  return (
    <div className="max-w-[1440px] mx-auto px-8 py-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-text-primary">Conjunction Details</h2>
        <Badge status={STATUS_BADGE[activeConjunctionAlert.status]}>
          {activeConjunctionAlert.status.replace('_', ' ')}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-text-muted">
        Satellite positions: {usingLiveObjects ? 'live WebSocket feed' : 'mock data (live tracking not yet available)'}
      </p>

      <div className="mt-6 flex flex-col gap-4 md:flex-row">
        <SatelliteCard label="Primary" obj={primaryObj} />
        <SatelliteCard label="Secondary" obj={secondaryObj} />
      </div>

      <Card className="mt-4">
        <p className="text-xs uppercase tracking-wide text-text-muted">Conjunction Assessment</p>
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-4">
          <dt className="text-text-secondary">Time of closest approach</dt>
          <dd className="font-mono text-text-primary">{activeConjunctionAlert.tca_utc}</dd>

          <dt className="text-text-secondary">Minimum distance</dt>
          <dd className="font-mono text-text-primary">
            {activeConjunctionAlert.miss_distance_km.toFixed(3)} km
          </dd>

          <dt className="text-text-secondary">Relative velocity</dt>
          <dd className="font-mono text-text-primary">
            {activeConjunctionAlert.relative_velocity_kmps.toFixed(3)} km/s
          </dd>

          <dt className="text-text-secondary">Collision probability</dt>
          <dd className="font-mono text-text-muted">TBD</dd>
        </dl>
      </Card>

      <Card className="mt-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-text-primary">Agent Negotiation</p>
            <p className="mt-1 text-xs text-text-muted">
              {negotiationStarted
                ? `Connected to /ws/negotiation/${activeConjunctionAlert.id} — ${messageCount} message(s) received (see console).`
                : 'Not started. Opens a live WebSocket to the negotiation engine.'}
            </p>
          </div>
          <Button
            variant={negotiationStarted ? 'secondary' : 'primary'}
            disabled={negotiationStarted}
            onClick={() => setNegotiationStarted(true)}
          >
            {negotiationStarted ? 'Negotiation running…' : 'Start Agent Negotiation'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
