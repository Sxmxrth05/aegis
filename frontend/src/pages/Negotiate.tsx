import { useState } from 'react';

import { NegotiationConsole } from '../components/negotiation/NegotiationConsole';
import { ResolutionCard } from '../components/negotiation/ResolutionCard';

import { Badge } from '../components/shared/Badge';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { MOCK_TRACKED_OBJECTS } from '../components/globe/mockTrackedObjects';
import type { ConjunctionStatus, TrackedObject } from '../components/globe/types';
import { buildNegotiationWsUrl, useAegisSocket } from '../lib/websocket';
import { useNegotiationStore } from '../store/useNegotiationStore';

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

function SatelliteCard({
  label,
  obj,
  profile,
}: {
  label: string;
  obj: TrackedObject | undefined;
  profile: { operator_name: string; fuel_margin_pct: number; mvi: number; delta_v_mps: number } | undefined;
}) {
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
        <dd className="text-right font-mono text-text-primary">
          {profile ? profile.operator_name : '—'}
        </dd>

        <dt className="text-text-secondary">Fuel Δv margin</dt>
        <dd className="text-right font-mono text-text-primary">
          {profile ? `${profile.fuel_margin_pct.toFixed(1)}%` : '—'}
        </dd>

        <dt className="text-text-secondary">Mission priority</dt>
        <dd className="text-right font-mono text-text-primary">
          {profile ? `${(profile.mvi * 100).toFixed(0)}% (MVI ${profile.mvi.toFixed(2)})` : '—'}
        </dd>

        <dt className="text-text-secondary">Maneuverability</dt>
        <dd className="text-right font-mono text-text-primary">
          {profile ? `Max Δv ${profile.delta_v_mps.toFixed(1)} m/s` : '—'}
        </dd>
      </dl>
    </Card>
  );
}

export default function Negotiate() {
  const activeConjunctionAlert = useNegotiationStore((s) => s.activeConjunctionAlert);
  const liveTrackedObjects = useNegotiationStore((s) => s.trackedObjects);
  const operatorProfiles = useNegotiationStore((s) => s.operatorProfiles);
  const messages = useNegotiationStore((s) => s.messages);
  const resolution = useNegotiationStore((s) => s.resolution);
  
  const trackedObjects = liveTrackedObjects.length > 0 ? liveTrackedObjects : MOCK_TRACKED_OBJECTS;

  const [negotiationStarted, setNegotiationStarted] = useState(false);

  const negotiationUrl = activeConjunctionAlert
    ? buildNegotiationWsUrl(activeConjunctionAlert.id)
    : undefined;

  // Page-local connection for the negotiation engine stream. updateStore is
  // now true since the store has been extended to handle negotiation messages
  // and safely merge snapshots without clobbering monitor state.
  useAegisSocket({
    url: negotiationUrl,
    enabled: negotiationStarted && !!negotiationUrl,
    updateStore: true,
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
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Conjunction Details</h2>
          <p className="text-xs text-text-muted mt-0.5">Evaluating Primary vs Secondary satellite encounter pair</p>
        </div>
        <Badge status={STATUS_BADGE[activeConjunctionAlert.status]}>
          {activeConjunctionAlert.status.replace('_', ' ')}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-text-muted">
        Satellite positions: {usingLiveObjects ? 'live WebSocket feed' : 'mock data (live tracking not yet available)'}
      </p>

      <div className="mt-6 flex flex-col gap-4 md:flex-row">
        <SatelliteCard label="Primary" obj={primaryObj} profile={primaryObj ? operatorProfiles[primaryObj.norad_id] : undefined} />
        <SatelliteCard label="Secondary" obj={secondaryObj} profile={secondaryObj ? operatorProfiles[secondaryObj.norad_id] : undefined} />
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
                ? `Connected to /ws/negotiation/${activeConjunctionAlert.id} — rendering transcript.`
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

      <NegotiationConsole messages={messages} />
      <ResolutionCard resolution={resolution} />
    </div>
  );
}

