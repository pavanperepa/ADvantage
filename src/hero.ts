import * as THREE from 'three';

// The hero's signature move. The business sits at the centre; a faint crowd
// (the whole market) surrounds it. Every few seconds the business sends its
// work out as a pulse. As the pulse passes, the right people light up and
// travel in to orbit the business: they become customers. Each wave reaches a
// different part of the crowd, and customers who arrived earlier settle into
// the business as new ones come in.

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uSize;
  uniform float uPixelRatio;
  uniform float uPeriod;
  uniform float uCycle;
  uniform float uPulseSpeed;
  uniform float uSpread;
  uniform float uFadeLeft;
  uniform float uFadeLow;

  attribute vec3 aPos;
  attribute float aMatch;
  attribute float aSlot;
  attribute float aRadius;
  attribute float aTilt;
  attribute float aAngle;
  attribute float aSpeed;
  attribute float aSeed;
  attribute float aSize;

  varying float vAlpha;
  varying float vLit;

  vec3 rotX(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x, c * p.y - s * p.z, s * p.y + c * p.z); }
  vec3 rotZ(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x - s * p.y, s * p.x + c * p.y, p.z); }

  void main() {
    vec3 crowd = aPos + 0.14 * vec3(
      sin(uTime * 0.23 + aSeed * 21.0),
      cos(uTime * 0.19 + aSeed * 13.0),
      sin(uTime * 0.17 + aSeed * 7.0)
    );
    vec3 p = crowd;
    float alpha = 0.1 + 0.14 * aSeed;
    float lit = 0.0;
    float size = aSize;

    if (aMatch > 0.5) {
      float since = uTime - aSlot * uPeriod - 0.6;
      float tau = since < 0.0 ? 0.0 : mod(since, uCycle);
      float started = step(0.0, since);
      float firstPass = step(since, uCycle);

      float hit = length(aPos) / uPulseSpeed;
      lit = smoothstep(hit, hit + 0.3, tau) * started;

      float t = clamp((tau - hit - 0.45) / 2.6, 0.0, 1.0) * started;
      float e = t * t * (3.0 - 2.0 * t);

      float ang = aAngle + uTime * aSpeed;
      vec3 ring = vec3(cos(ang) * aRadius, sin(ang * 2.0 + aSeed * 6.0) * 0.06 * aRadius, sin(ang) * aRadius);
      ring = rotZ(rotX(ring, aTilt), aTilt * 0.5);

      // Arc in rather than slide: lift the path while travelling.
      vec3 travel = mix(crowd, ring, e);
      travel.y += sin(e * 3.14159) * 0.9 * (aSeed - 0.5);
      p = travel;

      // Late in the cycle the customer settles into the business; the next
      // cycle starts it back in the crowd, fading in.
      float settle = smoothstep(uCycle - 1.4, uCycle - 0.2, tau) * started;
      p = mix(p, vec3(0.0), settle);
      float fadeIn = mix(smoothstep(0.0, 0.7, tau), 1.0, firstPass);

      alpha = mix(alpha, 1.0, lit) * fadeIn * (1.0 - settle);
      size = mix(aSize, aSize * 1.35, lit);
    }

    p *= 1.0 + uSpread;
    vec4 world = modelMatrix * vec4(p, 1.0);
    // Keep the crowd quiet behind the headline.
    float quiet = mix(1.0, smoothstep(-7.0, -1.0, world.x), uFadeLeft) * mix(1.0, smoothstep(-4.5, 0.5, world.y), uFadeLow);
    alpha *= quiet;

    vec4 mv = viewMatrix * world;
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize * size * uPixelRatio / -mv.z;
    vAlpha = alpha;
    vLit = lit;
  }
`;

const fragmentShader = /* glsl */ `
  uniform vec3 uInk;
  uniform vec3 uAccent;
  varying float vAlpha;
  varying float vLit;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    // Crowd: a soft ink dot. Lit: an accent dot with an ink rim, so it holds
    // up on the light ground.
    float soft = smoothstep(0.5, 0.15, d);
    float disc = smoothstep(0.5, 0.45, d);
    float rim = smoothstep(0.34, 0.38, d);
    vec3 litColor = mix(uAccent, uInk, rim);
    vec3 col = mix(uInk, litColor, vLit);
    float a = mix(soft, disc, vLit);
    gl_FragColor = vec4(col, a * vAlpha);
  }
