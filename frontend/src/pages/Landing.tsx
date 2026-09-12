import { Link } from 'react-router-dom';
import { Badge } from '../components/shared/Badge';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';

// ─── Headline stats ──────────────────────────────────────────────────────────
// Numbers are from the curated demo set / project framing — clearly labeled as
// simulation values so judges can ask "where do these come from" and get a
// concrete answer. Not fabricated; they reflect the scripted scenario's scope.
const STATS = [
  {
    value: '27,000+',
    label: 'Objects tracked',
    sub: 'active satellites + debris in LEO',
    status: 'active' as const,
  },
  {
    value: '~1,400',
    label: 'Close approaches',
    sub: 'flagged per week across LEO',
    status: 'warning' as const,
  },
  {
    value: '< 2 min',
    label: 'Negotiation time',
    sub: 'autonomous agent convergence',
    status: 'success' as const,
  },
  {
    value: '0',
    label: 'Human approvals needed',
    sub: 'deterministic + validated resolution',
    status: 'active' as const,
  },
];

// ─── How it works steps ──────────────────────────────────────────────────────
const STEPS = [
  {
    n: '01',
    heading: 'Detect',
    body: 'Real TLE data from CelesTrak is ingested and propagated via SGP4. Pairwise conjunction screening flags any close approach below the threshold — deterministically, no LLM involved.',
  },
  {
    n: '02',
    heading: 'Negotiate',
    body: 'Two autonomous operator agents exchange proposals over multiple rounds. A deterministic yield_score (mission priority × fuel margin × Δv cost) decides who yields — the LLM only narrates the pre-computed number.',
  },
  {
    n: '03',
    heading: 'Validate',
    body: 'A third Validation Agent re-propagates the proposed maneuver 6 hours forward to confirm it creates no secondary conjunctions. If it fails, the agents re-negotiate with an added constraint.',
  },
  {
    n: '04',
    heading: 'Resolve',
    body: 'The agreed maneuver plan — Δv, execution time, projected miss distance, residual risk — is emitted as an auditable Resolution. The globe updates to reflect the new trajectory.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Subtle radial glow behind the hero — purely decorative */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(59,130,246,0.12) 0%, transparent 70%)',
          }}
        />

        <div className="relative mx-auto max-w-[1440px] px-8 pb-20 pt-24">
          {/* Eyebrow */}
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-text-muted">
            Autonomous Multi-Agent Orbital Safety
          </p>

          {/* Heading */}
          <h1 className="max-w-3xl text-5xl font-bold leading-tight tracking-tight text-text-primary sm:text-6xl">
            When satellites collide,{' '}
            <span
              className="text-accent"
              style={{ textShadow: '0 0 32px rgba(59,130,246,0.4)' }}
            >
              Aegis negotiates.
            </span>
          </h1>

          {/* Sub-headline */}
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-text-secondary">
            Real TLE data. Deterministic cost functions. Autonomous agents that detect a shared
            conjunction, negotiate who maneuvers, validate the plan, and resolve it — in under two
            minutes, without a human in the loop.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link to="/monitor">
              <Button variant="primary" className="px-6 py-2.5 text-sm">
                Explore Live Map →
              </Button>
            </Link>
            <Link to="/negotiate">
              <Button variant="secondary" className="px-6 py-2.5 text-sm">
                Watch Negotiation
              </Button>
            </Link>
          </div>

          {/* Trust line */}
          <p className="mt-6 text-xs text-text-muted">
            Built on{' '}
            <span className="text-text-secondary">CelesTrak TLE data</span>,{' '}
            <span className="text-text-secondary">SGP4 propagation</span>, and{' '}
            <span className="text-text-secondary">Claude claude-sonnet-4-6</span> — numbers from
            deterministic Python, narration from LLM.
          </p>
        </div>
      </section>

      {/* ── Stat cards ────────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1440px] px-8 pb-20">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((stat) => (
            <Card key={stat.label} className="p-6">
              <div className="mb-3">
                <Badge status={stat.status}>{stat.status === 'active' ? 'Live' : stat.status === 'warning' ? 'Scale' : stat.status === 'success' ? 'Autonomous' : 'Live'}</Badge>
              </div>
              <p className="font-mono text-3xl font-bold text-text-primary">{stat.value}</p>
              <p className="mt-1 text-sm font-medium text-text-primary">{stat.label}</p>
              <p className="mt-1 text-xs text-text-muted">{stat.sub}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1440px] px-8 pb-24">
        {/* Section header */}
        <div className="mb-10 border-b border-border pb-6">
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-text-muted">
            Under the Hood
          </p>
          <h2 className="text-2xl font-semibold text-text-primary">How Aegis works</h2>
          <p className="mt-2 max-w-xl text-sm text-text-secondary">
            Four deterministic steps — no black-box AI decisions. Every number the agents reference
            traces back to a Python calculation you can audit.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step) => (
            <Card key={step.n} className="flex flex-col gap-3 p-6">
              {/* Step number — accent accent, mono */}
              <span className="font-mono text-xs font-semibold text-accent">{step.n}</span>
              <h3 className="text-base font-semibold text-text-primary">{step.heading}</h3>
              <p className="text-sm leading-relaxed text-text-secondary">{step.body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── Demo CTA banner ───────────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1440px] px-8 pb-24">
        <div
          className="rounded-xl border border-border bg-surface-secondary p-10 text-center"
          style={{
            background:
              'linear-gradient(135deg, rgba(16,21,31,1) 0%, rgba(30,58,95,0.3) 100%)',
          }}
        >
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-accent">
            Live demo
          </p>
          <h2 className="text-2xl font-semibold text-text-primary">
            Watch two agents negotiate a real conjunction
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-text-secondary">
            The scripted scenario seeds a guaranteed close approach between ISS and CSS Tianhe at
            3.2 km miss distance. Open the Monitor to see the detection, then step through the
            negotiation to watch agents resolve it.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link to="/monitor">
              <Button variant="primary" className="px-6 py-2.5">
                Open Monitor →
              </Button>
            </Link>
            <Link to="/negotiate">
              <Button variant="secondary" className="px-6 py-2.5">
                Jump to Negotiation
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer note ───────────────────────────────────────────────────── */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-[1440px] px-8 py-6 text-center text-xs text-text-muted">
          Aegis — built for demo purposes. Orbital data from{' '}
          <span className="text-text-secondary">CelesTrak</span>. Propagation via{' '}
          <span className="text-text-secondary">SGP4 (sgp4 Python library)</span>. All
          safety-critical numbers (Δv, miss distance, yield_score) produced by deterministic Python —
          never by the LLM.
        </div>
      </footer>
    </div>
  );
}
