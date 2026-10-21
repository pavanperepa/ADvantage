import './style.css';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';
import { ScrambleTextPlugin } from 'gsap/ScrambleTextPlugin';
import Lenis from 'lenis';
import {
  siFacebook,
  siGmail,
  siGoogledrive,
  siGooglemaps,
  siGooglemessages,
  siGooglesheets,
  siInstagram,
  siMeta,
  siWhatsapp,
  type SimpleIcon,
} from 'simple-icons';
import { createHero } from './hero';
import { countUp, decrypt, magnet, scrollVelocity, spotlight } from './bits';
import { site } from './config';
import type { NetHandle } from './net';

gsap.registerPlugin(ScrollTrigger, SplitText, DrawSVGPlugin, ScrambleTextPlugin);

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) => root.querySelector<T>(sel);
const $$ = <T extends Element = HTMLElement>(sel: string, root: ParentNode = document) =>
  Array.from(root.querySelectorAll<T>(sel));
const EASE = 'expo.out';

// ---------------------------------------------------------------- contact
function wireContact() {
  const href = site.bookingUrl || (site.email ? `mailto:${site.email}?subject=Free%20growth%20review` : '#contact');
  for (const a of $$<HTMLAnchorElement>('[data-booking]')) {
    a.href = href;
    if (site.bookingUrl) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
  }
  const lines = $('[data-contact-lines]');
  if (!lines) return;
  const add = (label: string, text: string, url: string, external = false) => {
    const li = document.createElement('li');
    const span = document.createElement('span');
    span.textContent = label;
    const a = document.createElement('a');
    a.href = url;
    a.textContent = text;
    if (external) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
    li.append(span, a);
    lines.appendChild(li);
  };
  if (site.email) add('Email', site.email, `mailto:${site.email}`);
  if (site.whatsapp) add('WhatsApp', `+${site.whatsapp}`, `https://wa.me/${site.whatsapp}`, true);
}

// ---------------------------------------------------------------- smooth scroll
function initScroll(): Lenis | null {
  if (reducedMotion) return null;
  const lenis = new Lenis({ lerp: 0.1, touchMultiplier: 1.4 });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  for (const a of $$<HTMLAnchorElement>('a[href^="#"]')) {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href')!;
      const target = id.length > 1 ? $(id) : null;
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target, { offset: id === '#top' ? 0 : -76, duration: 1.4 });
    });
  }
  return lenis;
}

// ---------------------------------------------------------------- React Bits-style effects
function initBits(lenis: Lenis | null) {
  if (reducedMotion) return;
  const track = $('[data-velocity]');
  if (track) {
    track.classList.add('is-driven');
    scrollVelocity(track, lenis);
  }
  for (const el of $$('[data-magnet]')) magnet(el);
  for (const el of $$('[data-spotlight]')) spotlight(el);
}

// ---------------------------------------------------------------- entrances
// Headings rise line by line, then their text and pictures follow, staggered.
function initEntrances() {
  if (reducedMotion) return;
  for (const el of $$('[data-split]')) {
    const split = SplitText.create(el, { type: 'lines', mask: 'lines', linesClass: 'split-line-inner' });
    for (const mask of split.masks) (mask as HTMLElement).classList.add('split-line');
    const hero = el.classList.contains('hero-title');
    gsap.from(split.lines, {
      yPercent: 110,
      duration: hero ? 1.3 : 1.05,
      ease: EASE,
      stagger: 0.09,
      delay: hero ? 0.15 : 0,
      scrollTrigger: hero ? undefined : { trigger: el, start: 'top 85%' },
    });
  }

  const hero = $$('.hero [data-rise]');
  gsap.from(hero, { y: 24, opacity: 0, duration: 1.1, ease: EASE, stagger: 0.08, delay: 0.55 });
  gsap.from('.nav-inner > *', { y: -16, opacity: 0, duration: 1, ease: EASE, stagger: 0.07 });

  const rest = $$('[data-rise]').filter((el) => !el.closest('.hero'));
  gsap.set(rest, { y: 24, opacity: 0 });
  ScrollTrigger.batch(rest, {
    start: 'top 88%',
    once: true,
    onEnter: (batch) => gsap.to(batch, { y: 0, opacity: 1, duration: 1, ease: EASE, stagger: 0.075, overwrite: true }),
  });
}

