/* Page-level scenery: the fixed starfield and the cover lattice. Loaded after
   first paint so the text does not wait on Three.js. */
import * as THREE from 'three';
import { C, loop } from './common.js';

export function starfield(canvas: HTMLCanvasElement): void {
  const r = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  const sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, .1, 2000);
  cam.position.z = 600;

  const N = 1400, g = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
  const pal = [C.cyan, C.violet, C.gold];
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - .5) * 1600;
    pos[i * 3 + 1] = (Math.random() - .5) * 1200;
    pos[i * 3 + 2] = (Math.random() - .5) * 1400;
    const c = new THREE.Color(pal[i % 3]).multiplyScalar(.4 + Math.random() * .6);
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const pts = new THREE.Points(g, new THREE.PointsMaterial({
    size: 2.2, vertexColors: true, transparent: true, opacity: .85,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  sc.add(pts);

  let sy = 0;
  addEventListener('scroll', () => { sy = scrollY; }, { passive: true });
  const resize = () => {
    r.setSize(innerWidth, innerHeight);
    cam.aspect = innerWidth / innerHeight;
    cam.updateProjectionMatrix();
  };
  addEventListener('resize', resize); resize();

  loop((t) => {
    pts.rotation.y = t * 0.00002 + sy * 0.00004;
    pts.rotation.x = Math.sin(t * 0.00001) * .1;
    cam.position.z = 600 - sy * 0.05;
    r.render(sc, cam);
  });
}

export function cover(mount: HTMLElement): void {
  const r = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  r.setSize(innerWidth, innerHeight);
  mount.appendChild(r.domElement);
  const sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .1, 100);
  cam.position.z = 9;
  const grp = new THREE.Group(); sc.add(grp);

  const nodes: THREE.Vector3[] = [], K = 90, rad = 4.2;
  const ng = new THREE.SphereGeometry(.055, 10, 10);
  for (let i = 0; i < K; i++) {
    const y = 1 - (i / (K - 1)) * 2, r2 = Math.sqrt(1 - y * y), th = i * 2.399963;
    const p = new THREE.Vector3(Math.cos(th) * r2, y, Math.sin(th) * r2).multiplyScalar(rad);
    const mm = new THREE.Mesh(ng, new THREE.MeshBasicMaterial({ color: [C.cyan, C.violet, C.gold][i % 3] }));
    mm.position.copy(p); grp.add(mm); nodes.push(p);
  }
  const lp: number[] = [];
  for (let i = 0; i < K; i++) for (let j = i + 1; j < K; j++) {
    if (nodes[i].distanceTo(nodes[j]) < 2.5) {
      lp.push(nodes[i].x, nodes[i].y, nodes[i].z, nodes[j].x, nodes[j].y, nodes[j].z);
    }
  }
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
  grp.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({
    color: C.cyan, transparent: true, opacity: .16, blending: THREE.AdditiveBlending,
  })));
  const core = new THREE.Mesh(new THREE.SphereGeometry(1.1, 32, 32),
    new THREE.MeshBasicMaterial({ color: C.gold, transparent: true, opacity: .12 }));
  grp.add(core);

  let mx = 0, my = 0;
  addEventListener('mousemove', (e) => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; });
  addEventListener('resize', () => {
    r.setSize(innerWidth, innerHeight);
    cam.aspect = innerWidth / innerHeight;
    cam.updateProjectionMatrix();
  });

  loop((t) => {
    grp.rotation.y = t * 0.0002 + mx * .6;
    grp.rotation.x = my * .4;
    core.scale.setScalar(1 + Math.sin(t * 0.001) * .06);
    r.render(sc, cam);
  });
}
