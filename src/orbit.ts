import * as THREE from 'three';

// The hero visual: an academy at the centre, with families settling into its
// orbit. Lime particles fly in from outside (new families from ads); cyan ones
// rise out of the core (returning families from the academy's own list).

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uIntro;
  uniform float uSize;
  uniform float uPixelRatio;
  uniform float uSpread;

  attribute vec3 aStart;
  attribute float aRadius;
  attribute float aTilt;
  attribute float aAngle;
  attribute float aSpeed;
  attribute float aFlow;
  attribute float aStream;
  attribute float aSize;
  attribute float aSeed;

  varying float vAlpha;
  varying float vStream;

  vec3 rotX(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x, c * p.y - s * p.z, s * p.y + c * p.z); }
  vec3 rotZ(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x - s * p.y, s * p.x + c * p.y, p.z); }

  void main() {
    float ang = aAngle + uTime * aSpeed;
    vec3 ring = vec3(cos(ang) * aRadius, sin(ang * 3.0 + aSeed * 6.2831) * 0.08 * aRadius, sin(ang) * aRadius);
    ring = rotZ(rotX(ring, aTilt), aTilt * 0.55);

    float t;
    float alpha;
    if (aFlow > 0.5) {
      float cycle = fract(uTime * (0.03 + aSeed * 0.04) + aSeed * 7.13);
      t = smoothstep(0.0, 0.75, cycle) * uIntro;
      alpha = smoothstep(0.0, 0.1, cycle) * (1.0 - smoothstep(0.88, 1.0, cycle)) * uIntro;
    } else {
      t = clamp(uIntro * (1.0 + aSeed * 0.6) - aSeed * 0.6, 0.0, 1.0);
      alpha = 0.25 + 0.75 * smoothstep(0.0, 0.4, uIntro);
    }

    float e = 1.0 - pow(1.0 - t, 3.0);
    vec3 p = mix(aStart, ring, e);
    float swirl = (1.0 - e) * 2.4;
    float cs = cos(swirl), sn = sin(swirl);
    p.xz = vec2(cs * p.x - sn * p.z, sn * p.x + cs * p.z);
    p *= 1.0 + uSpread;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize * aSize * uPixelRatio / -mv.z;
    vAlpha = alpha;
    vStream = aStream;
  }
`;

const fragmentShader = /* glsl */ `
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  uniform float uOpacity;
  varying float vAlpha;
  varying float vStream;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = pow(smoothstep(0.5, 0.0, d), 1.8);
    vec3 col = mix(uColorA, uColorB, vStream);
    gl_FragColor = vec4(col, a * vAlpha * uOpacity * 0.8);
  }
