import { Link } from 'react-router-dom';

import type { Resolution } from '../globe/types';

export function ResolutionCard({ resolution }: { resolution: Resolution | null }) {
  if (!resolution) return null;

  const isSuccess = resolution.status.startsWith('approved');
  const tone = isSuccess
    ? 'border-success/40 bg-success-muted/20 text-success-light'
    : 'border-danger/40 bg-danger-muted/20 text-danger-light';

  return (
    <section className={`mt-5 border ${tone}`} aria-labelledby="resolution-title">
      <header className="grid gap-4 border-b border-current/20 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.2em] opacity-80">Final decision record</p>
          <h3 id="resolution-title" className="mt-1 text-xl font-semibold tracking-tight text-text-primary">
            {resolution.status === 'no_safe_maneuver_found' ? 'No safe maneuver found' : 'Maneuver plan approved'}
          </h3>
        </div>
        <span className="w-fit border border-current/35 px-2.5 py-1.5 font-mono text-[9px] font-semibold uppercase tracking-wider">
          {resolution.status.replace(/_/g, ' ')}
        </span>
      </header>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_2fr]">
        <div className="border-b border-current/20 p-5 lg:border-b-0 lg:border-r">
          <p className="font-mono text-[8px] uppercase tracking-wider opacity-70">Resolution rationale</p>
          <p className="mt-3 max-w-[60ch] text-sm leading-6 text-text-secondary">{resolution.rationale_text}</p>
          {isSuccess && (
            <Link
              to={`/negotiate/${resolution.conjunction_id}/trajectory`}
              className="mt-6 inline-flex border-b border-current pb-1 font-mono text-[10px] font-semibold uppercase tracking-wider transition-opacity hover:opacity-70 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            >
              Inspect trajectory →
            </Link>
          )}
        </div>

        {isSuccess && (
          <dl className="grid grid-cols-2 gap-px bg-current/20 sm:grid-cols-3">
            {[
              ['Maneuvering agent', resolution.maneuvering_agent],
              ['Maneuver type', resolution.maneuver_type],
              ['Delta-V', `${resolution.delta_v_mps.toFixed(3)} m/s`],
              ['Expected miss', `${resolution.expected_min_distance_km.toFixed(3)} km`],
              ['Residual risk', `${(resolution.residual_risk * 100).toExponential(2)}%`],
              ['Execution UTC', resolution.execution_time_utc],
            ].map(([label, value]) => (
              <div key={label} className="min-w-0 bg-surface-muted p-4">
                <dt className="font-mono text-[8px] uppercase tracking-wider text-text-muted">{label}</dt>
                <dd className="mt-2 break-words font-mono text-xs font-medium tabular-nums text-text-primary">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}
