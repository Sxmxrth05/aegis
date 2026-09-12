import { animate, stagger } from 'animejs';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { InteractiveSatellite } from '../components/globe/InteractiveSatellite';
import { OrbitalSituation } from '../components/globe/OrbitalSituation';

/* ── data ─────────────────────────────────────────────────── */

const PIPELINE = [
  { index: '01', code: 'DETECT',    label: 'Detect',    detail: 'SGP4 propagation screens every tracked pair against a 5 km conjunction threshold.' },
  { index: '02', code: 'EVALUATE',  label: 'Evaluate',  detail: 'Cost functions score each candidate maneuver on mission value, fuel, and delta-v.' },
  { index: '03', code: 'NEGOTIATE', label: 'Negotiate', detail: 'Operator agents exchange typed proposals until a mutually acceptable plan emerges.' },
  { index: '04', code: 'VALIDATE',  label: 'Validate',  detail: 'An independent agent re-propagates the agreed maneuver over a 6-hour forward window.' },
  { index: '05', code: 'RECOMMEND', label: 'Recommend', detail: 'A signed Resolution record is emitted. Authority to execute remains with the operator.' },
];

const PRINCIPLES = [
  { code: 'SF', label: 'Safety First',         detail: 'No plan that increases collision risk is approved, regardless of mission priority.' },
  { code: 'MV', label: 'Mission Value',         detail: 'Orbital slot and mission priority are weighed against fuel cost deterministically.' },
  { code: 'DV', label: 'Minimum Delta-V',       detail: 'The smallest effective burn is preferred to preserve operational margins.' },
  { code: 'DI', label: 'Debris Impact',         detail: 'Maneuvers that redistribute risk to other tracked objects are penalised.' },
  { code: 'EF', label: 'Exec. Feasibility',     detail: 'Plans are bounded by realistic spacecraft actuation constraints.' },
];

function ProblemMetrics({ className = '' }: { className?: string }) {
  return (
    <div className={`pt-6 border-t border-border/70 space-y-2.5 font-mono text-[10px] uppercase tracking-[0.16em] ${className}`}>
      <div className="flex items-center gap-2.5">
        <span className="font-bold text-accent">01 /</span>
        <span className="text-text-secondary">Independent Operators</span>
      </div>
      <div className="flex items-center gap-2.5">
        <span className="font-bold text-accent">02 /</span>
        <span className="text-text-secondary">Shared Orbital Space</span>
      </div>
      <div className="flex items-center gap-2.5">
        <span className="font-bold text-accent">03 /</span>
        <span className="text-text-secondary">Conflicting Maneuvers</span>
      </div>
    </div>
  );
}

/* ── component ─────────────────────────────────────────────── */