`;

export interface HeroOptions {
  count: number;
  reducedMotion: boolean;
}

function rand(a: number, b: number) {
  return a + Math.random() * (b - a);
}

export function createHero(canvas: HTMLCanvasElement, opts: HeroOptions) {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch {
    return null;
  }
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0, 0, 16);

  const rig = new THREE.Group();
  const system = new THREE.Group();
  system.rotation.x = 0.38;
  rig.add(system);
  scene.add(rig);

  const PERIOD = 4;
  const SLOTS = 3;
  const CYCLE = PERIOD * SLOTS;

  const n = opts.count;
  const pos = new Float32Array(n * 3);
  const match = new Float32Array(n);
  const slot = new Float32Array(n);
  const radius = new Float32Array(n);
  const tilt = new Float32Array(n);
  const angle = new Float32Array(n);
  const speed = new Float32Array(n);
  const seed = new Float32Array(n);
  const size = new Float32Array(n);

  for (let i = 0; i < n; i++) {
    // The market: a wide, flattened shell around the business.
    const r = 3.4 + Math.pow(Math.random(), 0.7) * 10;
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(rand(-1, 1));
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[i * 3 + 1] = r * Math.cos(ph) * 0.5;
    pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th) * 0.8;

    // Only a small share of the market is the right audience.
    match[i] = Math.random() < 0.06 ? 1 : 0;
    slot[i] = Math.floor(Math.random() * SLOTS);
    const inner = Math.random() < 0.5;
    radius[i] = (inner ? 1.7 : 2.6) + (Math.random() - 0.5) * 0.35;
    tilt[i] = inner ? 0.25 : -0.35;
    angle[i] = Math.random() * Math.PI * 2;
    speed[i] = (inner ? 0.32 : 0.22) * (0.85 + Math.random() * 0.3);
    seed[i] = Math.random();
    size[i] = match[i] ? rand(16, 22) : rand(10, 20);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  geo.setAttribute('aPos', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aMatch', new THREE.BufferAttribute(match, 1));
  geo.setAttribute('aSlot', new THREE.BufferAttribute(slot, 1));
  geo.setAttribute('aRadius', new THREE.BufferAttribute(radius, 1));
  geo.setAttribute('aTilt', new THREE.BufferAttribute(tilt, 1));
  geo.setAttribute('aAngle', new THREE.BufferAttribute(angle, 1));
  geo.setAttribute('aSpeed', new THREE.BufferAttribute(speed, 1));
  geo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 40);

  const uniforms = {
    uTime: { value: 0 },
    uSize: { value: 9 },
    uPixelRatio: { value: 1 },
    uPeriod: { value: PERIOD },
    uCycle: { value: CYCLE },
    uPulseSpeed: { value: 5.5 },
    uSpread: { value: 0 },
    uFadeLeft: { value: 1 },
    uFadeLow: { value: 0 },
    uInk: { value: new THREE.Color('#121316') },
    uAccent: { value: new THREE.Color('#c5f03c') },
  };

  system.add(
    new THREE.Points(
      geo,
      new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true, depthWrite: false }),
    ),
  );

  // The business: an ink disc with an accent ring that kicks on every pulse.
  const core = new THREE.Group();
  const coreDisc = new THREE.Mesh(new THREE.CircleGeometry(0.5, 64), new THREE.MeshBasicMaterial({ color: 0x121316 }));
  const coreRing = new THREE.Mesh(
    new THREE.RingGeometry(0.62, 0.74, 64),
    new THREE.MeshBasicMaterial({ color: 0xc5f03c, transparent: true }),
  );
  core.add(coreRing, coreDisc);
  rig.add(core);

  // Pulses: the work going out. Rings face the camera and widen at the same
  // speed the crowd lights up.
  const pulses = Array.from({ length: 3 }, () => {
    const mesh = new THREE.Mesh(
      new THREE.RingGeometry(0.985, 1, 160),
      new THREE.MeshBasicMaterial({ color: 0x121316, transparent: true, opacity: 0, depthWrite: false }),
    );
    rig.add(mesh);
    return mesh;
  });

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(1, rect.width);
    const h = Math.max(1, rect.height);
    const pr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(pr);
    renderer.setSize(w, h, false);
    uniforms.uPixelRatio.value = pr;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const wide = w > 960;
    rig.position.set(wide ? 4.2 : 0, wide ? -0.2 : 3.6, 0);
    rig.scale.setScalar(wide ? 1 : w < 640 ? 0.62 : 0.8);
    uniforms.uFadeLeft.value = wide ? 1 : 0;
    uniforms.uFadeLow.value = wide ? 0 : 1;
    uniforms.uSize.value = w < 640 ? 7 : 9;
  }
  resize();
  new ResizeObserver(resize).observe(canvas);

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener(
    'pointermove',
    (e) => {
      pointer.tx = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.ty = (e.clientY / window.innerHeight) * 2 - 1;
    },
    { passive: true },
  );

  function draw(time: number) {
    uniforms.uTime.value = time;
    pointer.x += (pointer.tx - pointer.x) * 0.04;
    pointer.y += (pointer.ty - pointer.y) * 0.04;
    system.rotation.y = time * 0.04 + pointer.x * 0.3;
    system.rotation.x = 0.38 + pointer.y * 0.12;

    const since = time - 0.6;
    for (const [k, mesh] of pulses.entries()) {
      // Pulse k fires at 0.6 + (m * 3 + k) * PERIOD.
      const age = since < 0 ? -1 : ((since - k * PERIOD) % CYCLE + CYCLE) % CYCLE;
      const mat = mesh.material as THREE.MeshBasicMaterial;
      if (since < k * PERIOD || age < 0 || age > 2.6) {
        mat.opacity = 0;
        continue;
      }
      mesh.scale.setScalar(0.8 + age * uniforms.uPulseSpeed.value * 0.95);
      mat.opacity = 0.45 * (1 - age / 2.6);
    }
    const kick = ((since % PERIOD) + PERIOD) % PERIOD;
    coreRing.scale.setScalar(1 + Math.exp(-kick * 3) * 0.6);
    renderer.render(scene, camera);
  }

  if (opts.reducedMotion) {
    draw(7.2);
    new ResizeObserver(() => draw(7.2)).observe(canvas);
    return { setSpread() {} };
  }

  let visible = true;
  let running = false;
  const clock = new THREE.Clock();
  let elapsed = 0;
  function frame() {
    if (!visible) {
      running = false;
      return;
    }
    elapsed += Math.min(clock.getDelta(), 0.05);
    draw(elapsed);
    requestAnimationFrame(frame);
  }
  function start() {
    if (running) return;
    running = true;
    clock.getDelta();
    requestAnimationFrame(frame);
  }
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) start();
  }).observe(canvas);
  start();

  return {
    setSpread(v: number) {
      uniforms.uSpread.value = v;
    },
  };
}
