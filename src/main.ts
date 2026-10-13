import './style.css';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
import { createOrbit } from './orbit';
import { site } from './config';

gsap.registerPlugin(ScrollTrigger);

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = window.matchMedia('(pointer: fine)').matches;
const $ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) => root.querySelector<T>(sel);
const $$ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) =>
  Array.from(root.querySelectorAll<T>(sel));

// ---------------------------------------------------------------- contact
function wireContact() {
  const href = site.bookingUrl || (site.email ? `mailto:${site.email}?subject=Free%20enrollment%20review` : '#contact');
  for (const a of $$<HTMLAnchorElement>('[data-booking]')) {
    a.href = href;
    if (site.bookingUrl) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
  }
  const lines = $('[data-contact-lines]');
  if (!lines) return;
  if (site.email) {
    lines.insertAdjacentHTML('beforeend', `<li><span>Email</span><a href="mailto:${site.email}">${site.email}</a></li>`);
  }
  if (site.whatsapp) {
    lines.insertAdjacentHTML(
      'beforeend',
      `<li><span>WhatsApp</span><a href="https://wa.me/${site.whatsapp}" target="_blank" rel="noopener">+${site.whatsapp}</a></li>`,
    );
  }
}

// ---------------------------------------------------------------- split headings into words
function splitWords(el: HTMLElement) {
  const walk = (node: Node) => {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === Node.TEXT_NODE) {
        const parts = (child.textContent ?? '').split(/(\s+)/);
        const frag = document.createDocumentFragment();
        for (const part of parts) {
          if (!part) continue;
          if (/^\s+$/.test(part)) {
            frag.appendChild(document.createTextNode(part));
          } else {
            const outer = document.createElement('span');
            outer.className = 'word';
            const inner = document.createElement('span');
            inner.className = 'word-inner';
            inner.textContent = part;
            outer.appendChild(inner);
            frag.appendChild(outer);
          }
        }
        child.replaceWith(frag);
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        walk(child);
      }
    }
  };
  walk(el);
  return $$('.word-inner', el);
}

// ---------------------------------------------------------------- smooth scroll
function initScroll() {
  if (reducedMotion) return null;
  const lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1 });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  for (const a of $$<HTMLAnchorElement>('a[href^="#"]')) {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href')!;
      if (id === '#' || id.length < 2) return;
      const target = $(id);
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target as HTMLElement, { offset: id === '#top' ? 0 : -72, duration: 1.4 });
    });
  }
  return lenis;
}

// ---------------------------------------------------------------- hero
function initHero() {
  const canvas = $<HTMLCanvasElement>('[data-hero-canvas]');
  const orbit = canvas
    ? createOrbit(canvas, {
        count: window.innerWidth < 700 ? 2600 : 5200,
        offsetX: 4.3,
        autoIntro: true,
        reducedMotion,
      })
    : null;

  const title = $('.hero-title')!;
  const words = splitWords(title);

  if (reducedMotion) return;

  const tl = gsap.timeline({ defaults: { ease: 'expo.out' } });
  tl.from('.nav', { y: -30, opacity: 0, duration: 1.2 }, 0.1)
    .from(words, { yPercent: 115, rotate: 4, duration: 1.3, stagger: 0.08 }, 0.25)
    .from('.hero-reveal', { y: 26, opacity: 0, duration: 1.1, stagger: 0.1 }, 0.6)
    .from('.scroll-cue', { opacity: 0, duration: 1 }, 1.4);

  if (orbit) {
    ScrollTrigger.create({
      trigger: '.hero',
      start: 'top top',
      end: 'bottom top',
      scrub: true,
      onUpdate: (self) => orbit.setSpread(self.progress * 0.9),
    });
  }
  gsap.to('.hero-inner', {
    yPercent: -18,
    opacity: 0.2,
    ease: 'none',
    scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true },
  });
}

// ---------------------------------------------------------------- section reveals
function initReveals() {
  const headings = $$('[data-split]').filter((el) => !el.classList.contains('hero-title'));
  for (const h of headings) {
    const words = splitWords(h);
    if (reducedMotion) continue;
    gsap.from(words, {
      yPercent: 110,
      duration: 1.1,
      ease: 'expo.out',
      stagger: 0.05,
      scrollTrigger: { trigger: h, start: 'top 85%' },
    });
  }
  if (reducedMotion) return;

  for (const el of $$('.reveal')) {
    gsap.from(el, {
      y: 24,
      opacity: 0,
      duration: 1,
      ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 88%' },
    });
  }

  gsap.set('.reveal-card', { opacity: 0 });
  ScrollTrigger.batch('.reveal-card', {
    start: 'top 90%',
    once: true,
    onEnter: (batch) =>
      gsap.fromTo(
        batch,
        { y: 48, opacity: 0, scale: 0.97 },
        { y: 0, opacity: 1, scale: 1, duration: 1.1, ease: 'expo.out', stagger: 0.09, overwrite: true },
      ),
  });
}