// ---------------------------------------------------------------- hero
function initHero() {
  const canvas = $<HTMLCanvasElement>('[data-hero-canvas]');
  if (!canvas) return;
  const hero = createHero(canvas, { count: window.innerWidth < 700 ? 2200 : 4200, reducedMotion });
  if (!hero || reducedMotion) return;
  ScrollTrigger.create({
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: true,
    onUpdate: (self) => hero.setSpread(self.progress * 0.8),
  });
  gsap.to('.hero-inner', {
    y: -80,
    opacity: 0.15,
    ease: 'none',
    scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true },
  });
}

// ---------------------------------------------------------------- connect hub
const APPS: { icon: SimpleIcon; label: string }[] = [
  { icon: siMeta, label: 'Meta Ads' },
  { icon: siInstagram, label: 'Instagram' },
  { icon: siFacebook, label: 'Facebook' },
  { icon: siGooglemessages, label: 'Text messages' },
  { icon: siWhatsapp, label: 'WhatsApp' },
  { icon: siGmail, label: 'Email' },
  { icon: siGoogledrive, label: 'Your footage' },
  { icon: siGooglesheets, label: 'Lead lists' },
  { icon: siGooglemaps, label: 'Banner spots' },
];

function initHub() {
  const hub = $('[data-hub]');
  const svg = $<SVGSVGElement>('[data-hub-lines]');
  const list = $('[data-hub-apps]');
  if (!hub || !svg || !list) return;
  const ns = 'http://www.w3.org/2000/svg';
  const radius = hub.clientWidth < 480 ? 38 : 41;
  const flows: SVGLineElement[] = [];
  const items: HTMLLIElement[] = [];

  APPS.forEach(({ icon, label }, i) => {
    const angle = (i / APPS.length) * Math.PI * 2 - Math.PI / 2;
    const x = 50 + Math.cos(angle) * radius;
    const y = 50 + Math.sin(angle) * radius;

    const li = document.createElement('li');
    li.style.left = `${x}%`;
    li.style.top = `${y}%`;
    const disc = document.createElement('span');
    disc.className = 'hub-icon';
    const iconSvg = document.createElementNS(ns, 'svg');
    iconSvg.setAttribute('viewBox', '0 0 24 24');
    iconSvg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', icon.path);
    path.setAttribute('fill', `#${icon.hex}`);
    iconSvg.appendChild(path);
    disc.appendChild(iconSvg);
    const name = document.createElement('span');
    name.textContent = label;
    li.append(disc, name);
    list.appendChild(li);
    items.push(li);

    for (const cls of ['line-base', 'line-flow']) {
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', String(x));
      line.setAttribute('y1', String(y));
      line.setAttribute('x2', '50');
      line.setAttribute('y2', '50');
      line.setAttribute('class', cls);
      if (cls === 'line-flow') {
        line.style.animationDelay = `${-i * 0.29}s`;
        flows.push(line);
      }
      svg.appendChild(line);
    }
  });

  if (reducedMotion) return;
  const bases = $$<SVGLineElement>('.line-base', svg);
  const tl = gsap.timeline({ scrollTrigger: { trigger: hub, start: 'top 75%', once: true } });
  tl.from('.hub-core', { scale: 0.4, opacity: 0, duration: 1, ease: 'back.out(1.7)' })
    .from(bases, { drawSVG: '100% 100%', duration: 0.9, ease: 'power2.out', stagger: 0.05 }, 0.2)
    .from(items, { scale: 0.5, opacity: 0, duration: 0.7, ease: 'back.out(2)', stagger: 0.05 }, 0.3)
    .from(flows, { opacity: 0, duration: 0.6, stagger: 0.04 }, 0.9);
}