export default function About() {
  /* section refs for independent scroll-triggered animations */
  const problemSectionRef = useRef<HTMLElement>(null);
  const problemLeftRef = useRef<HTMLDivElement>(null);
  const problemRightRef = useRef<HTMLDivElement>(null);
  const [visualMode, setVisualMode] = useState<'SPACECRAFT' | 'ORBIT'>('SPACECRAFT');

  /* page entry stagger (skipping problem section which triggers on scroll) */
  const pageRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = pageRef.current;
    if (!el) return;
    const sections = (Array.from(el.children) as HTMLElement[]).filter(
      (child) => child !== problemSectionRef.current,
    );
    animate(sections, {
      opacity: [0, 1],
      translateY: [14, 0],
      duration: 400,
      delay: stagger(75),
      easing: 'easeOutCubic',
    });
  }, []);

  /* problem section scroll-triggered entrance (triggers once at ~20% visibility) */
  useEffect(() => {
    const el = problemSectionRef.current;
    if (!el) return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.style.opacity = '1';
      if (problemLeftRef.current) {
        problemLeftRef.current.style.opacity = '1';
        problemLeftRef.current.style.transform = 'none';
      }
      if (problemRightRef.current) {
        problemRightRef.current.style.opacity = '1';
        problemRightRef.current.style.transform = 'none';
      }
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();

        el.style.opacity = '1';

        // Left text column: opacity 0 -> 1, y 32 -> 0 (duration ~0.8s easeOut)
        if (problemLeftRef.current) {
          animate(problemLeftRef.current, {
            opacity: [0, 1],
            translateY: [32, 0],
            duration: 800,
            easing: 'easeOutCubic',
          });
        }

        // Right interactive visualization: opacity 0 -> 1, x 40 -> 0, scale 0.97 -> 1 (130ms stagger)
        if (problemRightRef.current) {
          animate(problemRightRef.current, {
            opacity: [0, 1],
            translateX: [40, 0],
            scale: [0.97, 1],
            duration: 800,
            delay: 130,
            easing: 'easeOutCubic',
          });
        }
      },
      { threshold: 0.2 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /* pipeline steps stagger on scroll (both directions) */
  const pipelineRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = pipelineRef.current;
    if (!el) return;

    let hasAnimatedIn = false;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.1) {
          if (!hasAnimatedIn) {
            hasAnimatedIn = true;
            animate(Array.from(el.children) as HTMLElement[], {
              opacity: [0, 1],
              translateY: [10, 0],
              duration: 320,
              delay: stagger(60),
              easing: 'easeOutCubic',
            });
          }
        } else if (!entry.isIntersecting || entry.intersectionRatio === 0) {
          if (hasAnimatedIn) {
            hasAnimatedIn = false;
            Array.from(el.children).forEach((child) => {
              (child as HTMLElement).style.opacity = '0';
            });
          }
        }
      },
      { threshold: [0, 0.1] },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /* principles stagger on scroll (both directions) */
  const principlesRef = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = principlesRef.current;
    if (!el) return;

    let hasAnimatedIn = false;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.1) {
          if (!hasAnimatedIn) {
            hasAnimatedIn = true;
            animate(Array.from(el.children) as HTMLElement[], {
              opacity: [0, 1],
              translateX: [-8, 0],
              duration: 300,
              delay: stagger(50),
              easing: 'easeOutCubic',
            });
          }
        } else if (!entry.isIntersecting || entry.intersectionRatio === 0) {
          if (hasAnimatedIn) {
            hasAnimatedIn = false;
            Array.from(el.children).forEach((child) => {
              (child as HTMLElement).style.opacity = '0';
            });
          }
        }
      },
      { threshold: [0, 0.1] },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <main className="ops-grid min-h-[calc(100dvh-4rem)] bg-background text-text-primary">
      <div
        ref={pageRef}
        className="mx-auto w-full max-w-[1200px] px-4 py-10 sm:px-6 lg:px-8"
      >

        {/* ─── 1. HERO ─────────────────────────────────────── */}
        <section
          className="relative border border-border overflow-hidden"
          style={{ opacity: 0 }}
        >
          <div className="scan-beam" aria-hidden="true" />

          <div className="relative z-10 px-7 py-14 sm:px-10 sm:py-16 lg:py-20">
            {/* eyebrow */}
            <div className="flex items-center gap-4 font-mono text-[9px] uppercase tracking-[0.22em] text-text-muted">
              <span>System manifest</span>
              <span aria-hidden="true" className="h-px w-8 bg-border-light" />
              <span>Aegis Ops</span>
              <span aria-hidden="true" className="h-px w-8 bg-border-light" />
              {/* simulation env badge */}
              <span className="flex items-center gap-1.5 border border-success/25 bg-success-muted/35 px-2 py-0.5 text-success-light">
                <span className="h-1 w-1 rounded-full bg-success shadow-[0_0_5px_var(--color-success)]" />
                Simulation environment
              </span>
            </div>

            {/* headline */}
            <h1
              className="mt-8 font-sans font-bold uppercase tracking-[-0.045em] text-text-primary"
              style={{ fontSize: 'clamp(2.6rem,7vw,5.6rem)', lineHeight: '0.9' }}
            >
              <span className="block">Autonomous coordination</span>
              <span className="block text-accent-light">for crowded orbit.</span>
            </h1>

            {/* description */}
            <p className="mt-8 max-w-[58ch] border-l-2 border-accent pl-5 text-sm leading-7 text-text-secondary sm:text-base">
              Aegis helps spacecraft operators detect conjunctions, evaluate competing maneuver
              options, and coordinate safer orbital decisions — without manual email chains or
              opaque bilateral processes.
            </p>

            {/* CTA row */}
            <div className="mt-10 flex flex-wrap items-center gap-5">
              <Link
                to="/monitor"
                className="inline-flex items-center gap-2.5 bg-accent px-5 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-white transition duration-200 hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:translate-y-px"
              >
                Enter mission control
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-3 w-3">
                  <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
            </div>
          </div>

          {/* bottom accent bar */}
          <div className="absolute bottom-0 left-0 h-px w-full bg-border" />
          <div className="absolute bottom-0 left-0 h-px w-1/3 bg-accent/60" />
        </section>

        {/* ─── 2. THE PROBLEM ──────────────────────────────── */}
        <section
          ref={problemSectionRef}
          className="relative mt-8 py-10 lg:py-14 border-t border-b border-border"
          style={{ opacity: 0 }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[minmax(0,9fr)_minmax(0,11fr)] gap-8 lg:gap-12 items-center">
            {/* LEFT — 45%: Mission / problem statement */}
            <div
              ref={problemLeftRef}
              className="w-full"
              style={{ opacity: 0, transform: 'translateY(32px)' }}
            >
              {/* Eyebrow */}
              <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.24em] text-accent-light">
                <span className="h-1 w-1 rounded-full bg-accent shadow-[0_0_6px_var(--color-accent)]" />
                <span>The Problem</span>
              </div>

              {/* Large Heading */}
              <h2
                className="mt-4 font-sans font-bold uppercase tracking-[-0.04em] text-text-primary"
                style={{ fontSize: 'clamp(1.9rem, 3.8vw, 3rem)', lineHeight: 0.98 }}
              >
                <span className="block">Orbit is becoming</span>
                <span className="block text-accent-light">a coordination problem.</span>
              </h2>

              {/* Body */}
              <p className="mt-5 text-sm leading-relaxed text-text-secondary sm:text-base sm:leading-7">
                Independent spacecraft operators share the same orbital environment, but a maneuver that protects one satellite can create risk for another.
              </p>

              {/* Second short line */}
              <p className="mt-3.5 border-l-2 border-accent/50 pl-3.5 text-xs sm:text-sm leading-relaxed text-text-muted">
                Aegis turns collision avoidance into a coordination problem.
              </p>

              {/* Metrics (Desktop & Tablet) */}
              <ProblemMetrics className="hidden md:block mt-8" />
            </div>

            {/* RIGHT — 55%: Interactive Spacecraft / Orbital Command Visualization */}
            <div
              ref={problemRightRef}
              className="w-full"
              style={{ opacity: 0, transform: 'translateX(40px) scale(0.97)' }}
            >
              {/* Visualization Mode Selector */}
              <div className="mb-2 flex items-center justify-between font-mono text-[8.5px] uppercase tracking-[0.16em]">
                <span className="text-text-muted">Aegis Mission Asset Visualization</span>
                <div className="flex items-center gap-1 border border-border/80 bg-[#0a0e17] p-0.5">
                  <button
                    onClick={() => setVisualMode('SPACECRAFT')}
                    className={`px-2 py-0.5 transition ${
                      visualMode === 'SPACECRAFT'
                        ? 'bg-accent text-white font-bold'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    SPACECRAFT
                  </button>
                  <button
                    onClick={() => setVisualMode('ORBIT')}
                    className={`px-2 py-0.5 transition ${
                      visualMode === 'ORBIT'
                        ? 'bg-accent text-white font-bold'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    ORBIT (3D)
                  </button>
                </div>
              </div>

              {visualMode === 'SPACECRAFT' ? <InteractiveSatellite /> : <OrbitalSituation />}

              {/* Metrics (Mobile stack order: 1. Heading -> 2. Description -> 3. Interactive Visualization -> 4. Metrics) */}
              <ProblemMetrics className="block md:hidden mt-7" />
            </div>
          </div>
        </section>

        {/* ─── 3. HOW AEGIS WORKS ──────────────────────────── */}
        <section
          className="mt-4 border border-border"
          style={{ opacity: 0 }}
        >
          <header className="border-b border-border px-7 py-5 sm:px-9">
            <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-text-muted">
              Agent pipeline
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
              How Aegis works
            </h2>
          </header>

          {/* 5-step horizontal pipeline */}
          <ol
            ref={pipelineRef}
            className="grid divide-y divide-border sm:grid-cols-5 sm:divide-x sm:divide-y-0"
          >
            {PIPELINE.map((step, i) => (
              <li key={step.code} className="relative flex flex-col gap-3 px-5 py-6" style={{ opacity: 0 }}>
                {/* step connector arrow — desktop only */}
                {i < PIPELINE.length - 1 && (
                  <span
                    className="absolute right-0 top-1/2 z-10 hidden -translate-y-1/2 translate-x-[7px] border border-border bg-background px-1 font-mono text-[8px] text-text-muted sm:block"
                    aria-hidden="true"
                  >
                    {'>'}
                  </span>
                )}

                <div className="flex items-center gap-2">
                  <span className="font-mono text-[9px] text-accent-light">{step.index}</span>
                  <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-muted">{step.code}</span>
                </div>
                <p className="text-sm font-semibold text-text-primary">{step.label}</p>
                <p className="text-xs leading-5 text-text-secondary">{step.detail}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* ─── 4. DECISION PRINCIPLES ──────────────────────── */}
        <section
          className="mt-4 border border-border"
          style={{ opacity: 0 }}
        >
          <header className="border-b border-border px-7 py-5 sm:px-9">
            <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-text-muted">
              Cost function axes
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
              Decision principles
            </h2>
          </header>

          <ul
            ref={principlesRef}
            className="divide-y divide-border"
          >
            {PRINCIPLES.map((p) => (
              <li key={p.code} className="grid grid-cols-[3.5rem_6rem_minmax(0,1fr)] items-start gap-x-6 px-7 py-4 transition-colors duration-150 hover:bg-surface-secondary/30 sm:px-9" style={{ opacity: 0 }}>
                <span className="font-mono text-[9px] font-semibold text-accent-light">{p.code}</span>
                <span className="text-[11px] font-semibold uppercase tracking-wide text-text-primary">{p.label}</span>
                <span className="text-xs leading-5 text-text-secondary">{p.detail}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* ─── 5. SAFETY / SCOPE ───────────────────────────── */}
        <section
          className="mt-4 border border-warning/25 bg-warning-muted/15"
          style={{ opacity: 0 }}
        >
          <div className="grid lg:grid-cols-[auto_minmax(0,1fr)]">
            {/* left accent bar */}
            <div className="hidden w-1 bg-warning/50 lg:block" />

            <div className="px-7 py-8 sm:px-9">
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 bg-warning shadow-[0_0_7px_var(--color-warning)]" />
                <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-warning-light">
                  Scope declaration
                </p>
              </div>
              <h2
                className="mt-5 font-sans font-bold uppercase tracking-[-0.04em] text-text-primary"
                style={{ fontSize: 'clamp(1.2rem,2.8vw,1.9rem)', lineHeight: 1.05 }}
              >
                Simulation, not flight authority.
              </h2>
              <p className="mt-5 max-w-[68ch] text-sm leading-7 text-text-secondary">
                Aegis evaluates orbital scenarios, maneuver options, and coordination outcomes.
                It does not issue spacecraft commands, ingest live telemetry, or hold execution
                authority. Final operational authority remains with spacecraft operators and
                validated flight systems. Mission priority, fuel margin, and actuation constraints
                are simulated for the negotiation demonstration.
              </p>
            </div>
          </div>
        </section>

        {/* ─── 6. FINAL CTA ────────────────────────────────── */}
        <section
          className="mt-4 border border-border px-7 py-10 sm:px-9"
          style={{ opacity: 0 }}
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-text-muted">
                Ready to inspect
              </p>
              <p
                className="mt-3 font-sans font-bold uppercase tracking-[-0.04em] text-text-primary"
                style={{ fontSize: 'clamp(1.1rem,2.5vw,1.7rem)' }}
              >
                See the system in operation.
              </p>
            </div>
            <Link
              to="/monitor"
              className="inline-flex w-fit items-center gap-2.5 bg-accent px-6 py-3.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-white transition duration-200 hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:translate-y-px"
            >
              Open mission control
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-3 w-3">
                <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
          </div>
        </section>

      </div>
    </main>
  );
}
