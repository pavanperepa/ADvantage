// Small interaction effects in the manner of React Bits (reactbits.dev),
// written for this vanilla page on top of GSAP: ScrollVelocity, Magnet,
// SpotlightCard, CountUp and DecryptedText. Each one is a no-op under
// reduced motion and on touch-only devices where it would not be felt.
import gsap from 'gsap';
import type Lenis from 'lenis';

const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

// ScrollVelocity: a marquee that drifts on its own and speeds up with the
// scroll, flipping direction when the visitor scrolls back up.
export function scrollVelocity(track: HTMLElement, lenis: Lenis | null, baseSpeed = 40) {
  let x = 0;
  let dir = 1;
  let boost = 0;
  const half = () => track.scrollWidth / 2;
  gsap.ticker.add((_, delta) => {
    const v = lenis?.velocity ?? 0;
    if (Math.abs(v) > 0.2) dir = v > 0 ? 1 : -1;
    boost += (Math.min(Math.abs(v) * 6, 600) - boost) * 0.08;
    x -= dir * (baseSpeed + boost) * (delta / 1000);
    const w = half();
    if (w > 0) x = ((x % w) - w) % w;
    track.style.transform = `translate3d(${x.toFixed(2)}px,0,0)`;
  });
}

// Magnet: the element leans toward the cursor while it is near, then springs
// back.
export function magnet(el: HTMLElement, strength = 0.28, padding = 36) {
  if (!finePointer) return;
  const xTo = gsap.quickTo(el, 'x', { duration: 0.6, ease: 'power3.out' });
  const yTo = gsap.quickTo(el, 'y', { duration: 0.6, ease: 'power3.out' });
  let active = false;
  window.addEventListener(
    'pointermove',
    (e) => {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const near =
        e.clientX > r.left - padding &&
        e.clientX < r.right + padding &&
        e.clientY > r.top - padding &&
        e.clientY < r.bottom + padding;
      if (near) {
        active = true;
        xTo((e.clientX - cx) * strength);
        yTo((e.clientY - cy) * strength);
      } else if (active) {
        active = false;
        xTo(0);
        yTo(0);
      }
    },
    { passive: true },
  );
}

// SpotlightCard: a soft light follows the cursor across the surface. The
// light itself is drawn in CSS from --mx / --my.
export function spotlight(el: HTMLElement) {
  if (!finePointer) return;
  el.classList.add('has-spotlight');
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
  });
}

// CountUp: counts a number up from zero.
export function countUp(el: HTMLElement, to: number, duration = 1.2) {
  const state = { v: 0 };
  gsap.to(state, {
    v: to,
    duration,
    ease: 'power3.out',
    overwrite: true,
    onUpdate: () => {
      el.textContent = Math.round(state.v).toLocaleString('en-US');
    },
  });
}

// DecryptedText: the new text resolves out of scrambled characters.
export function decrypt(el: HTMLElement, text: string) {
  gsap.to(el, {
    duration: 0.7,
    ease: 'none',
    overwrite: true,
    scrambleText: { text, chars: 'lowerCase', speed: 0.6, revealDelay: 0.1 },
  });
}
