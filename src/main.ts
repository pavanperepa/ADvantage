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
        theme: 'light',
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

// ---------------------------------------------------------------- connect hub
// Places the app chips on a circle and draws a line from each to the core.
function initHub() {
  const hub = $('[data-hub]');
  const svg = $<SVGSVGElement>('[data-hub-lines]');
  if (!hub || !svg) return;
  const apps = $$('.hub-apps li', hub);
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML =
    '<defs><linearGradient id="hub-grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7fb800"/><stop offset="1" stop-color="#0ea5e9"/></linearGradient></defs>';
  // A tighter ring on phones keeps the outer chips on screen.
  const radius = hub.clientWidth < 480 ? 35 : 42;
  apps.forEach((li, i) => {
    const angle = (i / apps.length) * Math.PI * 2 - Math.PI / 2;
    const x = 50 + Math.cos(angle) * radius;
    const y = 50 + Math.sin(angle) * radius;
    li.style.left = `${x}%`;
    li.style.top = `${y}%`;
    for (const cls of ['line-base', 'line-flow']) {
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', String(x));
      line.setAttribute('y1', String(y));
      line.setAttribute('x2', '50');
      line.setAttribute('y2', '50');
      line.setAttribute('class', cls);
      if (cls === 'line-flow') line.style.animationDelay = `${-i * 0.37}s`;
      svg.appendChild(line);
    }
  });
  // Take over the CSS centring so GSAP's scale tween keeps it on resize.
  gsap.set([...apps, $('.hub-core', hub)], { xPercent: -50, yPercent: -50, x: 0, y: 0 });
  if (reducedMotion) return;
  const tl = gsap.timeline({ scrollTrigger: { trigger: hub, start: 'top 75%', once: true } });
  tl.from('.hub-core', { scale: 0.6, opacity: 0, duration: 1, ease: 'back.out(1.6)' })
    .from(apps, { scale: 0.4, opacity: 0, duration: 0.7, ease: 'back.out(2)', stagger: 0.06 }, 0.2)
    .from('.line-flow', { opacity: 0, duration: 0.8, stagger: 0.05 }, 0.5);
}

// ---------------------------------------------------------------- strategy season
// Desktop: the section pins and the season scrolls sideways. Narrow screens
// keep a native, swipeable row.
function initSeason() {
  const section = $('[data-season]');
  const track = $('[data-season-track]');
  const progress = $('[data-season-progress]');
  if (!section || !track || reducedMotion) return;
  const mm = gsap.matchMedia();
  mm.add('(min-width: 1001px)', () => {
    const distance = () => Math.max(0, track.scrollWidth - window.innerWidth);
    gsap.to(track, {
      x: () => -distance(),
      ease: 'none',
      scrollTrigger: {
        trigger: section,
        start: 'top top',
        end: () => `+=${distance()}`,
        pin: true,
        scrub: 0.8,
        // Created after triggers further down the page; refresh it first so
        // their positions include the pin's added scroll distance.
        refreshPriority: 1,
        invalidateOnRefresh: true,
        onUpdate: (self) => {
          if (progress) progress.style.transform = `scaleX(${0.12 + self.progress * 0.88})`;
        },
      },
    });
  });
}

// ---------------------------------------------------------------- outcome calculator
function initCalc() {
  const root = $('[data-calc]');
  if (!root) return;
  const inputs = $$<HTMLInputElement>('[data-in]', root);
  const val = (k: string) => Number(inputs.find((i) => i.dataset.in === k)?.value ?? 0);
  const show = (k: string, text: string) => {
    const el = $(`[data-show="${k}"]`, root);
    if (el) el.textContent = text;
  };
  const money = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;
  const shown: Record<string, number> = {};
  const out = (k: string, n: number, fmt: (n: number) => string) => {
    const el = $(`[data-out="${k}"]`, root);
    if (!el) return;
    const from = shown[k] ?? n;
    shown[k] = n;
    if (reducedMotion || from === n) {
      el.textContent = fmt(n);
      return;
    }
    const state = { v: from };
    gsap.to(state, { v: n, duration: 0.5, ease: 'power2.out', onUpdate: () => (el.textContent = fmt(state.v)) });
  };
  const oneDecimal = (n: number) => (Math.round(n * 10) / 10).toLocaleString('en-US', { maximumFractionDigits: 1 });

  const update = () => {
    for (const i of inputs) {
      const pct = ((Number(i.value) - Number(i.min)) / (Number(i.max) - Number(i.min))) * 100;
      i.style.setProperty('--fill', `${pct}%`);
    }
    const inquiries = val('inquiries');
    const trial = val('trial') / 100;
    const enroll = val('enroll') / 100;
    const fee = val('fee');
    const months = val('months');
    show('inquiries', String(inquiries));
    show('trial', `${Math.round(trial * 100)}%`);
    show('enroll', `${Math.round(enroll * 100)}%`);
    show('fee', money(fee));
    show('months', String(months));

    const trials = inquiries * trial;
    const students = trials * enroll;
    out('trials', trials, oneDecimal);
    out('students', students, oneDecimal);
    out('monthly', students * fee, money);
    out('lifetime', students * fee * months, money);
    const lever = inquiries * 0.1 * enroll;
    out('lever', lever, oneDecimal);
    out('leverValue', lever * fee * months, money);
  };
  for (const i of inputs) i.addEventListener('input', update);
  update();
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

// ---------------------------------------------------------------- capabilities
// Desktop: a sticky mock screen switches panels as each capability scrolls
// past. Narrow screens: each capability carries its own copy of its panel.
function initCaps() {
  const root = $('[data-caps]');
  if (!root) return;
  const caps = $$('.cap', root);
  const panels = $$('.panel', root);
  const title = $('[data-screen-title]', root);

  for (const [i, cap] of caps.entries()) {
    const panel = panels.at(i);
    if (!panel) continue;
    const inline = document.createElement('div');
    inline.className = 'cap-inline';
    inline.setAttribute('aria-hidden', 'true');
    inline.innerHTML = `<div class="screen dark"><div class="screen-bar"><i></i><i></i><i></i><span>${panel.dataset.title}</span><em>Illustrative</em></div><div class="screen-body"></div></div>`;
    const copy = panel.cloneNode(true) as HTMLElement;
    copy.classList.remove('is-active');
    $('.screen-body', inline)!.appendChild(copy);
    $('.cap-body', cap)!.appendChild(inline);
    ScrollTrigger.create({
      trigger: inline,
      start: 'top 85%',
      once: true,
      onEnter: () => copy.classList.add('is-active'),
    });
  }

  let current = 0;
  const show = (i: number) => {
    caps.forEach((c, k) => c.classList.toggle('is-active', k === i));
    if (i === current) return;
    panels.at(current)?.classList.remove('is-active');
    panels.at(i)?.classList.add('is-active');
    if (title) title.textContent = panels.at(i)?.dataset.title ?? '';
    current = i;
  };
  show(0);

  for (const [i, cap] of caps.entries()) {
    ScrollTrigger.create({
      trigger: cap,
      start: 'top 55%',
      end: 'bottom 55%',
      onToggle: (self) => self.isActive && show(i),
    });
  }
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
    opacity: 0.55,
    theme: 'light',
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
    glow.classList.add('is-on');
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
initSteps();
initCaps();
initHub();
initSeason();
initCalc();
initCta();
initPointer();
initNav();
initFaq();
window.addEventListener('load', () => ScrollTrigger.refresh());
