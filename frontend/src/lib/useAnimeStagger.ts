import { animate, stagger } from 'animejs';
import { type RefObject, useEffect } from 'react';

/**
 * Fires a staggered entry animation on the *direct children* of the element
 * referenced by `ref` whenever `deps` changes.
 *
 * Motion: translateY(+10px → 0) + opacity(0 → 1), staggered 55ms apart.
 * Respects `prefers-reduced-motion` — skips the animation entirely if set.
 *
 * @param ref     - Ref pointing to the container element
 * @param deps    - Dependency values — animation re-fires on every change
 * @param options - Optional overrides for duration / stagger delay / translateY
 */
export function useAnimeStagger(
  ref: RefObject<HTMLElement | null>,
  deps: readonly unknown[],
  options?: { duration?: number; staggerDelay?: number; translateY?: number },
): void {
  useEffect(() => {
    if (!ref.current) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const children = Array.from(ref.current.children) as HTMLElement[];
    if (children.length === 0) return;

    const { duration = 340, staggerDelay = 55, translateY = 10 } = options ?? {};

    animate(children, {
      opacity: [0, 1],
      translateY: [translateY, 0],
      duration,
      delay: stagger(staggerDelay),
      easing: 'easeOutCubic',
    });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * Fires a staggered entry animation on a specific *last child* only —
 * useful when a list grows one item at a time (e.g. incoming WS messages).
 *
 * Only the last `count` children are animated; previous ones are left alone.
 *
 * @param ref        - Ref pointing to the container element
 * @param itemCount  - Current number of items; animation fires when it changes
 * @param recentN    - How many tail items to animate (default 1)
 */
export function useAnimeAppend(
  ref: RefObject<HTMLElement | null>,
  itemCount: number,
  recentN = 1,
): void {
  useEffect(() => {
    if (!ref.current || itemCount === 0) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const children = Array.from(ref.current.children) as HTMLElement[];
    const targets = children.slice(-recentN);
    if (targets.length === 0) return;

    animate(targets, {
      opacity: [0, 1],
      translateY: [8, 0],
      duration: 280,
      delay: stagger(40),
      easing: 'easeOutCubic',
    });
  }, [itemCount]); // eslint-disable-line react-hooks/exhaustive-deps
}