// ---------------------------------------------------------------- capabilities
// Desktop: a sticky product screen switches panels as each job scrolls past.
// Narrow screens: each job carries its own copy of its panel.
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
    const screen = document.createElement('div');
    screen.className = 'screen';
    const bar = document.createElement('div');
    bar.className = 'screen-bar';
    bar.innerHTML = '<i></i><i></i><i></i><span></span><em>Illustrative</em>';
    $('span', bar)!.textContent = panel.dataset.title ?? '';
    const body = document.createElement('div');
    body.className = 'screen-body';
    const copy = panel.cloneNode(true) as HTMLElement;
    copy.classList.remove('is-active');
    body.appendChild(copy);
    screen.append(bar, body);
    inline.appendChild(screen);
    cap.appendChild(inline);
    ScrollTrigger.create({
      trigger: inline,
      start: 'top 85%',
      once: true,
      onEnter: () => {
        copy.classList.add('is-active');
        counts(copy);
      },
    });
  }

  const counts = (panel: HTMLElement | undefined) => {
    if (!panel || reducedMotion) return;
    for (const b of $$('[data-count]', panel)) countUp(b, Number(b.dataset.count));
  };

  let current = 0;
  const show = (i: number) => {
    caps.forEach((c, k) => c.classList.toggle('is-active', k === i));
    if (i === current) return;
    panels.at(current)?.classList.remove('is-active');
    panels.at(i)?.classList.add('is-active');
    const next = panels.at(i)?.dataset.title ?? '';
    if (title) {
      if (reducedMotion) title.textContent = next;
      else decrypt(title, next);
    }
    counts(panels.at(i));
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

// ---------------------------------------------------------------- strategy season
function initSeason() {
  const section = $('[data-season]');
  const track = $('[data-season-track]');
  const progress = $('[data-season-progress]');
  if (!section || !track || reducedMotion) return;
  initNet(section);
  gsap.matchMedia().add('(min-width: 1001px)', () => {
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
          if (progress) progress.style.transform = `scaleX(${0.1 + self.progress * 0.9})`;
        },
      },
    });
  });
}

// The Vanta net loads on approach, runs only while the section is on screen
// and is skipped on small screens, where the cards cover it anyway.
function initNet(section: HTMLElement) {
  const host = $('[data-net]', section);
  if (!host || window.innerWidth < 700) return;
  let net: NetHandle | null = null;
  let loading = false;
  new IntersectionObserver(
    async ([entry]) => {
      if (entry.isIntersecting && !net && !loading) {
        loading = true;
        const { createNet } = await import('./net');
        net = createNet(host);
        loading = false;
        if (net) gsap.fromTo(host, { opacity: 0 }, { opacity: 1, duration: 1.6, ease: 'power2.out' });
      } else if (!entry.isIntersecting && net) {
        net.destroy();
        net = null;
      }
    },
    { rootMargin: '300px 0px' },
  ).observe(section);
}

// ---------------------------------------------------------------- outcomes: calculator + chart
const money = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;
const compact = (n: number) =>
  n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `$${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K` : `$${Math.round(n)}`;
const oneDecimal = (n: number) => (Math.round(n * 10) / 10).toLocaleString('en-US', { maximumFractionDigits: 1 });

function niceMax(v: number) {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * mag * 4 >= v)! * mag;
  return step * 4;
}

interface Series {
  base: number[];
  lift: number[];
}