// ---------------------------------------------------------------- results
function initResults() {
  const counters = $$('[data-count-to]');
  const bars = $$('.bar-fill');
  if (reducedMotion) {
    for (const c of counters) c.textContent = Number(c.dataset.countTo).toFixed(Number(c.dataset.decimals ?? 0));
    for (const b of bars) b.style.transform = 'scaleX(1)';
    return;
  }
  for (const c of counters) {
    const from = Number(c.dataset.countFrom);
    const to = Number(c.dataset.countTo);
    const decimals = Number(c.dataset.decimals ?? 0);
    const state = { v: from };
    gsap.to(state, {
      v: to,
      duration: 2.2,
      ease: 'power4.inOut',
      scrollTrigger: { trigger: c, start: 'top 80%', once: true },
      onUpdate: () => {
        c.textContent = state.v.toFixed(decimals);
      },
    });
  }
  gsap.fromTo(
    bars,
    { scaleX: 0 },
    {
      scaleX: 1,
      duration: 1.8,
      ease: 'expo.out',
      stagger: 0.35,
      scrollTrigger: { trigger: '.bars', start: 'top 85%', once: true },
    },
  );
}

// ---------------------------------------------------------------- steps
function initSteps() {
  const progress = $('[data-steps-progress]');
  const steps = $$('.step');
  if (!progress || reducedMotion) {
    steps.forEach((s) => s.classList.add('is-active'));
    return;
  }
  gsap.fromTo(
    progress,
    { '--p': 0 },
    {
      '--p': 1,
      ease: 'none',
      scrollTrigger: {
        trigger: '[data-steps]',
        start: 'top 70%',
        end: 'bottom 55%',
        scrub: 0.6,
        onUpdate: (self) => {
          steps.forEach((s, i) => s.classList.toggle('is-active', self.progress >= i / steps.length + 0.02));
        },
      },
    },
  );
}

// ---------------------------------------------------------------- CTA orbit
function initCta() {
  const canvas = $<HTMLCanvasElement>('[data-cta-canvas]');
  if (!canvas) return;
  createOrbit(canvas, {
    count: window.innerWidth < 700 ? 1800 : 3600,
    offsetX: 0,
    autoIntro: false,
    reducedMotion,
    opacity: 0.5,
  });
}

// ---------------------------------------------------------------- pointer effects
function initPointer() {
  if (!finePointer || reducedMotion) return;

  const glow = $('.cursor-glow')!;
  const gx = gsap.quickTo(glow, 'x', { duration: 0.6, ease: 'power3' });
  const gy = gsap.quickTo(glow, 'y', { duration: 0.6, ease: 'power3' });
  window.addEventListener('pointermove', (e) => {
    gx(e.clientX);
    gy(e.clientY);
  });

  for (const btn of $$('.magnetic')) {
    const mx = gsap.quickTo(btn, 'x', { duration: 0.5, ease: 'elastic.out(1, 0.4)' });
    const my = gsap.quickTo(btn, 'y', { duration: 0.5, ease: 'elastic.out(1, 0.4)' });
    btn.addEventListener('pointermove', (e) => {
      const r = btn.getBoundingClientRect();
      mx((e.clientX - r.left - r.width / 2) * 0.25);
      my((e.clientY - r.top - r.height / 2) * 0.35);
    });
    btn.addEventListener('pointerleave', () => {
      mx(0);
      my(0);
    });
  }

  for (const card of $$('[data-tilt]')) {
    card.addEventListener('pointermove', (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      card.style.setProperty('--mx', `${px * 100}%`);
      card.style.setProperty('--my', `${py * 100}%`);
      gsap.to(card, {
        rotateY: (px - 0.5) * 7,
        rotateX: (0.5 - py) * 7,
        transformPerspective: 900,
        duration: 0.6,
        ease: 'power3.out',
      });
    });
    card.addEventListener('pointerleave', () => {
      gsap.to(card, { rotateX: 0, rotateY: 0, duration: 0.9, ease: 'elastic.out(1, 0.5)' });
    });
  }
}

// ---------------------------------------------------------------- nav
function initNav() {
  const nav = $('[data-nav]')!;
  ScrollTrigger.create({
    start: 40,
    end: 'max',
    onToggle: (self) => nav.classList.toggle('is-scrolled', self.isActive),
  });
  const links = $$<HTMLAnchorElement>('.nav-links a');
  for (const link of links) {
    const section = $(link.getAttribute('href')!);
    if (!section) continue;
    ScrollTrigger.create({
      trigger: section,
      start: 'top 50%',
      end: 'bottom 50%',
      onToggle: (self) => link.classList.toggle('is-current', self.isActive),
    });
  }
}

// ---------------------------------------------------------------- FAQ: one open at a time
function initFaq() {
  const items = $$<HTMLDetailsElement>('.faq-list details');
  for (const d of items) {
    d.addEventListener('toggle', () => {
      if (d.open) items.forEach((o) => o !== d && (o.open = false));
      ScrollTrigger.refresh();
    });
  }
}

if (reducedMotion) document.documentElement.classList.add('reduced-motion');
wireContact();
initScroll();
initHero();
initReveals();
initResults();
initSteps();
initCta();
initPointer();
initNav();
initFaq();
window.addEventListener('load', () => ScrollTrigger.refresh());
