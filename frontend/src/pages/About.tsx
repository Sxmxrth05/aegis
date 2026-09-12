import { Link } from 'react-router-dom';

const INVARIANTS = [
  ['01', 'Deterministic authority', 'Δv, miss distance, and yield score originate in Python code — never in generated text.'],
  ['02', 'Transport separation', 'Agents emit typed events through the orchestrator; they never address WebSocket clients directly.'],
  ['03', 'Independent validation', 'A third agent re-propagates the proposed maneuver before any resolution is approved.'],
  ['04', 'Bounded negotiation', 'Every exchange is round-capped and escalates deterministically if the operators cannot converge.'],
];

const SOURCES = [
  { id: 'CAT-01', name: 'CelesTrak', role: 'Two-line element catalogue', mode: 'LIVE + CACHE', tone: 'text-accent-light' },
  { id: 'PHY-01', name: 'SGP4', role: 'ECI position and velocity propagation', mode: 'LOCAL', tone: 'text-success-light' },
  { id: 'ENV-02', name: 'NOAA SWPC', role: 'Space-weather context', mode: 'PHASE 2', tone: 'text-warning-light' },
  { id: 'NAR-01', name: 'Claude', role: 'Operational narration only', mode: 'FALLBACK SAFE', tone: 'text-text-secondary' },
];

const ROADMAP = [
  { phase: '00', title: 'Contracts', state: 'COMPLETE', detail: 'Schemas, event envelope, fixtures, ownership boundaries.' },
  { phase: '01', title: 'Live detection', state: 'COMPLETE', detail: 'TLE ingestion, SGP4 propagation, conjunction broadcast, globe.' },
  { phase: '02', title: 'Negotiation loop', state: 'BUILT', detail: 'Agent rounds, validation, resolution, trajectory, persistence.' },
  { phase: '03', title: 'Demo hardening', state: 'ACTIVE', detail: 'Offline proof, reconnect resilience, fallback verification, visual QA.' },
];