function initOutcomes() {
  const root = $('[data-calc]');
  const plot = $('[data-chart-plot]');
  const tableHost = $('[data-chart-table]');
  if (!root || !plot || !tableHost) return;
  const inputs = $$<HTMLInputElement>('[data-in]', root);
  const val = (k: string) => Number(inputs.find((i) => i.dataset.in === k)?.value ?? 0);
  const setText = (sel: string, text: string) => {
    const el = $(sel, root);
    if (el) el.textContent = text;
  };

  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('role', 'img');
  plot.appendChild(svg);
  const tip = document.createElement('div');
  tip.className = 'chart-tip';
  plot.appendChild(tip);
  plot.tabIndex = 0;

  let shown: Series = { base: Array(12).fill(0), lift: Array(12).fill(0) };
  let target: Series = shown;
  let drawn = false;
  let hoverIndex = -1;

  const compute = (): Series & { customers: number; perCustomer: number; liftYear: number } => {
    const inquiries = val('inquiries');
    const conv = val('conv') / 100;
    const fee = val('spend');
    const stay = val('visits');
    const base: number[] = [];
    const lift: number[] = [];
    const cBase = inquiries * conv;
    const cLift = inquiries * Math.min(conv + 0.05, 1);
    for (let m = 1; m <= 12; m++) {
      // Each month's new students pay the fee every month until they leave.
      let months = 0;
      for (let j = 1; j <= m; j++) months += Math.min(m - j + 1, stay);
      base.push(cBase * fee * months);
      lift.push(cLift * fee * months);
    }
    return { base, lift, customers: cBase, perCustomer: fee * stay, liftYear: lift[11] - base[11] };
  };

  const render = (s: Series) => {
    const w = plot.clientWidth;
    const h = plot.clientHeight;
    const pad = { l: 52, r: w < 520 ? 64 : 88, t: 12, b: 30 };
    const iw = Math.max(10, w - pad.l - pad.r);
    const ih = Math.max(10, h - pad.t - pad.b);
    const max = niceMax(Math.max(...target.lift, 1));
    const X = (i: number) => pad.l + (i / 11) * iw;
    const Y = (v: number) => pad.t + ih - (v / max) * ih;
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute(
      'aria-label',
      `Fees from new students over 12 months: ${money(target.base[11])} with your numbers today, ${money(target.lift[11])} with 5 points more enrolment.`,
    );

    const ticks = [0, 1, 2, 3, 4].map((k) => (max / 4) * k);
    const months = [0, 2, 5, 8, 11];
    const line = (arr: number[]) => arr.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join('');
    const area = `${line(s.lift)}L${X(11)},${Y(0)}L${X(0)},${Y(0)}Z`;

    const endBase = Y(s.base[11]);
    let endLift = Y(s.lift[11]);
    if (endBase - endLift < 18) endLift = endBase - 18;

    svg.innerHTML = `
      <g class="grid">${ticks.map((t) => `<line x1="${pad.l}" x2="${pad.l + iw}" y1="${Y(t)}" y2="${Y(t)}"/>`).join('')}</g>
      <g class="axis">
        ${ticks.map((t) => `<text x="${pad.l - 10}" y="${Y(t) + 4}" text-anchor="end">${compact(t)}</text>`).join('')}
        ${months.map((m) => `<text x="${X(m)}" y="${h - 6}" text-anchor="middle">${m === 0 ? 'Month 1' : m + 1}</text>`).join('')}
      </g>
      <path class="area" d="${area}" fill="var(--series-lift)"/>
      <path class="series series-base" d="${line(s.base)}" stroke="var(--series-base)"/>
      <path class="series series-lift" d="${line(s.lift)}" stroke="var(--series-lift)"/>
      <line class="crosshair" x1="0" x2="0" y1="${pad.t}" y2="${pad.t + ih}"/>
      <g class="dots"></g>
      <text class="end-label" x="${X(11) + 10}" y="${endLift + 4}">${compact(s.lift[11])}</text>
      <text class="end-label" x="${X(11) + 10}" y="${endBase + 4}">${compact(s.base[11])}</text>
    `;
    // End markers with a ring in the surface colour.
    const dots = svg.querySelector('.dots')!;
    for (const [arr, color] of [
      [s.base, 'var(--series-base)'],
      [s.lift, 'var(--series-lift)'],
    ] as const) {
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', String(X(11)));
      c.setAttribute('cy', String(Y(arr[11])));
      c.setAttribute('r', '5');
      c.setAttribute('fill', color);
      c.setAttribute('stroke', 'var(--tone)');
      c.setAttribute('stroke-width', '2');
      dots.appendChild(c);
    }
    if (hoverIndex >= 0) showTip(hoverIndex, X, pad.t, ih);
    return { X, pad, ih };
  };

  const showTip = (i: number, X: (i: number) => number, top: number, ih: number) => {
    const cross = svg.querySelector<SVGLineElement>('.crosshair');
    if (cross) {
      cross.setAttribute('x1', String(X(i)));
      cross.setAttribute('x2', String(X(i)));
      cross.style.opacity = '1';
    }
    tip.replaceChildren();
    const head = document.createElement('p');
    head.className = 'tip-head';
    head.textContent = `By month ${i + 1}`;
    tip.appendChild(head);
    for (const [key, label, color] of [
      ['lift', 'With 5 points more enrolment', 'var(--series-lift)'],
      ['base', 'Your numbers today', 'var(--series-base)'],
    ] as const) {
      const row = document.createElement('p');
      const k = document.createElement('i');
      k.style.background = color;
      const b = document.createElement('b');
      b.textContent = money(target[key][i]);
      const span = document.createElement('span');
      span.textContent = label;
      row.append(k, b, span);
      tip.appendChild(row);
    }
    const x = X(i);
    const left = x > plot.clientWidth / 2 ? x - tip.offsetWidth - 12 : x + 12;
    tip.style.left = `${left}px`;
    tip.style.top = `${top + ih * 0.05}px`;
    tip.classList.add('is-on');
  };

  const hide = () => {
    hoverIndex = -1;
    tip.classList.remove('is-on');
    const cross = svg.querySelector<SVGLineElement>('.crosshair');
    if (cross) cross.style.opacity = '0';
  };

  const indexAt = (clientX: number) => {
    const rect = plot.getBoundingClientRect();
    const w = plot.clientWidth;
    const padL = 52;
    const padR = w < 520 ? 64 : 88;
    const t = (clientX - rect.left - padL) / (w - padL - padR);
    return Math.max(0, Math.min(11, Math.round(t * 11)));
  };

  plot.addEventListener('pointermove', (e) => {
    hoverIndex = indexAt(e.clientX);
    render(shown);
  });
  plot.addEventListener('pointerleave', hide);
  plot.addEventListener('focus', () => {
    hoverIndex = 11;
    render(shown);
  });
  plot.addEventListener('blur', hide);
  plot.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    hoverIndex = Math.max(0, Math.min(11, (hoverIndex < 0 ? 11 : hoverIndex) + (e.key === 'ArrowRight' ? 1 : -1)));
    render(shown);
  });

  const renderTable = (s: Series) => {
    const table = document.createElement('table');
    const thead = table.createTHead().insertRow();
    for (const h of ['Month', 'Your numbers today', 'With 5 points more']) {
      const th = document.createElement('th');
      th.textContent = h;
      thead.appendChild(th);
    }
    const body = table.createTBody();
    s.base.forEach((v, i) => {
      const row = body.insertRow();
      row.insertCell().textContent = String(i + 1);
      row.insertCell().textContent = money(v);
      row.insertCell().textContent = money(s.lift[i]);
    });
    tableHost.replaceChildren(table);
  };

  const animateTo = (next: Series) => {
    const from = shown;
    target = next;
    if (reducedMotion || !drawn) {
      shown = next;
      render(shown);
      return;
    }
    const state = { t: 0 };
    gsap.to(state, {
      t: 1,
      duration: 0.55,
      ease: 'power3.out',
      overwrite: true,
      onUpdate: () => {
        shown = {
          base: from.base.map((v, i) => v + (next.base[i] - v) * state.t),
          lift: from.lift.map((v, i) => v + (next.lift[i] - v) * state.t),
        };
        render(shown);
      },
    });
  };

  const update = () => {
    for (const i of inputs) {
      const pct = ((Number(i.value) - Number(i.min)) / (Number(i.max) - Number(i.min))) * 100;
      i.style.setProperty('--fill', `${pct}%`);
    }
    setText('[data-show="inquiries"]', String(val('inquiries')));
    setText('[data-show="conv"]', `${val('conv')}%`);
    setText('[data-show="spend"]', money(val('spend')));
    setText('[data-show="visits"]', String(val('visits')));
    const r = compute();
    setText('[data-out="customers"]', oneDecimal(r.customers));
    setText('[data-out="perCustomer"]', money(r.perCustomer));
    const lever = $('[data-out="liftYear"]');
    if (lever) lever.textContent = money(r.liftYear);
    animateTo({ base: r.base, lift: r.lift });
    renderTable(r);
  };
  for (const i of inputs) i.addEventListener('input', update);
  update();
  new ResizeObserver(() => render(shown)).observe(plot);

  if (reducedMotion) {
    drawn = true;
    return;
  }
  ScrollTrigger.create({
    trigger: plot,
    start: 'top 80%',
    once: true,
    onEnter: () => {
      drawn = true;
      render(shown);
      gsap.from(svg.querySelectorAll('.series'), { drawSVG: '0%', duration: 1.6, ease: 'power2.inOut', stagger: 0.2 });
      gsap.from(svg.querySelectorAll('.area, .end-label, .dots circle'), { opacity: 0, duration: 0.6, delay: 1.2 });
    },
  });
}

// ---------------------------------------------------------------- nav
function initNav() {
  const nav = $('[data-nav]')!;
  // A plain scroll check: a ScrollTrigger ending at 'max' turns off at the
  // very bottom of the page and drops the bar's background there.
  const setScrolled = () => nav.classList.toggle('is-scrolled', window.scrollY > 40);
  window.addEventListener('scroll', setScrolled, { passive: true });
  setScrolled();
  for (const link of $$<HTMLAnchorElement>('.nav-links a')) {
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

wireContact();
const lenis = initScroll();
initBits(lenis);
initHero();
initEntrances();
initHub();
initCaps();
initSeason();
initOutcomes();
initNav();
initFaq();
window.addEventListener('load', () => ScrollTrigger.refresh());
