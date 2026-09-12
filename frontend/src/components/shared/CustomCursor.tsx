import { useEffect, useRef, useState } from 'react';

/**
 * Elements that trigger the cursor's "hover-lock" state (tighter brackets +
 * center dot). Matches code-standards.md's convention of naming interactive
 * regions rather than hooking every element — extend via data-cursor-hover
 * on anything that isn't naturally one of these but should still lock.
 */
const INTERACTIVE_SELECTOR =
  'button, a, [role="button"], input, select, textarea, .cluster-label, [data-cursor-hover]';

/** Priority-ordered semantic tone classes, reusing Badge.tsx's own status
 * vocabulary (bg-danger/-success/-warning-*) so a click ring's color always
 * matches whatever status color the clicked element already carries. */
const TONE_SELECTORS: Array<{ selector: string; color: string }> = [
  { selector: '[class*="danger"]', color: 'var(--color-danger)' },
  { selector: '[class*="success"]', color: 'var(--color-success)' },
  { selector: '[class*="warning"]', color: 'var(--color-warning)' },
];
const DEFAULT_TONE = 'var(--color-accent)';

function toneForTarget(target: EventTarget | null): string {
  if (!(target instanceof Element)) return DEFAULT_TONE;
  for (const { selector, color } of TONE_SELECTORS) {
    if (target.closest(selector)) return color;
  }
  return DEFAULT_TONE;
}

type Ping = { id: number; x: number; y: number; color: string };

/**
 * App-wide custom cursor: a small crosshair + four corner brackets (same
 * bracket language as GlobeHud's frame) with a faint slow-rotating ring,
 * a hover-lock state over interactive elements, and a short expanding-ring
 * pulse on click (visually the same grow-and-fade idea as the globe's
 * hazard/conjunction ring). Mounted once at the app root (App.tsx).
 */
export function CustomCursor() {
  const rootRef = useRef<HTMLDivElement>(null);
  const posRef = useRef({ x: -100, y: -100 });
  const rafRef = useRef<number | undefined>(undefined);
  const [enabled, setEnabled] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [pings, setPings] = useState<Ping[]>([]);
  const pingIdRef = useRef(0);

  // Only render on real pointer devices (mouse/trackpad) — never on
  // touch-only devices, and never override the native cursor there.
  useEffect(() => {
    const pointerFine = window.matchMedia('(pointer: fine)');
    const update = () => setEnabled(pointerFine.matches);
    update();
    pointerFine.addEventListener('change', update);
    return () => pointerFine.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const reduceMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(reduceMotionQuery.matches);
    update();
    reduceMotionQuery.addEventListener('change', update);
    return () => reduceMotionQuery.removeEventListener('change', update);
  }, []);

  // Hide the native cursor only while this component is actually active —
  // cleans itself up on unmount so no other consumer is affected.
  useEffect(() => {
    if (!enabled) return;
    document.documentElement.classList.add('custom-cursor-active');
    return () => document.documentElement.classList.remove('custom-cursor-active');
  }, [enabled]);

  // Pointer tracking: the pointermove listener only writes into a ref (no
  // React state, no re-render per move); a single rAF loop reads that ref
  // and applies the position directly via a CSS transform, which is the
  // cheapest possible way to keep 1:1 tracking with zero perceptible lag.
  useEffect(() => {
    if (!enabled) return;

    const onPointerMove = (event: PointerEvent) => {
      posRef.current = { x: event.clientX, y: event.clientY };
      const isHovering = event.target instanceof Element && event.target.closest(INTERACTIVE_SELECTOR) !== null;
      setHovering((prev) => (prev === isHovering ? prev : isHovering));
    };

    const tick = () => {
      const el = rootRef.current;
      if (el) {
        el.style.transform = `translate(${posRef.current.x}px, ${posRef.current.y}px)`;
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      if (rafRef.current !== undefined) cancelAnimationFrame(rafRef.current);
    };
  }, [enabled]);

  // Click pulse: skipped entirely under prefers-reduced-motion (falls back
  // to the static reticle with no extra animation), otherwise spawns a
  // short-lived ping that removes itself once its animation finishes.
  useEffect(() => {
    if (!enabled || reducedMotion) return;

    const onPointerDown = (event: PointerEvent) => {
      const id = (pingIdRef.current += 1);
      const color = toneForTarget(event.target);
      setPings((prev) => [...prev, { id, x: event.clientX, y: event.clientY, color }]);
      window.setTimeout(() => {
        setPings((prev) => prev.filter((p) => p.id !== id));
      }, 420);
    };

    window.addEventListener('pointerdown', onPointerDown, { passive: true });
    return () => window.removeEventListener('pointerdown', onPointerDown);
  }, [enabled, reducedMotion]);

  if (!enabled) return null;

  return (
    <>
      <div
        ref={rootRef}
        className={[
          'custom-cursor',
          hovering ? 'custom-cursor--hover' : '',
          reducedMotion ? 'custom-cursor--static' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        aria-hidden="true"
      >
        {!reducedMotion && <span className="custom-cursor__ring" />}
        <svg className="custom-cursor__brackets" viewBox="0 0 40 40" width="40" height="40">
          <path d="M2 10V2h8M30 2h8v8M38 30v8h-8M10 38H2v-8" />
        </svg>
        <span className="custom-cursor__dot" />
      </div>

      {pings.map((ping) => (
        <span
          key={ping.id}
          className="custom-cursor-ping"
          style={{ left: ping.x, top: ping.y, ['--cursor-ping-color' as string]: ping.color }}
          aria-hidden="true"
        />
      ))}
    </>
  );
}
