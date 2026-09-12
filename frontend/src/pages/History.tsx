import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const STATUS_STYLE: Record<string, string> = {
  alerted: 'border-danger/40 bg-danger-muted/35 text-danger-light',
  negotiating: 'border-warning/40 bg-warning-muted/35 text-warning-light',
  resolved: 'border-success/40 bg-success-muted/35 text-success-light',
  escalated: 'border-danger/40 bg-danger-muted/35 text-danger-light',
  stood_down: 'border-success/40 bg-success-muted/35 text-success-light',
  approved: 'border-success/40 bg-success-muted/35 text-success-light',
  approved_no_action: 'border-success/40 bg-success-muted/35 text-success-light',
  no_safe_maneuver_found: 'border-danger/40 bg-danger-muted/35 text-danger-light',
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

const SKELETON_WIDTHS = ['w-1/2', 'w-2/3', 'w-3/4', 'w-5/6'] as const;

function compactUtc(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 19)}Z`;
}

export default function History() {
  const [data, setData] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      setError(false);
      try {
        const url = statusFilter ? `/api/history?status=${statusFilter}` : '/api/history';
        const response = await fetch(url);
        if (!response.ok) throw new Error(`History request failed with ${response.status}`);
        const payload: HistoryRow[] = await response.json();
        setData(payload);
      } catch (requestError) {
        console.error('[History] failed to load decision records', requestError);
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    void fetchHistory();
  }, [statusFilter]);

  const resolvedCount = data.filter((row) => {
    const status = row.resolution_status ?? row.conjunction_status;
    return status === 'resolved' || status.startsWith('approved');
  }).length;
  const escalatedCount = data.filter((row) => {
    const status = row.resolution_status ?? row.conjunction_status;
    return status === 'escalated' || status === 'no_safe_maneuver_found';
  }).length;
  const totalMessages = data.reduce((total, row) => total + row.message_count, 0);

  return (
    <main className="ops-grid min-h-[calc(100dvh-4rem)] bg-background px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1440px]">
        <header className="grid gap-5 border-b border-border pb-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <div className="flex items-center gap-3 font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">
              <span>archive / decision records</span>
              <span aria-hidden="true" className="h-px w-8 bg-border-light" />
              <span>scope / all operators</span>
            </div>
            <h1 className="mt-3 text-3xl font-semibold uppercase tracking-[-0.025em] text-text-primary sm:text-4xl">Resolution archive</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
              Immutable conjunction outcomes, agent exchanges, and maneuver deltas retained for operational audit.
            </p>
          </div>

          <label className="grid min-w-56 gap-1.5 font-mono text-[9px] uppercase tracking-[0.14em] text-text-muted" htmlFor="status-filter">
            Record state
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="h-10 border border-border bg-surface-muted px-3 font-mono text-[10px] uppercase tracking-wider text-text-primary outline-none transition-colors hover:border-border-light focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <option value="">All records</option>
              <option value="resolved">Resolved</option>
              <option value="escalated">Escalated</option>
              <option value="approved">Approved</option>
              <option value="no_safe_maneuver_found">No safe maneuver</option>
            </select>
          </label>
        </header>

        <section className="mt-5 grid grid-cols-2 gap-px border border-border bg-border lg:grid-cols-4" aria-label="Archive summary">
          {[
            ['Visible records', loading ? '—' : String(data.length).padStart(2, '0'), 'current query'],
            ['Resolved', loading ? '—' : String(resolvedCount).padStart(2, '0'), 'approved outcomes'],
            ['Escalated', loading ? '—' : String(escalatedCount).padStart(2, '0'), 'operator review'],
            ['Agent messages', loading ? '—' : String(totalMessages).padStart(2, '0'), 'retained frames'],
          ].map(([label, value, detail]) => (
            <div key={label} className="bg-surface-muted/90 px-4 py-4 sm:px-5">
              <p className="font-mono text-[8px] uppercase tracking-[0.16em] text-text-muted">{label}</p>
              <p className="mt-1.5 font-mono text-2xl font-semibold tabular-nums text-text-primary">{value}</p>
              <p className="mt-1 font-mono text-[8px] uppercase tracking-wider text-text-muted">{detail}</p>
            </div>
          ))}
        </section>

        <section className="mt-3 border border-border bg-surface-muted/75" aria-labelledby="archive-ledger-title">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
            <div className="flex items-center gap-3">
              <span className={`h-1.5 w-1.5 ${error ? 'bg-danger' : loading ? 'bg-warning animate-pulse' : 'bg-success'}`} />
              <h2 id="archive-ledger-title" className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-text-primary">Conjunction ledger</h2>
            </div>
            <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-text-muted">
              {error ? 'archive unavailable' : loading ? 'synchronizing' : `${data.length} rows returned`}
            </span>
          </header>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] table-fixed border-collapse text-left">
              <thead className="bg-surface-secondary/55 font-mono text-[8px] uppercase tracking-[0.16em] text-text-muted">
                <tr>
                  <th className="w-16 border-r border-border px-3 py-2.5 font-medium">rec</th>
                  <th className="w-52 border-r border-border px-3 py-2.5 font-medium">object pair</th>
                  <th className="w-48 border-r border-border px-3 py-2.5 font-medium">tca / utc</th>
                  <th className="w-40 border-r border-border px-3 py-2.5 text-right font-medium">miss / km</th>
                  <th className="w-32 border-r border-border px-3 py-2.5 text-right font-medium">rel vel</th>
                  <th className="w-20 border-r border-border px-3 py-2.5 text-right font-medium">msgs</th>
                  <th className="w-52 border-r border-border px-3 py-2.5 font-medium">outcome</th>
                  <th className="w-24 px-3 py-2.5 text-right font-medium">record</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  Array.from({ length: 4 }, (_, index) => (
                    <tr key={index} className="animate-pulse">
                      {Array.from({ length: 8 }, (_, cell) => (
                        <td key={cell} className="border-r border-border px-3 py-4 last:border-r-0">
                          <span className={`block h-2 bg-surface-tertiary ${SKELETON_WIDTHS[(index + cell) % SKELETON_WIDTHS.length]}`} />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : error ? (
                  <tr>
                    <td colSpan={8} className="h-44 px-5 py-8">
                      <div className="flex items-center gap-4 border-l-2 border-danger pl-4">
                        <div>
                          <p className="font-mono text-xs uppercase tracking-wider text-danger-light">Archive connection failed</p>
                          <p className="mt-1 text-xs text-text-muted">The history endpoint did not return a valid record set. Live monitoring remains unaffected.</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : data.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="h-44 px-5 py-8">
                      <div className="flex items-center gap-4 border-l-2 border-warning pl-4">
                        <div>
                          <p className="font-mono text-xs uppercase tracking-wider text-warning-light">No matching records</p>
                          <p className="mt-1 text-xs text-text-muted">Resolved or escalated sessions will appear here after persistence completes.</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  data.map((row, index) => {
                    const displayStatus = row.resolution_status ?? row.conjunction_status;
                    return (
                      <tr key={row.conjunction_id} className="align-middle transition-colors duration-200 hover:bg-surface-secondary/40">
                        <td className="border-r border-border px-3 py-4 font-mono text-[9px] text-text-muted">{String(index + 1).padStart(3, '0')}</td>
                        <td className="border-r border-border px-3 py-4">
                          <span className="font-mono text-xs font-semibold text-accent-light">{row.primary_id}</span>
                          <span className="mx-2 text-text-muted">/</span>
                          <span className="font-mono text-xs font-semibold text-success-light">{row.secondary_id}</span>
                          <span className="mt-1 block truncate font-mono text-[8px] text-text-muted">{row.conjunction_id}</span>
                        </td>
                        <td className="border-r border-border px-3 py-4 font-mono text-[10px] tabular-nums text-text-secondary">{compactUtc(row.tca_utc)}</td>
                        <td className="border-r border-border px-3 py-4 text-right font-mono text-xs tabular-nums text-text-primary">
                          <span>{row.initial_miss_distance_km.toFixed(3)}</span>
                          {row.post_maneuver_miss_distance_km !== null && (
                            <span className="mt-1 block text-success-light">→ {row.post_maneuver_miss_distance_km.toFixed(3)}</span>
                          )}
                        </td>
                        <td className="border-r border-border px-3 py-4 text-right font-mono text-[10px] tabular-nums text-text-secondary">{row.relative_velocity_kmps.toFixed(3)}</td>
                        <td className="border-r border-border px-3 py-4 text-right font-mono text-xs tabular-nums text-text-primary">{row.message_count}</td>
                        <td className="border-r border-border px-3 py-4">
                          <span className={`inline-block border px-2 py-1 font-mono text-[8px] font-semibold uppercase tracking-wider ${STATUS_STYLE[displayStatus] ?? STATUS_STYLE.negotiating}`}>
                            {displayStatus.replace(/_/g, ' ')}
                          </span>
                          {row.maneuver_type && <span className="mt-1.5 block font-mono text-[8px] uppercase text-text-muted">{row.maneuver_type}</span>}
                        </td>
                        <td className="px-3 py-4 text-right">
                          <Link
                            to={`/negotiate/${row.conjunction_id}`}
                            className="border-b border-border-light pb-1 font-mono text-[9px] uppercase tracking-wider text-text-secondary transition-colors hover:border-accent hover:text-accent-light focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
                          >
                            inspect →
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2.5 font-mono text-[8px] uppercase tracking-[0.15em] text-text-muted sm:px-5">
            <span>sqlite persistence / append-only sessions</span>
            <span>all timestamps normalized to utc</span>
          </footer>
        </section>
      </div>
    </main>
  );
}
