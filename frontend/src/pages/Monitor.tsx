import { Card } from '../components/shared/Card';
import { Globe } from '../components/globe/Globe';
import { MOCK_TRACKED_OBJECTS } from '../components/globe/mockTrackedObjects';
import { useNegotiationStore } from '../store/useNegotiationStore';

export default function Monitor() {
  const liveTrackedObjects = useNegotiationStore((s) => s.trackedObjects);
  const activeConjunctionAlert = useNegotiationStore((s) => s.activeConjunctionAlert);

  // The backend's /ws/monitor snapshot doesn't carry tracked-object state
  // yet (only conjunctions — see store/useNegotiationStore.ts), so the live
  // array is empty today even when connected. Fall back to the hand-written
  // dev fixture so the globe stays populated; this self-corrects with zero
  // code changes once Dev A/B wire real tracked-object data into the
  // snapshot payload.
  const trackedObjects = liveTrackedObjects.length > 0 ? liveTrackedObjects : MOCK_TRACKED_OBJECTS;
  const usingLiveData = liveTrackedObjects.length > 0;

  const flaggedIds = activeConjunctionAlert
    ? new Set([activeConjunctionAlert.primary_id, activeConjunctionAlert.secondary_id])
    : new Set<string>();
  const hazardCount = trackedObjects.filter((obj) => flaggedIds.has(obj.norad_id)).length;
  const activeCount = trackedObjects.length - hazardCount;

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full">
      <Globe
        trackedObjects={trackedObjects}
        mode={activeConjunctionAlert ? 'conjunction' : 'live'}
        conjunctionAlert={activeConjunctionAlert ?? undefined}
      />

      <Card className="absolute left-8 top-8 w-64 p-4">
        <h2 className="text-sm font-semibold text-text-primary">Live Orbital View</h2>
        <div className="mt-1 space-y-0.5 text-xs text-text-muted">
          <p>
            Satellite positions:{' '}
            {usingLiveData ? 'live WebSocket feed' : 'mock data (live tracking not yet available)'}
          </p>
          <p>
            Conjunction alert:{' '}
            {activeConjunctionAlert ? <span className="text-danger-light">live</span> : 'none active'}
          </p>
        </div>

        <div className="mt-4 space-y-2 text-xs">
          <div className="flex items-center justify-between text-text-secondary">
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_6px_var(--color-accent)]" />
              Active
            </span>
            <span className="font-mono text-text-primary">{activeCount}</span>
          </div>
          <div className="flex items-center justify-between text-text-secondary">
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-danger shadow-[0_0_6px_var(--color-danger)]" />
              Hazard / debris
            </span>
            <span className="font-mono text-text-primary">{hazardCount}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
