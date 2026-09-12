import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactGlobe, { type GlobeMethods } from 'react-globe.gl';
import {
  ACESFilmicToneMapping, AdditiveBlending, AmbientLight, BufferGeometry,
  Color, DirectionalLight, Float32BufferAttribute, Group, Mesh,
  MeshPhongMaterial, Points, PointsMaterial, ShaderMaterial, SphereGeometry,
} from 'three';

import earthNightTexture from '../../assets/earth-night.jpg';
import earthBumpTexture from '../../assets/earth-bump.png';

/* ---- sample data: two conjunction objects + 6 background sats ---- */
const POINTS = [
  { id: 'ISS',  lat:  28.6, lng: -80.6, alt: 0.068, flagged: true  },
  { id: 'CSS',  lat:  41.2, lng:  89.4, alt: 0.072, flagged: true  },
  { id: 'S1',   lat:  51.6, lng: 140.0, alt: 0.055, flagged: false },
  { id: 'S2',   lat: -28.0, lng: -60.0, alt: 0.050, flagged: false },
  { id: 'S3',   lat:  20.0, lng:  30.0, alt: 0.062, flagged: false },
  { id: 'S4',   lat: -50.0, lng: 170.0, alt: 0.048, flagged: false },
  { id: 'S5',   lat:  65.0, lng:  20.0, alt: 0.058, flagged: false },
  { id: 'S6',   lat: -10.0, lng: -120.0, alt: 0.052, flagged: false },
];

/* short orbit trail arcs */
const ARCS = POINTS.map((p, i) => ({
  ...p,
  endLat: Math.max(-82, Math.min(82, p.lat + (i % 2 === 0 ? 10 : -10))),
  endLng: p.lng - 38,
  endAlt: p.alt,
}));

const atmosphereVert = `
  varying vec3 vNormal; varying vec3 vView;
  void main() {
    vec4 vp = modelViewMatrix * vec4(position,1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-vp.xyz);
    gl_Position = projectionMatrix * vp;
  }
`;
const atmosphereFrag = `
  uniform vec3 glowColor; uniform float intensity;
  varying vec3 vNormal; varying vec3 vView;
  void main() {
    float f = pow(1.0 - max(dot(vNormal, vView), 0.0), 3.1);
    gl_FragColor = vec4(glowColor, f * intensity);
  }
`;

function makeAtmosphere(r: number) {
  const mat = new ShaderMaterial({
    uniforms: { glowColor: { value: new Color('#6fa8ff') }, intensity: { value: 0.52 } },
    vertexShader: atmosphereVert, fragmentShader: atmosphereFrag,
    transparent: true, blending: AdditiveBlending, depthWrite: false,
  });
  const m = new Mesh(new SphereGeometry(r * 1.045, 64, 64), mat);
  m.name = 'landing-atm'; return m;
}

function makeStarfield(r: number) {
  const count = 460;
  const pos = new Float32Array(count * 3);
  const ga = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - ((i + 0.5) / count) * 2;
    const ring = Math.sqrt(1 - y * y);
    const t = i * ga;
    const d = r * 7.5 + ((i * 17) % 11) - 5;
    pos[i*3] = Math.cos(t) * ring * d;
    pos[i*3+1] = y * d;
    pos[i*3+2] = Math.sin(t) * ring * d;
  }
  const geo = new BufferGeometry();
  geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
  const mat = new PointsMaterial({ color: '#9fc9ff', size: 1.1, sizeAttenuation: false, transparent: true, opacity: 0.48, depthWrite: false });
  const g = new Group(); g.name = 'landing-stars'; g.add(new Points(geo, mat));
  return g;
}

export function LandingGlobe() {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  const globeMat = useMemo(() => new MeshPhongMaterial({
    color: '#bfd6f5', emissive: '#071a36', emissiveIntensity: 0.28,
    specular: '#42689a', shininess: 9, bumpScale: 0.72,
  }), []);

  useEffect(() => {
    const el = containerRef.current; if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      if (e) setSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const onReady = useCallback(() => {
    const g = globeRef.current; if (!g) return;
    const scene = g.scene();
    /* remove stale */
    scene.getObjectByName('landing-atm')?.removeFromParent();
    scene.getObjectByName('landing-stars')?.removeFromParent();
    scene.add(makeAtmosphere(g.getGlobeRadius()));
    const stars = makeStarfield(g.getGlobeRadius()); stars.rotation.y = -0.42; scene.add(stars);

    const renderer = g.renderer();
    renderer.toneMapping = ACESFilmicToneMapping; renderer.toneMappingExposure = 1.04;

    const dir = g.lights().find(l => l instanceof DirectionalLight) as DirectionalLight | undefined;
    if (dir) { dir.position.set(1.3, 0.65, 1.5); dir.intensity = 1.45; }

    if (!scene.getObjectByName('landing-fill')) {
      const fill = new AmbientLight('#89b6eb', 0.48); fill.name = 'landing-fill'; scene.add(fill);
    }

    /* gentle auto-rotate */
    g.controls().autoRotate = true;
    g.controls().autoRotateSpeed = 0.28;
    g.controls().enableZoom = false;
    g.controls().enablePan = false;

    /* set initial camera distance / angle */
    g.pointOfView({ lat: 20, lng: 10, altitude: 2.1 }, 0);
  }, []);

  useEffect(() => () => { globeMat.dispose(); }, [globeMat]);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden" aria-hidden="true">
      <div className="globe-star-dust" aria-hidden="true" />
      <ReactGlobe
        ref={globeRef}
        width={size.w || undefined}
        height={size.h || undefined}
        onGlobeReady={onReady}
        globeImageUrl={earthNightTexture}
        bumpImageUrl={earthBumpTexture}
        globeMaterial={globeMat}
        showAtmosphere={false}
        backgroundColor="rgba(0,0,0,0)"
        pointsData={POINTS}
        pointLat="lat"
        pointLng="lng"
        pointAltitude="alt"
        pointColor={(p) => ((p as typeof POINTS[0]).flagged ? '#ff5b67' : '#60a5fa')}
        pointRadius={(p) => ((p as typeof POINTS[0]).flagged ? 0.72 : 0.38)}
        pointResolution={24}
        arcsData={ARCS}
        arcStartLat="lat"
        arcStartLng="lng"
        arcStartAltitude="alt"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcEndAltitude="endAlt"
        arcColor={(a: object) => (a as typeof ARCS[0]).flagged
          ? ['rgba(255,91,103,0.72)', 'rgba(255,91,103,0.02)']
          : ['rgba(96,165,250,0.44)', 'rgba(96,165,250,0.01)']}
        arcStroke={0.22}
        arcAltitude={0.065}
        arcDashLength={0.48}
        arcDashGap={0.72}
        arcDashAnimateTime={5200}
        ringsData={POINTS.filter(p => p.flagged)}
        ringLat="lat"
        ringLng="lng"
        ringAltitude="alt"
        ringColor={() => (t: number) => `rgba(255,91,103,${Math.pow(1-t,1.8)})`}
        ringResolution={120}
        ringMaxRadius={4.2}
        ringPropagationSpeed={1.35}
        ringRepeatPeriod={3100}
      />
    </div>
  );
}
