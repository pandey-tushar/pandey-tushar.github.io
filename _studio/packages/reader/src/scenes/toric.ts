/* Toric code: a periodic L x L lattice on a torus. Data qubits live on edges.
   Each qubit can carry a bit flip (X) and a phase flip (Z), chosen by a toggle.
   Two stabilizer families: STAR checks on vertices catch phase flips (Z),
   PLAQUETTE checks on faces catch bit flips (X). A single error lights a PAIR
   of the matching family; on the torus the pair can wrap across the boundary. */
import * as THREE from 'three';
import { C, makeRenderer, loop, readouts } from './common.js';

interface QData { kind: 'h' | 'v'; i: number; j: number; x: boolean; z: boolean }

export default function toric(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.set(0, 0, 9); r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  const L = 4, g = 1.35, off = ((L - 0.5) / 2) * g;
  const P = (px: number, py: number) => new THREE.Vector3(px * g - off, py * g - off, 0);
  const mod = (a: number) => ((a % L) + L) % L;
  const XC = C.gold, ZC = C.violet, YC = C.rose, Q0 = C.cyan;

  // faint grid lines (edges of the fundamental domain, with wrap stubs)
  const seg: number[] = [];
  for (let j = 0; j < L; j++) for (let i = 0; i < L; i++) {
    const a = P(i, j), b = P((i + 1) < L ? i + 1 : i + 0.5, j);
    seg.push(a.x, a.y, 0, b.x, b.y, 0);
  }
  for (let i = 0; i < L; i++) for (let j = 0; j < L; j++) {
    const a = P(i, j), b = P(i, (j + 1) < L ? j + 1 : j + 0.5);
    seg.push(a.x, a.y, 0, b.x, b.y, 0);
  }
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(seg, 3));
  grp.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: C.cyan, transparent: true, opacity: .10 })));

  // dashed boundary box to signal the torus identification
  const lo = P(-0.35, -0.35), hi = P(L - 0.5 + 0.35, L - 0.5 + 0.35);
  const bx = [
    lo.x, lo.y, 0, hi.x, lo.y, 0, hi.x, lo.y, 0, hi.x, hi.y, 0,
    hi.x, hi.y, 0, lo.x, hi.y, 0, lo.x, hi.y, 0, lo.x, lo.y, 0,
  ];
  const bg = new THREE.BufferGeometry();
  bg.setAttribute('position', new THREE.Float32BufferAttribute(bx, 3));
  grp.add(new THREE.LineSegments(bg, new THREE.LineBasicMaterial({ color: C.gold, transparent: true, opacity: .28 })));

  // stars (vertices) catch phase flips; plaquettes (faces) catch bit flips
  const stars: { m: THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial>; i: number; j: number }[] = [];
  const faces: typeof stars = [];
  for (let i = 0; i < L; i++) for (let j = 0; j < L; j++) {
    const s = new THREE.Mesh(new THREE.SphereGeometry(.14, 14, 14),
      new THREE.MeshBasicMaterial({ color: ZC, transparent: true, opacity: .16 }));
    s.position.copy(P(i, j)); grp.add(s); stars.push({ m: s, i, j });
    const f = new THREE.Mesh(new THREE.SphereGeometry(.14, 14, 14),
      new THREE.MeshBasicMaterial({ color: XC, transparent: true, opacity: .12 }));
    f.position.copy(P(i + 0.5, j + 0.5)); grp.add(f); faces.push({ m: f, i, j });
  }

  // data qubits on edges: horizontal bar for h-edges, vertical bar for v-edges
  const qubits: THREE.Mesh<THREE.BoxGeometry, THREE.MeshBasicMaterial>[] = [];
  function addQ(kind: 'h' | 'v', i: number, j: number, pos: THREE.Vector3) {
    const geo = kind === 'h' ? new THREE.BoxGeometry(.55, .16, .1) : new THREE.BoxGeometry(.16, .55, .1);
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: Q0, transparent: true, opacity: .55 }));
    m.position.copy(pos);
    m.userData = { kind, i, j, x: false, z: false } satisfies QData;
    grp.add(m); qubits.push(m);
  }
  for (let i = 0; i < L; i++) for (let j = 0; j < L; j++) { addQ('h', i, j, P(i + 0.5, j)); addQ('v', i, j, P(i, j + 0.5)); }
  const Q: Record<string, typeof qubits[number]> = {};
  for (const m of qubits) { const d = m.userData as QData; Q[d.kind + d.i + '_' + d.j] = m; }
  const at = (k: 'h' | 'v', i: number, j: number) => Q[k + mod(i) + '_' + mod(j)].userData as QData;

  function paint(m: typeof qubits[number]) {
    const d = m.userData as QData;
    m.material.color.setHex(d.x && d.z ? YC : d.x ? XC : d.z ? ZC : Q0);
    m.material.opacity = (d.x || d.z) ? .98 : .55;
  }
  const readout = el.querySelector('.rl');
  const say = readouts(el);
  function refresh() {
    let sd = 0, fd = 0;
    for (const s of stars) {
      const n = (at('h', s.i, s.j).z ? 1 : 0) + (at('h', s.i - 1, s.j).z ? 1 : 0)
        + (at('v', s.i, s.j).z ? 1 : 0) + (at('v', s.i, s.j - 1).z ? 1 : 0);
      const lit = n & 1;
      s.m.material.opacity = lit ? .98 : .16; s.m.scale.setScalar(lit ? 1.5 : 1); if (lit) sd++;
    }
    for (const f of faces) {
      const n = (at('h', f.i, f.j).x ? 1 : 0) + (at('h', f.i, f.j + 1).x ? 1 : 0)
        + (at('v', f.i, f.j).x ? 1 : 0) + (at('v', f.i + 1, f.j).x ? 1 : 0);
      const lit = n & 1;
      f.m.material.opacity = lit ? .98 : .12; f.m.scale.setScalar(lit ? 1.5 : 1); if (lit) fd++;
    }
    const ne = qubits.filter((m) => (m.userData as QData).x || (m.userData as QData).z).length;
    if (readout) {
      readout.textContent = say(
        'syndrome', '{n} error(s) · {star} star (phase) · {plaquette} plaquette (bit)',
        { n: String(ne), star: String(sd), plaquette: String(fd) },
      );
    }
  }

  let mode: 'x' | 'z' = 'x';
  const btns = el.querySelectorAll<HTMLElement>('.errbtn');
  btns.forEach((btn) => btn.addEventListener('click', () => {
    mode = btn.dataset.err === 'z' ? 'z' : 'x';
    btns.forEach((b) => b.classList.toggle('active', b === btn));
  }));

  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  el.addEventListener('click', (e) => {
    if (e.target !== r.domElement) return;
    const b = el.getBoundingClientRect();
    mouse.x = ((e.clientX - b.left) / b.width) * 2 - 1;
    mouse.y = -((e.clientY - b.top) / b.height) * 2 + 1;
    ray.setFromCamera(mouse, cam);
    const hit = ray.intersectObjects(qubits)[0];
    if (!hit) return;
    const d = hit.object.userData as QData;
    if (mode === 'x') d.x = !d.x; else d.z = !d.z;
    paint(hit.object as typeof qubits[number]); refresh(); redraw();
  });
  el.querySelector('[data-act=clear]')?.addEventListener('click', () => {
    for (const m of qubits) { const d = m.userData as QData; d.x = false; d.z = false; paint(m); }
    refresh(); redraw();
  });
  refresh();

  const redraw = loop((t) => { grp.rotation.z = Math.sin(t * 0.0002) * .03; r.render(sc, cam); });
}
