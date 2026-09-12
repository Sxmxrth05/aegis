import { Link } from 'react-router-dom';
import { Badge } from '../shared/Badge';
import { Card } from '../shared/Card';
import { Button } from '../shared/Button';
import type { Resolution } from '../globe/types';

export function ResolutionCard({ resolution }: { resolution: Resolution | null }) {
  if (!resolution) return null;

  const isSuccess = resolution.status.startsWith('approved');
  const badgeStatus = isSuccess ? 'success' : 'danger';

  return (
    <Card className={`mt-6 border-2 ${isSuccess ? 'border-success-muted' : 'border-danger-muted'}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">Final Resolution</p>
          <h3 className="mt-1 text-xl font-bold text-text-primary">
            {resolution.status === 'no_safe_maneuver_found' 
              ? 'No Safe Maneuver Found' 
              : 'Maneuver Plan Approved'}
          </h3>
        </div>
        <Badge status={badgeStatus}>{resolution.status.replace(/_/g, ' ')}</Badge>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-text-secondary">
        {resolution.rationale_text}
      </p>

      {isSuccess && (
        <div className="mt-4">
          <Link to={`/negotiate/${resolution.conjunction_id}/trajectory`}>
            <Button variant="secondary" className="px-3 py-1.5 text-xs">View Trajectory Simulation</Button>
          </Link>
        </div>
      )}

      {isSuccess && (
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs text-text-muted">Maneuvering Agent</dt>
            <dd className="font-mono text-sm font-semibold text-text-primary">{resolution.maneuvering_agent}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Type</dt>
            <dd className="font-mono text-sm text-text-primary">{resolution.maneuver_type}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Delta-V</dt>
            <dd className="font-mono text-sm font-semibold text-text-primary">{resolution.delta_v_mps.toFixed(3)} m/s</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Residual Risk</dt>
            <dd className="font-mono text-sm text-text-primary">{(resolution.residual_risk * 100).toExponential(2)}%</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Expected Miss Distance</dt>
            <dd className="col-span-2 font-mono text-sm text-text-primary">{resolution.expected_min_distance_km.toFixed(3)} km</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Execution Time</dt>
            <dd className="col-span-2 font-mono text-sm text-text-primary">{resolution.execution_time_utc}</dd>
          </div>
        </div>
      )}
    </Card>
  );
}