`;

const RINGS = [
  { radius: 1.9, tilt: 0.35 },
  { radius: 2.9, tilt: -0.5 },
  { radius: 4.0, tilt: 0.95 },
];

export interface OrbitOptions {
  count: number;
  /** Horizontal offset of the system on wide screens, in world units. */
  offsetX: number;
  /** Start the fly-in immediately (hero) or when first visible (CTA). */
  autoIntro: boolean;
  reducedMotion: boolean;
  /** Overall brightness, 0 to 1. Lower it when text sits on top. */
  opacity?: number;
}

export interface Orbit {
  setSpread(v: number): void;
  setIntro(v: number): void;
  readonly uniforms: { uIntro: { value: number } };
}

function rand(a: number, b: number) {
  return a + Math.random() * (b - a);
}

function gaussian() {
  return (Math.random() + Math.random() + Math.random() - 1.5) / 1.5;
}

function glowTexture(inner: string, outer: string) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, inner);
  grad.addColorStop(0.25, outer);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function createOrbit(canvas: HTMLCanvasElement, opts: OrbitOptions): Orbit | null {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch {
    return null;
  }
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0, 0, 14);

  const system = new THREE.Group();
  const tiltGroup = new THREE.Group();
  tiltGroup.rotation.x = 0.42;
  tiltGroup.add(system);
  scene.add(tiltGroup);

  // Particles
  const n = opts.count;
  const start = new Float32Array(n * 3);
  const radius = new Float32Array(n);
  const tilt = new Float32Array(n);
  const angle = new Float32Array(n);
  const speed = new Float32Array(n);
  const flow = new Float32Array(n);
  const stream = new Float32Array(n);
  const size = new Float32Array(n);
  const seed = new Float32Array(n);

  for (let i = 0; i < n; i++) {
    const ring = RINGS[i % RINGS.length];
    const isBack = Math.random() < 0.38;
    radius[i] = ring.radius + gaussian() * 0.28;
    tilt[i] = ring.tilt;
    angle[i] = Math.random() * Math.PI * 2;
    speed[i] = (0.12 + Math.random() * 0.1) * (ring.radius < 2.5 ? 1.4 : 1) * (i % 2 ? 1 : 0.85);
    flow[i] = Math.random() < 0.22 ? 1 : 0;
    stream[i] = isBack ? 1 : 0;
    size[i] = rand(12, 30) * (Math.random() < 0.03 ? 2.4 : 1);
    seed[i] = Math.random();

    if (isBack) {
      // Returning families rise out of the academy at the centre.
      const r = rand(0.05, 0.45);
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(rand(-1, 1));
      start[i * 3] = r * Math.sin(ph) * Math.cos(th);
      start[i * 3 + 1] = r * Math.cos(ph);
      start[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    } else {
      // New families arrive from far outside.
      const r = rand(10, 20);
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(rand(-1, 1));
      start[i * 3] = r * Math.sin(ph) * Math.cos(th);
      start[i * 3 + 1] = r * Math.cos(ph) * 0.6;
      start[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  geo.setAttribute('aStart', new THREE.BufferAttribute(start, 3));
  geo.setAttribute('aRadius', new THREE.BufferAttribute(radius, 1));
  geo.setAttribute('aTilt', new THREE.BufferAttribute(tilt, 1));
  geo.setAttribute('aAngle', new THREE.BufferAttribute(angle, 1));
  geo.setAttribute('aSpeed', new THREE.BufferAttribute(speed, 1));
  geo.setAttribute('aFlow', new THREE.BufferAttribute(flow, 1));
  geo.setAttribute('aStream', new THREE.BufferAttribute(stream, 1));
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  geo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 30);

  const uniforms = {
    uTime: { value: 0 },
    uIntro: { value: opts.reducedMotion ? 1 : 0 },
    uSize: { value: 9 },
    uPixelRatio: { value: 1 },
    uSpread: { value: 0 },
    uOpacity: { value: 1 },
    uColorA: { value: new THREE.Color('#d4ff3f') },
    uColorB: { value: new THREE.Color('#4fd8ff') },
  };

  const points = new THREE.Points(
    geo,
    new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  system.add(points);

  // Faint orbit lines
  const ringMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.07 });
  for (const ring of RINGS) {
    const pts: THREE.Vector3[] = [];
    for (let k = 0; k <= 160; k++) {
      const a = (k / 160) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * ring.radius, 0, Math.sin(a) * ring.radius));
    }
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), ringMat);
    line.rotation.x = ring.tilt;
    const holder = new THREE.Group();
    holder.rotation.z = ring.tilt * 0.55;
    holder.add(line);
    system.add(holder);
  }

  // The academy at the centre
  const core = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: glowTexture('rgba(255,255,255,1)', 'rgba(212,255,63,0.35)'),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  core.scale.setScalar(2.6);
  system.add(core);
  const halo = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: glowTexture('rgba(79,216,255,0.35)', 'rgba(79,216,255,0.08)'),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  halo.scale.setScalar(9);
  system.add(halo);

  // Sizing
  let width = 0;
  let height = 0;
  function resize() {
    const rect = canvas.getBoundingClientRect();
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    const pr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(pr);
    renderer.setSize(width, height, false);
    uniforms.uPixelRatio.value = pr;
    camera.aspect = width / height;
    const wide = width > 960;
    tiltGroup.position.x = wide ? opts.offsetX : 0;
    tiltGroup.position.y = wide ? 0 : opts.offsetX ? 2.5 : 0;
    const portraitScale = width < 640 ? 0.7 : width < 960 ? 0.85 : 1;
    tiltGroup.scale.setScalar(portraitScale);
    const base = opts.opacity ?? 1;
    uniforms.uOpacity.value = wide ? base : base * 0.6;
    uniforms.uSize.value = width < 640 ? 6 : 8;
    camera.updateProjectionMatrix();
  }
  resize();
  new ResizeObserver(resize).observe(canvas);

  // Pointer parallax
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener(
    'pointermove',
    (e) => {
      pointer.tx = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.ty = (e.clientY / window.innerHeight) * 2 - 1;
    },
    { passive: true },
  );

  // Render only while visible
  let visible = true;
  let running = false;
  let introStarted = opts.autoIntro;
  const clock = new THREE.Clock();
  let elapsed = 0;

  function frame() {
    if (!visible) {
      running = false;
      return;
    }
    const dt = Math.min(clock.getDelta(), 0.05);
    elapsed += dt;
    uniforms.uTime.value = elapsed;
    if (introStarted && uniforms.uIntro.value < 1) {
      uniforms.uIntro.value = Math.min(1, uniforms.uIntro.value + dt / 3.2);
    }
    pointer.x += (pointer.tx - pointer.x) * 0.04;
    pointer.y += (pointer.ty - pointer.y) * 0.04;
    system.rotation.y = elapsed * 0.05 + pointer.x * 0.35;
    tiltGroup.rotation.x = 0.42 + pointer.y * 0.18;
    core.scale.setScalar(2.6 + Math.sin(elapsed * 1.6) * 0.18);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  function startLoop() {
    if (running) return;
    running = true;
    clock.getDelta();
    requestAnimationFrame(frame);
  }

  if (opts.reducedMotion) {
    uniforms.uTime.value = 8;
    renderer.render(scene, camera);
    new ResizeObserver(() => renderer.render(scene, camera)).observe(canvas);
  } else {
    new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        if (visible) {
          introStarted = true;
          startLoop();
        }
      },
      { threshold: 0.01 },
    ).observe(canvas);
    startLoop();
  }

  return {
    setSpread(v: number) {
      uniforms.uSpread.value = v;
    },
    setIntro(v: number) {
      uniforms.uIntro.value = v;
    },
    uniforms,
  };
}
