import { Card } from '../components/shared/Card';
import { Globe } from '../components/globe/Globe';
import { MOCK_TRACKED_OBJECTS } from '../components/globe/mockTrackedObjects';

const activeCount = MOCK_TRACKED_OBJECTS.length;

export default function Monitor() {
  return (
    <div className="relative h-[calc(100vh-4rem)] w-full">
      <Globe trackedObjects={MOCK_TRACKED_OBJECTS} mode="live" />

      <Card className="absolute left-8 top-8 w-64 p-4">
        <h2 className="text-sm font-semibold text-text-primary">Live Orbital View</h2>
        <p className="mt-1 text-xs text-text-muted">
          Globe component placeholder data — Workstream D4 mock objects.
        </p>

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
            <span className="font-mono text-text-primary">0</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
