import { Link } from 'react-router-dom';

const TELEMETRY = [
  { value: '27,000+', label: 'catalogued objects', detail: 'active spacecraft + debris' },
  { value: '~1,400', label: 'weekly approaches', detail: 'screened across LEO' },
  { value: '05.000 km', label: 'alert threshold', detail: 'deterministic trigger' },
  { value: '06 h', label: 'validation horizon', detail: 'secondary-risk sweep' },
];

const PIPELINE = [
  {
    code: 'MON',
    state: 'ACTIVE',
    title: 'Conjunction monitor',
    detail: 'CelesTrak TLE → SGP4 propagation → pairwise screen',
    output: 'ConjunctionAlert',
  },
  {
    code: 'NEG',
    state: 'ARMED',
    title: 'Operator negotiation',
    detail: 'Mission value + fuel margin + maneuver cost',
    output: 'NegotiationMessage',
  },
  {
    code: 'VAL',
    state: 'GATED',
    title: 'Safety validation',
    detail: 'Six-hour propagation against the tracked set',
    output: 'approve / reject',
  },
  {
    code: 'RES',
    state: 'READY',
    title: 'Resolution record',
    detail: 'Maneuver, Δv, execution UTC, residual risk',
    output: 'Resolution',
  },
];

function StatusMark({ tone = 'success' }: { tone?: 'success' | 'warning' | 'danger' }) {
  const color = {
    success: 'bg-success shadow-[0_0_8px_var(--color-success)]',
    warning: 'bg-warning shadow-[0_0_8px_var(--color-warning)]',
    danger: 'bg-danger shadow-[0_0_8px_var(--color-danger)]',
  }[tone];

  return <span aria-hidden="true" className={`inline-block h-1.5 w-1.5 ${color}`} />;
}

