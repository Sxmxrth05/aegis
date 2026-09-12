import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '../components/shared/Badge';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';

const STATUS_BADGE: Record<string, 'active' | 'danger' | 'warning' | 'success'> = {
  alerted: 'danger',
  negotiating: 'warning',
  resolved: 'success',
  escalated: 'danger',
  stood_down: 'success',
  approved: 'success',
  approved_no_action: 'success',
  no_safe_maneuver_found: 'danger',
};

type HistoryRow = {
  conjunction_id: string;
  primary_id: string;
  secondary_id: string;
  tca_utc: string;
  initial_miss_distance_km: number;
  relative_velocity_kmps: number;
  conjunction_status: string;
  alert_created_at: string;
  maneuvering_agent: string | null;
  maneuver_type: string | null;
  delta_v_mps: number | null;
  execution_time_utc: string | null;
  post_maneuver_miss_distance_km: number | null;
  resolution_status: string | null;
  rationale_text: string | null;
  message_count: number;
};

export default function History() {
  const [data, setData] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      setError(false);
      try {
        const url = statusFilter ? `/api/history?status=${statusFilter}` : '/api/history';
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error(err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [statusFilter]);

  return (
    <div className="mx-auto max-w-[1440px] px-8 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-text-primary">History</h2>
        <div className="flex items-center gap-3">
           <label htmlFor="status-filter" className="text-sm text-text-secondary">Filter:</label>
           <select 
             id="status-filter"
             className="rounded-md border border-border bg-surface-secondary px-3 py-1.5 text-sm text-text-primary outline-none focus:border-accent"
             value={statusFilter}
             onChange={e => setStatusFilter(e.target.value)}
           >
             <option value="">All</option>
             <option value="resolved">Resolved</option>
             <option value="escalated">Escalated</option>
             <option value="approved">Approved</option>
             <option value="no_safe_maneuver_found">No Safe Maneuver</option>
           </select>
        </div>
      </div>
      
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-text-secondary">
            <thead className="bg-surface-secondary text-xs uppercase tracking-wider text-text-muted">
              <tr>
                <th className="px-6 py-4 font-medium">Objects (Pri / Sec)</th>
                <th className="px-6 py-4 font-medium">TCA (UTC)</th>
                <th className="px-6 py-4 text-right font-medium">Miss Dist (km)</th>
                <th className="px-6 py-4 text-right font-medium">Msg Count</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-muted">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-text-muted">Loading...</td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-danger">Failed to load history data.</td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-text-muted">No history found.</td>
                </tr>
              ) : (
                data.map((row) => {
                  const displayStatus = row.resolution_status || row.conjunction_status;
                  return (
                    <tr key={row.conjunction_id} className="transition-colors hover:bg-surface-secondary/50">
                      <td className="px-6 py-4 font-mono">
                        <div className="text-text-primary">{row.primary_id}</div>
                        <div className="text-xs text-text-muted">{row.secondary_id}</div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-text-primary">{row.tca_utc}</td>
                      <td className="px-6 py-4 text-right font-mono text-text-primary">
                        {row.initial_miss_distance_km.toFixed(3)}
                        {row.post_maneuver_miss_distance_km ? (
                          <div className="mt-1 text-xs text-success-light">→ {row.post_maneuver_miss_distance_km.toFixed(3)}</div>
                        ) : null}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-text-primary">{row.message_count}</td>
                      <td className="px-6 py-4">
                        <Badge status={STATUS_BADGE[displayStatus] || 'warning'}>
                          {displayStatus.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <Link to={`/negotiate/${row.conjunction_id}`}>
                          <Button variant="secondary" className="px-3 py-1.5 text-xs">View</Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
