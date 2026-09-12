import { animate } from 'animejs';
import { type RefObject, useEffect } from 'react';

/**
 * Fires a single-element entry animation on the element referenced by `ref`
 * whenever `trigger` becomes truthy.
 *
 * Motion: translateY(+12px → 0) + opacity(0 → 1).
 * Respects `prefers-reduced-motion` — skips the animation entirely if set.
 */
export function useAnimeEntry(
  ref: RefObject<HTMLElement | null>,
  trigger: boolean,
  options?: { duration?: number; delay?: number; translateY?: number },
): void {
  useEffect(() => {
    if (!trigger || !ref.current) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const { duration = 380, delay = 0, translateY = 12 } = options ?? {};

    animate(ref.current, {
      opacity: [0, 1],
      translateY: [translateY, 0],
      duration,
      delay,
      easing: 'easeOutCubic',
    });
  }, [trigger]); // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * Fires a horizontal slide-in animation on the element referenced by `ref`
 * whenever `trigger` becomes truthy.
 *
 * Motion: translateX(+20px → 0) + opacity(0 → 1).
 * Respects `prefers-reduced-motion`.
 */
export function useAnimeSlideIn(
  ref: RefObject<HTMLElement | null>,
  trigger: boolean,
  options?: { duration?: number; delay?: number; translateX?: number },
): void {
  useEffect(() => {
    if (!trigger || !ref.current) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const { duration = 350, delay = 0, translateX = 20 } = options ?? {};

    animate(ref.current, {
      opacity: [0, 1],
      translateX: [translateX, 0],
      duration,
      delay,
      easing: 'easeOutCubic',
    });
  }, [trigger]); // eslint-disable-line react-hooks/exhaustive-deps
}