export default function Landing() {
  return (
    <main className="ops-grid min-h-screen bg-background text-text-primary">
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[minmax(0,1.45fr)_minmax(22rem,0.55fr)]">
          <div className="relative overflow-hidden border-border px-6 py-14 sm:px-8 lg:border-r lg:px-12 lg:py-20">
            <div className="scan-beam" aria-hidden="true" />
            <div className="relative z-10 max-w-4xl">
              <div className="mb-10 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[10px] uppercase tracking-[0.18em] text-text-muted">
                <span className="flex items-center gap-2 text-success-light">
                  <StatusMark /> node online
                </span>
                <span>AEGIS / OPS-01</span>
                <span>UTC synchronized</span>
              </div>

              <p className="mb-3 font-mono text-xs uppercase tracking-[0.24em] text-accent-light">
                autonomous orbital deconfliction
              </p>
              <h1 className="max-w-4xl text-balance text-[clamp(3rem,7vw,6.8rem)] font-semibold uppercase leading-[0.86] tracking-[-0.055em]">
                Traffic conflict.
                <span className="mt-2 block text-text-secondary">Resolution computed.</span>
              </h1>

              <div className="mt-10 grid max-w-3xl gap-8 border-l border-accent pl-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                <p className="max-w-[62ch] text-sm leading-6 text-text-secondary sm:text-base">
                  Aegis detects close approaches, assigns maneuver responsibility through deterministic
                  cost functions, and validates the resulting trajectory before a plan is released.
                  Language models explain the record; they never produce safety-critical numbers.
                </p>
                <div className="flex items-center gap-3">
                  <Link
                    to="/monitor"
                    className="bg-accent px-5 py-3 font-mono text-xs font-semibold uppercase tracking-wider text-white transition duration-200 hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:translate-y-px"
                  >
                    Open monitor ↗
                  </Link>
                  <Link
                    to="/negotiate"
                    className="border-b border-border-light px-1 py-3 font-mono text-xs uppercase tracking-wider text-text-secondary transition duration-200 hover:border-accent hover:text-text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
                  >
                    View ledger
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <aside className="relative bg-surface-muted/80 px-6 py-8 sm:px-8 lg:px-7 lg:py-10" aria-label="Active conjunction snapshot">
            <div className="flex items-start justify-between border-b border-border pb-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-text-muted">Priority queue / 01</p>
                <h2 className="mt-2 text-lg font-semibold">Active conjunction</h2>
              </div>
              <span className="flex items-center gap-2 border border-danger/30 bg-danger-muted/50 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-danger-light">
                <StatusMark tone="danger" /> alerted
              </span>
            </div>

            <div className="mt-7 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Primary / 25544</p>
                <p className="mt-1 text-xl font-semibold">ISS</p>
                <p className="text-xs text-text-secondary">ZARYA</p>
              </div>
              <div className="relative h-px w-14 bg-danger/50">
                <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border border-danger bg-background" />
              </div>
              <div className="text-right">
                <p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Secondary / 48274</p>
                <p className="mt-1 text-xl font-semibold">CSS</p>
                <p className="text-xs text-text-secondary">TIANHE</p>
              </div>
            </div>

            <dl className="mt-8 divide-y divide-border-muted border-y border-border">
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Predicted miss</dt>
                <dd className="text-right font-mono text-sm font-semibold text-danger-light">3.202 km</dd>
              </div>
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Relative velocity</dt>
                <dd className="text-right font-mono text-sm text-text-primary">9.052 km/s</dd>
              </div>
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Decision source</dt>
                <dd className="text-right font-mono text-[11px] uppercase text-success-light">Python / deterministic</dd>
              </div>
            </dl>

            <div className="mt-7 flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-text-muted">
              <span>cached scenario ready</span>
              <span className="text-warning-light">awaiting operator trigger</span>
            </div>
          </aside>
        </div>
      </section>

      <section className="border-b border-border bg-surface/55" aria-label="System telemetry">
        <dl className="mx-auto grid max-w-[1440px] grid-cols-2 lg:grid-cols-4">
          {TELEMETRY.map((item, index) => (
            <div
              key={item.label}
              className={`px-6 py-5 sm:px-8 ${index % 2 !== 0 ? 'border-l border-border' : ''} ${index > 1 ? 'border-t border-border lg:border-t-0' : ''} ${index > 0 ? 'lg:border-l lg:border-border' : ''}`}
            >
              <dd className="font-mono text-xl font-medium tabular-nums text-text-primary">{item.value}</dd>
              <dt className="mt-1 text-xs font-medium text-text-secondary">{item.label}</dt>
              <p className="mt-1 font-mono text-[9px] uppercase tracking-wider text-text-muted">{item.detail}</p>
            </div>
          ))}
        </dl>
      </section>

      <section className="mx-auto grid max-w-[1440px] border-x border-border lg:grid-cols-[0.92fr_1.35fr_0.73fr]">
        <div className="border-b border-border p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-light">Execution chain</p>
          <h2 className="mt-3 max-w-sm text-3xl font-semibold leading-tight tracking-tight">
            One incident. Four accountable stages.
          </h2>
          <p className="mt-4 max-w-[46ch] text-sm leading-6 text-text-secondary">
            The interface exposes the handoff between physics, negotiation, validation, and resolution.
            Each emitted object remains inspectable.
          </p>
        </div>

        <ol className="divide-y divide-border">
          {PIPELINE.map((step, index) => (
            <li key={step.code} className="group grid grid-cols-[3.5rem_minmax(0,1fr)_auto] gap-4 px-6 py-5 transition-colors duration-200 hover:bg-surface-secondary/45 sm:px-8">
              <div className="font-mono text-xs text-text-muted">
                <span className="block text-accent-light">{step.code}</span>
                <span className="mt-1 block text-[9px]">0{index + 1}</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <StatusMark tone={index === 2 ? 'warning' : 'success'} />
                  <h3 className="text-sm font-semibold text-text-primary">{step.title}</h3>
                </div>
                <p className="mt-1.5 text-xs leading-5 text-text-secondary">{step.detail}</p>
              </div>
              <div className="text-right font-mono text-[9px] uppercase tracking-wider text-text-muted">
                <span className="block text-text-secondary">{step.state}</span>
                <span className="mt-2 hidden border-t border-border pt-2 xl:block">{step.output}</span>
              </div>
            </li>
          ))}
        </ol>

        <aside className="border-t border-border bg-surface-muted/70 p-6 sm:p-8 lg:border-l lg:border-t-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Audit contract</p>
          <div className="mt-6 space-y-6">
            <div className="border-l-2 border-success pl-4">
              <p className="font-mono text-[10px] uppercase tracking-wider text-success-light">Verified source</p>
              <p className="mt-2 text-sm font-medium">Safety numbers originate in deterministic Python.</p>
            </div>
            <div className="border-l-2 border-accent pl-4">
              <p className="font-mono text-[10px] uppercase tracking-wider text-accent-light">Narration boundary</p>
              <p className="mt-2 text-sm font-medium">The LLM explains a computed decision; it does not make one.</p>
            </div>
            <div className="border-l-2 border-warning pl-4">
              <p className="font-mono text-[10px] uppercase tracking-wider text-warning-light">Fail-safe</p>
              <p className="mt-2 text-sm font-medium">Unsafe or non-convergent plans escalate as valid outcomes.</p>
            </div>
          </div>
          <Link
            to="/negotiate"
            className="mt-10 inline-flex items-center gap-3 border-t border-border-light pt-4 font-mono text-xs uppercase tracking-wider text-text-primary transition-colors hover:text-accent-light focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
          >
            Inspect negotiation record <span aria-hidden="true">→</span>
          </Link>
        </aside>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-2 px-6 py-5 font-mono text-[9px] uppercase tracking-wider text-text-muted sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>Aegis orbital safety demonstrator / CelesTrak + SGP4</span>
          <span>Δv · miss distance · yield score — deterministic sources only</span>
        </div>
      </footer>
    </main>
  );
}
