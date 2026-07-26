/* The knot, in WebGL. Loaded on demand by upgrade.ts, so three.js never sits
   in front of the first paint. The shaders, the morph targets and the scroll
   choreography are the shipped page's; what changed is when they arrive and
   where the colours come from.

   The canvas fades in over the poster, which is the same frame at rest, so the
   handover has nothing to hide. */

import {
  AdditiveBlending, BufferAttribute, BufferGeometry, Clock, Curve, Group, LineSegments,
  LinearSRGBColorSpace, Mesh, OrthographicCamera, PerspectiveCamera, PlaneGeometry, Points,
  Scene, ShaderMaterial, TubeGeometry, Vector2, Vector3, WebGLRenderer,
} from 'three';
import { site } from '@qubit/tokens';
import { fig8, rest, tref } from './curves.ts';

/* tokens are hex strings; glsl wants literals, so bake them once */
const rgb = (h: string): [number, number, number] => [
  parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255,
];
const v3 = (c: [number, number, number]): string =>
  'vec3(' + c.map((n) => n.toFixed(3)).join(',') + ')';
const INK = rgb(site.ink);
const C0 = rgb(site.cyan), C1 = rgb(site.violet), C2 = rgb(site.magenta);
/* the nebula is the same palette at half weight against the page ink */
const dim = (c: [number, number, number]): string =>
  v3(c.map((n, i) => n * 0.48 + INK[i] * 0.52) as [number, number, number]);

/** a closed parametric loop three can sweep a tube along */
class Loop extends Curve<Vector3> {
  private readonly fn: (t: number) => [number, number, number];
  constructor(fn: (t: number) => [number, number, number]) { super(); this.fn = fn; }
  getPoint(u: number, o: Vector3 = new Vector3()): Vector3 {
    const p = this.fn(u * Math.PI * 2);
    return o.set(p[0], p[1], p[2]);
  }
}