export default function About() {
  return (
    <main className="ops-grid min-h-[calc(100dvh-4rem)] bg-background px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1440px] border-x border-border">
        <section className="grid border-y border-border lg:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)]">
          <div className="relative overflow-hidden border-b border-border px-6 py-12 sm:px-8 lg:border-b-0 lg:border-r lg:px-10 lg:py-16">
            <div className="scan-beam" aria-hidden="true" />
            <div className="relative z-10">
              <div className="flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">
                <span>system manifest / aegis</span>
                <span aria-hidden="true" className="h-px w-8 bg-border-light" />
                <span>revision / mvp-03</span>
              </div>
              <h1 className="mt-7 max-w-4xl text-balance text-[clamp(2.8rem,6vw,5.8rem)] font-semibold uppercase leading-[0.9] tracking-[-0.05em] text-text-primary">
                Autonomous coordination for crowded orbit.
              </h1>
              <p className="mt-8 max-w-[62ch] border-l border-accent pl-5 text-sm leading-6 text-text-secondary sm:text-base">
                Aegis replaces slow, bilateral collision-avoidance email chains with a typed, auditable
                protocol. Operator agents negotiate responsibility; deterministic orbital mechanics and
                cost functions remain the authority for every safety decision.
              </p>
            </div>
          </div>

          <aside className="bg-surface-muted/75 p-6 sm:p-8 lg:p-9">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-accent-light">Mission directive</p>
            <blockquote className="mt-5 text-2xl font-medium leading-snug tracking-tight text-text-primary">
              Detect early. Negotiate visibly. Validate independently. Preserve the record.
            </blockquote>
            <dl className="mt-8 divide-y divide-border border-y border-border">
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Operating domain</dt>
                <dd className="text-right font-mono text-[10px] uppercase text-text-primary">LEO / demo set</dd>
              </div>
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Human approval</dt>
                <dd className="text-right font-mono text-[10px] uppercase text-success-light">not required</dd>
              </div>
              <div className="grid grid-cols-2 py-3">
                <dt className="text-xs text-text-muted">Unsafe outcome</dt>
                <dd className="text-right font-mono text-[10px] uppercase text-danger-light">explicit escalation</dd>
              </div>
            </dl>
            <Link
              to="/monitor"
              className="mt-8 inline-flex bg-accent px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-white transition duration-200 hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:translate-y-px"
            >
              Enter watch floor →
            </Link>
          </aside>
        </section>

        <section className="grid border-b border-border lg:grid-cols-[0.7fr_1.3fr]">
          <header className="border-b border-border p-6 sm:p-8 lg:border-b-0 lg:border-r">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-success-light">Safety contract</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-text-primary">The system cannot narrate its way around physics.</h2>
            <p className="mt-4 max-w-[45ch] text-sm leading-6 text-text-secondary">
              These boundaries make the demo inspectable when a judge asks where a number came from.
            </p>
          </header>
          <ol className="grid sm:grid-cols-2">
            {INVARIANTS.map(([index, title, detail], itemIndex) => (
              <li key={index} className={`p-6 sm:p-7 ${itemIndex % 2 === 1 ? 'sm:border-l sm:border-border' : ''} ${itemIndex > 1 ? 'border-t border-border' : itemIndex === 1 ? 'border-t border-border sm:border-t-0' : ''}`}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[9px] text-accent-light">INV-{index}</span>
                  <span className="h-1.5 w-1.5 bg-success shadow-[0_0_7px_var(--color-success)]" />
                </div>
                <h3 className="mt-5 text-sm font-semibold text-text-primary">{title}</h3>
                <p className="mt-2 text-xs leading-5 text-text-secondary">{detail}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="grid border-b border-border lg:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
          <div className="border-b border-border lg:border-b-0 lg:border-r">
            <header className="border-b border-border px-6 py-5 sm:px-8">
              <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">Data + computation register</p>
              <h2 className="mt-2 text-xl font-semibold text-text-primary">Operational dependencies</h2>
            </header>
            <div className="divide-y divide-border">
              {SOURCES.map((source) => (
                <article key={source.id} className="grid grid-cols-[4rem_minmax(0,1fr)_auto] items-center gap-4 px-6 py-4 transition-colors duration-200 hover:bg-surface-secondary/35 sm:px-8">
                  <span className={`font-mono text-[9px] font-semibold ${source.tone}`}>{source.id}</span>
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary">{source.name}</h3>
                    <p className="mt-0.5 text-xs text-text-muted">{source.role}</p>
                  </div>
                  <span className="border border-border px-2 py-1 font-mono text-[8px] uppercase tracking-wider text-text-secondary">{source.mode}</span>
                </article>
              ))}
            </div>
          </div>

          <aside className="bg-surface-muted/70 p-6 sm:p-8">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-warning-light">Scope declaration</p>
            <h2 className="mt-3 text-xl font-semibold text-text-primary">Simulation, not flight authority.</h2>
            <div className="mt-6 space-y-5 text-sm leading-6 text-text-secondary">
              <p>Aegis does not issue spacecraft commands or ingest private operator telemetry.</p>
              <p>Mission priority, fuel margin, and maneuver cost inputs are simulated for the negotiation demonstration.</p>
              <p>The curated object set keeps the demo deterministic and supports a fully cached, offline path.</p>
            </div>
          </aside>
        </section>

        <section>
          <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border px-6 py-5 sm:px-8">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">Program status</p>
              <h2 className="mt-2 text-xl font-semibold text-text-primary">Build roadmap</h2>
            </div>
            <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-warning-light">checkpoint verification pending</span>
          </header>
          <ol className="grid lg:grid-cols-4">
            {ROADMAP.map((item, index) => (
              <li key={item.phase} className={`relative p-6 sm:p-7 ${index > 0 ? 'border-t border-border lg:border-l lg:border-t-0' : ''}`}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[9px] text-accent-light">PHASE / {item.phase}</span>
                  <span className={`font-mono text-[8px] uppercase tracking-wider ${item.state === 'ACTIVE' ? 'text-warning-light' : 'text-success-light'}`}>{item.state}</span>
                </div>
                <h3 className="mt-7 text-base font-semibold text-text-primary">{item.title}</h3>
                <p className="mt-2 text-xs leading-5 text-text-secondary">{item.detail}</p>
                <span aria-hidden="true" className={`absolute bottom-0 left-0 h-0.5 ${item.state === 'ACTIVE' ? 'w-2/3 bg-warning' : 'w-full bg-success/50'}`} />
              </li>
            ))}
          </ol>
        </section>
      </div>
    </main>
  );
}