export function mountScene(): void {
  const hero = document.querySelector('.hero');
  const picture = document.querySelector('.hero picture');
  if (!hero || !picture) return;

  const canvas = document.createElement('canvas');
  canvas.id = 'scene';
  canvas.setAttribute('aria-hidden', 'true');
  picture.after(canvas);

  let renderer: WebGLRenderer;
  try { renderer = new WebGLRenderer({ canvas, antialias: true, alpha: false }); }
  catch { canvas.remove(); return; }

  /* r128 wrote custom shader output straight to the buffer; keep that */
  renderer.outputColorSpace = LinearSRGBColorSpace;
  renderer.setClearColor(parseInt(site.ink.slice(1), 16), 1);
  renderer.autoClear = false;
  const DPR = Math.min(devicePixelRatio || 1, 2);
  renderer.setPixelRatio(DPR);
  const MOBILE = innerWidth < 640;

  /* ---- background nebula ---- */
  const bgScene = new Scene();
  const bgCam = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const bgMat = new ShaderMaterial({
    uniforms: { uRes: { value: new Vector2(1, 1) }, uTime: { value: 0 }, uStage: { value: 0 } },
    vertexShader: 'void main(){gl_Position=vec4(position,1.0);}',
    fragmentShader: [
      'precision highp float;', 'uniform vec2 uRes;uniform float uTime;uniform float uStage;',
      'vec2 hash(vec2 p){p=vec2(dot(p,vec2(127.1,311.7)),dot(p,vec2(269.5,183.3)));return -1.0+2.0*fract(sin(p)*43758.5453);}',
      'float noise(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.0-2.0*f);',
      'return mix(mix(dot(hash(i),f),dot(hash(i+vec2(1,0)),f-vec2(1,0)),u.x),mix(dot(hash(i+vec2(0,1)),f-vec2(0,1)),dot(hash(i+vec2(1,1)),f-vec2(1,1)),u.x),u.y);}',
      'float fbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){v+=a*noise(p);p*=2.0;a*=0.5;}return v;}',
      'void main(){vec2 uv=gl_FragCoord.xy/uRes.xy;vec2 p=(uv-0.5);p.x*=uRes.x/uRes.y;',
      'float t=uTime*0.035;',
      'vec2 q=vec2(fbm(p*1.4+t),fbm(p*1.4-t+5.2));',
      'float f=fbm(p*1.7+q*1.6+t*0.4);',
      'vec3 cyan=' + dim(C0) + ',violet=' + dim(C1) + ',magenta=' + dim(C2) + ';',
      'float s1=clamp(uStage,0.,1.), s2=clamp(uStage-1.,0.,1.);',
      'vec3 a=mix(violet,mix(violet,cyan,0.5),s1); a=mix(a,magenta,s2);',
      'vec3 b=mix(cyan,violet,s1*0.6); b=mix(b,magenta,s2*0.5);',
      'vec3 col=mix(a,b,smoothstep(-0.25,0.3,f));col=mix(col,magenta,smoothstep(0.28,0.72,f)*(0.6+0.4*s2));',
      'col*=0.55;col+=' + v3(INK) + '*0.7;',
      'float vig=smoothstep(1.15,0.25,length(uv-0.5));col*=mix(0.32,1.0,vig);',
      'gl_FragColor=vec4(col,1.0);}',
    ].join('\n'),
  });
  bgScene.add(new Mesh(new PlaneGeometry(2, 2), bgMat));

  /* ---- the knot ---- */
  const scene = new Scene();
  const camera = new PerspectiveCamera(rest.fov, 1, 0.1, 100);
  camera.position.set(0, 0, rest.cameraZ);
  const group = new Group(); scene.add(group);

  const TUB = MOBILE ? 260 : 440, RAD = 16;
  const g1 = new TubeGeometry(new Loop(fig8), TUB, rest.tubeRadius, RAD, true);
  const g2 = new TubeGeometry(new Loop(tref), TUB, rest.tubeRadius, RAD, true);
  const NT = g1.attributes.position.count;
  const aU = new Float32Array(NT);
  for (let k = 0; k < NT; k++) aU[k] = Math.floor(k / (RAD + 1)) / TUB;
  g1.setAttribute('aPos2', new BufferAttribute((g2.attributes.position.array as Float32Array).slice(), 3));
  g1.setAttribute('aNrm2', new BufferAttribute((g2.attributes.normal.array as Float32Array).slice(), 3));
  g1.setAttribute('aU', new BufferAttribute(aU, 1));
  g2.dispose();

  const tubeU = { uTime: { value: 0 }, uMorph: { value: 0 }, uFade: { value: 1 }, uIntro: { value: 0 } };
  const tubeVert = [
    'attribute vec3 aPos2;attribute vec3 aNrm2;attribute float aU;',
    'uniform float uMorph;varying float vU;varying vec3 vN;varying vec3 vV;',
    'void main(){vec3 p=mix(position,aPos2,uMorph);vec3 n=normalize(mix(normal,aNrm2,uMorph));',
    'vU=aU;vec4 mv=modelViewMatrix*vec4(p,1.0);vV=mv.xyz;vN=normalize(normalMatrix*n);',
    'gl_Position=projectionMatrix*mv;}',
  ].join('\n');
  const tubeFrag = (boost: number): string => [
    'precision highp float;uniform float uTime;uniform float uFade;uniform float uIntro;',
    'varying float vU;varying vec3 vN;varying vec3 vV;',
    'vec3 pal(float t){vec3 c=' + v3(C0) + ',v=' + v3(C1) + ',m=' + v3(C2) + ';',
    't=fract(t)*2.0;return t<1.0?mix(c,v,t):mix(v,m,t-1.0);}',
    'void main(){vec3 N=normalize(vN);vec3 V=normalize(-vV);',
    'float fr=pow(1.0-max(dot(N,V),0.0),2.2);',
    'vec3 base=pal(vU+uTime*0.025);',
    'vec3 col=base*0.30+base*fr*' + boost.toFixed(1) + '+vec3(fr)*0.22;',
    'float a=(' + (boost > 2 ? 'fr*0.6' : 'max(fr,0.22)') + ')*uFade*uIntro;',
    'gl_FragColor=vec4(col,a);}',
  ].join('\n');
  const matMain = new ShaderMaterial({ uniforms: tubeU, vertexShader: tubeVert, fragmentShader: tubeFrag(1.8), transparent: true, depthWrite: true });
  const matHalo = new ShaderMaterial({ uniforms: tubeU, vertexShader: tubeVert, fragmentShader: tubeFrag(2.6), transparent: true, depthWrite: false, blending: AdditiveBlending });
  group.add(new Mesh(g1, matMain));
  const halo = new Mesh(g1, matHalo); halo.scale.setScalar(1.06); group.add(halo);

  /* ---- the cloud: knot, then lattice, then graph, then ignition ---- */
  const SIDE = MOBILE ? 10 : 14, N = SIDE * SIDE * SIDE;
  const knotPts = new Float32Array(N * 3), lattPts = new Float32Array(N * 3), graphPts = new Float32Array(N * 3);
  const seeds = new Float32Array(N), delays = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const p = tref((i / N) * Math.PI * 2);
    const a = Math.random() * Math.PI * 2, r = 0.3 + (Math.random() - 0.5) * 0.1;
    knotPts[i * 3] = p[0] + Math.cos(a) * r;
    knotPts[i * 3 + 1] = p[1] + Math.sin(a) * r;
    knotPts[i * 3 + 2] = p[2] + (Math.random() - 0.5) * 0.24;
    seeds[i] = Math.random(); delays[i] = Math.random();
  }
  const SP = MOBILE ? 0.46 : 0.4, HALF = ((SIDE - 1) * SP) / 2;
  let idx = 0;
  for (let x = 0; x < SIDE; x++) for (let y = 0; y < SIDE; y++) for (let z = 0; z < SIDE; z++) {
    lattPts[idx * 3] = x * SP - HALF;
    lattPts[idx * 3 + 1] = y * SP - HALF;
    lattPts[idx * 3 + 2] = z * SP - HALF;
    idx++;
  }
  const HUBS = MOBILE ? 18 : 26, hubs: number[][] = [];
  for (let h = 0; h < HUBS; h++) {
    const th = Math.acos(1 - (2 * (h + 0.5)) / HUBS), ph = Math.PI * (1 + Math.sqrt(5)) * h;
    hubs.push([2.1 * Math.sin(th) * Math.cos(ph), 2.1 * Math.cos(th) * 0.82, 2.1 * Math.sin(th) * Math.sin(ph)]);
  }
  for (let i = 0; i < N; i++) {
    const h = hubs[i % HUBS];
    const g = (): number => (Math.random() + Math.random() + Math.random() - 1.5) * 0.5;
    graphPts[i * 3] = h[0] + g() * 0.72; graphPts[i * 3 + 1] = h[1] + g() * 0.72; graphPts[i * 3 + 2] = h[2] + g() * 0.72;
  }
  const pGeo = new BufferGeometry();
  pGeo.setAttribute('position', new BufferAttribute(knotPts, 3));
  pGeo.setAttribute('aLatt', new BufferAttribute(lattPts, 3));
  pGeo.setAttribute('aGraph', new BufferAttribute(graphPts, 3));
  pGeo.setAttribute('aSeed', new BufferAttribute(seeds, 1));
  pGeo.setAttribute('aDelay', new BufferAttribute(delays, 1));

  const ptsU = {
    uTime: { value: 0 }, uT1: { value: 0 }, uT2: { value: 0 }, uConv: { value: 0 },
    uAlpha: { value: 0 }, uClickT: { value: -10 }, uDPR: { value: DPR },
  };
  const ptsMat = new ShaderMaterial({
    uniforms: ptsU, transparent: true, depthWrite: false, blending: AdditiveBlending,
    vertexShader: [
      'attribute vec3 aLatt;attribute vec3 aGraph;attribute float aSeed;attribute float aDelay;',
      'uniform float uTime,uT1,uT2,uConv,uClickT,uDPR;',
      'varying vec3 vCol;varying float vGlow;',
      'float ss(float a,float b,float x){return smoothstep(a,b,x);}',
      'void main(){',
      'float t1=ss(0.,1.,clamp((uT1-aDelay*0.35)/0.65,0.,1.));',
      'float t2=ss(0.,1.,clamp((uT2-aDelay*0.35)/0.65,0.,1.));',
      'float gate2=t1*(1.0-t2);',
      'vec3 p=mix(position,aLatt,t1); p=mix(p,aGraph,t2);',
      'float cv=ss(0.,1.,clamp((uConv-aDelay*0.25)/0.75,0.,1.));',
      'vec3 dir=normalize(p+vec3(1e-4));',
      'vec3 core=dir*(0.55+0.5*fract(aSeed*7.31));',
      'p=mix(p,core,cv);',
      'p+=0.035*(1.0-cv*0.6)*(1.0-0.55*gate2)*vec3(sin(uTime*0.7+aSeed*17.0),cos(uTime*0.9+aSeed*23.0),sin(uTime*0.8+aSeed*31.0));',
      'float age=uTime-uClickT;',
      'float w=(age>0.0&&age<2.5)?exp(-3.0*abs(length(p)-age*3.2))*exp(-age*1.4):0.0;',
      'p+=normalize(p+vec3(1e-4))*w*0.4;',
      'float gate=t1*(1.0-t2);',
      'float flick=step(0.982,fract(aSeed*91.7+floor(uTime*2.0)*0.618))*gate;',
      'vec3 c0=' + v3(C0) + ',c1=' + v3(C1) + ',c2=' + v3(C2) + ';',
      'vec3 cg=mix(c2,c1,fract(aSeed*3.17));',
      'vCol=mix(c0,c1,t1); vCol=mix(vCol,cg,t2);',
      'vCol=mix(vCol,mix(c2,vec3(1.0),0.35),flick*0.9);',
      'vCol=mix(vCol,mix(c2,vec3(1.0),0.8),cv*0.45);',
      'vGlow=w*1.6+flick*0.9+cv*0.8;',
      'vec4 mv=modelViewMatrix*vec4(p,1.0);',
      'gl_PointSize=(2.4+1.6*aSeed+3.5*w+2.2*flick+1.4*cv)*uDPR*(9.0/max(1.0,-mv.z));',
      'gl_Position=projectionMatrix*mv;}',
    ].join('\n'),
    fragmentShader: [
      'precision highp float;uniform float uAlpha;',
      'varying vec3 vCol;varying float vGlow;',
      'void main(){',
      'float d=length(gl_PointCoord-vec2(0.5));',
      'float m=smoothstep(0.5,0.12,d);',
      'vec3 col=vCol*(0.55+vGlow)+vec3(vGlow*0.35);',
      'gl_FragColor=vec4(col,m*uAlpha);}',
    ].join('\n'),
  });
  group.add(new Points(pGeo, ptsMat));

  /* ---- graph edges ---- */
  const edgeSet = new Set<string>(); const epos: number[] = [], emix: number[] = [], ephase: number[] = [];
  for (let a = 0; a < HUBS; a++) {
    const ds = hubs.map((h, b) => [b, Math.hypot(h[0] - hubs[a][0], h[1] - hubs[a][1], h[2] - hubs[a][2])])
      .sort((x, y) => x[1] - y[1]);
    for (let k = 1; k <= 3 && k < ds.length; k++) {
      const b = ds[k][0], key = a < b ? a + '_' + b : b + '_' + a;
      if (edgeSet.has(key)) continue;
      edgeSet.add(key);
      const ph = Math.random();
      epos.push(...hubs[a], ...hubs[b]); emix.push(0, 1); ephase.push(ph, ph);
    }
  }
  const eGeo = new BufferGeometry();
  eGeo.setAttribute('position', new BufferAttribute(new Float32Array(epos), 3));
  eGeo.setAttribute('aMix', new BufferAttribute(new Float32Array(emix), 1));
  eGeo.setAttribute('aPhase', new BufferAttribute(new Float32Array(ephase), 1));
  const edgeU = { uTime: { value: 0 }, uOn: { value: 0 } };
  const eMat = new ShaderMaterial({
    uniforms: edgeU, transparent: true, depthWrite: false, blending: AdditiveBlending,
    vertexShader: [
      'attribute float aMix;attribute float aPhase;',
      'varying float vM;varying float vP;',
      'void main(){vM=aMix;vP=aPhase;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    ].join('\n'),
    fragmentShader: [
      'precision highp float;uniform float uTime,uOn;varying float vM;varying float vP;',
      'void main(){',
      'vec3 c=mix(' + v3(C1) + ',' + v3(C2) + ',vM);',
      'float pulse=0.55+0.45*sin(uTime*1.7+vP*6.2831);',
      'gl_FragColor=vec4(c*0.8,uOn*0.34*pulse);}',
    ].join('\n'),
  });
  group.add(new LineSegments(eGeo, eMat));

  const BASE = MOBILE ? 0.8 : rest.scale;
  group.scale.setScalar(BASE);

  const resize = (): void => {
    const w = innerWidth, h = innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    bgMat.uniforms.uRes.value.set(w * DPR, h * DPR);
  };
  resize(); addEventListener('resize', resize);

  /* ---- pointer ---- */
  let tx = 0, ty = 0, cx = 0, cy = 0;
  let dragging = false, moved = 0, lastX = 0, lastY = 0, yaw = 0, pitch = 0, velYaw = 0, velPitch = 0;
  const DRAG_K = 0.009;
  if (matchMedia('(pointer:fine)').matches) {
    addEventListener('pointermove', (e) => {
      tx = e.clientX / innerWidth - 0.5; ty = e.clientY / innerHeight - 0.5;
      if (!dragging) return;
      const dx = e.clientX - lastX, dy = e.clientY - lastY; lastX = e.clientX; lastY = e.clientY;
      moved += Math.abs(dx) + Math.abs(dy);
      yaw += dx * DRAG_K; pitch = Math.max(-1.2, Math.min(1.2, pitch + dy * DRAG_K));
      velYaw = dx * DRAG_K; velPitch = dy * DRAG_K; e.preventDefault();
    }, { passive: false });
    addEventListener('pointerdown', (e) => {
      if ((e.target as Element).closest('a,button,nav,.box')) return;
      dragging = true; moved = 0; lastX = e.clientX; lastY = e.clientY; velYaw = velPitch = 0;
      document.body.classList.add('grabbing');
    });
    addEventListener('pointerup', () => {
      if (dragging && moved < 6) ptsU.uClickT.value = ptsU.uTime.value;
      dragging = false; document.body.classList.remove('grabbing');
    });
    addEventListener('pointercancel', () => { dragging = false; document.body.classList.remove('grabbing'); });
  }

  const secQ = document.getElementById('quantum');
  const secAI = document.getElementById('ai');
  const secC = document.getElementById('contact');
  const sp = (el: Element | null): number => {
    if (!el) return 0;
    const top = el.getBoundingClientRect().top, vh = innerHeight;
    return Math.max(0, Math.min(1, (vh * 0.7 - top) / (vh * 0.7)));
  };

  const frame = (): void => {
    renderer.clear();
    renderer.render(bgScene, bgCam);
    renderer.clearDepth();
    renderer.render(scene, camera);
  };

  const INTRO_MS = 1200;
  const start = performance.now();
  const clock = new Clock();
  let live = true;
  const animate = (): void => {
    if (!live) return;
    requestAnimationFrame(animate);
    const dt = clock.getDelta(), now = performance.now();
    tubeU.uTime.value += dt; bgMat.uniforms.uTime.value += dt; ptsU.uTime.value += dt; edgeU.uTime.value += dt;
    let it = Math.min((now - start) / INTRO_MS, 1); it = 1 - Math.pow(1 - it, 3);
    tubeU.uIntro.value = it;
    cx += (tx - cx) * 0.05; cy += (ty - cy) * 0.05;

    const sQ = sp(secQ), sAI = sp(secAI), sC = sp(secC);
    tubeU.uMorph.value = Math.min(1, sQ * 1.6);
    tubeU.uFade.value = Math.max(0, 1 - Math.max(0, sQ - 0.3) * 2.6);
    ptsU.uAlpha.value = Math.min(1, Math.max(0, sQ - 0.22) * 3) * (0.92 - 0.15 * sC);
    ptsU.uT1.value = sQ; ptsU.uT2.value = sAI; ptsU.uConv.value = sC;
    edgeU.uOn.value = Math.max(0, sAI * 1.2 - 0.2) * (1 - sC * 0.85);
    bgMat.uniforms.uStage.value = sQ + sAI;

    const xT = innerWidth < 900 ? 0 : (() => {
      let x = rest.offsetX; x += (-2 - x) * sQ; x += (2 - x) * sAI; x += (0 - x) * sC; return x;
    })();
    group.position.x += (xT - group.position.x) * 0.06;
    group.position.y += (Math.sin((sQ + sAI) * 3.14) * 0.3 - group.position.y) * 0.05;
    group.scale.setScalar(BASE * (1 - 0.06 * sQ + 0.02 * sAI - 0.1 * sC));

    if (!dragging) {
      yaw += velYaw; pitch = Math.max(-1.2, Math.min(1.2, pitch + velPitch));
      velYaw *= 0.95; velPitch *= 0.95;
      yaw += dt * (0.16 + 0.08 * sAI + 0.22 * sC);
    }
    group.rotation.y = yaw;
    group.rotation.x = rest.rotX + pitch + (dragging ? 0 : cy * 0.3);
    group.rotation.z = dragging ? 0 : cx * 0.3;
    frame();
  };

  /* start where the poster left off, then take over */
  yaw = rest.rotY;
  group.position.x = innerWidth < 900 ? 0 : rest.offsetX;
  frame();
  requestAnimationFrame(() => canvas.classList.add('up'));
  animate();

  addEventListener('pagehide', () => { live = false; renderer.dispose(); });
}
