/* Shor: a lock woven from a factor lattice, dissolving. */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function lock(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.z = 6; r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.5, .16, 16, 60),
    new THREE.MeshBasicMaterial({ color: C.gold, transparent: true, opacity: .8 }));
  grp.add(ring);
  const shackle = new THREE.Mesh(new THREE.TorusGeometry(.8, .12, 16, 40, Math.PI),
    new THREE.MeshBasicMaterial({ color: C.gold, transparent: true, opacity: .8 }));
  shackle.position.y = 1.4; grp.add(shackle);

  const N = 500, g = new THREE.BufferGeometry(), pos = new Float32Array(N * 3), home: THREE.Vector3[] = [];
  for (let i = 0; i < N; i++) {
    const a = Math.random() * Math.PI * 2, rr = 1.5 + (Math.random() - .5) * .3;
    const v = new THREE.Vector3(Math.cos(a) * rr, Math.sin(a) * rr, (Math.random() - .5) * .4);
    pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z; home.push(v.clone());
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pm = new THREE.PointsMaterial({
    color: C.cyan, size: .05, transparent: true, opacity: 0, blending: THREE.AdditiveBlending,
  });
  grp.add(new THREE.Points(g, pm));
  const p = g.attributes.position.array as Float32Array;

  loop((t) => {
    grp.rotation.y = Math.sin(t * 0.0003) * .5;
    const phase = (t * 0.00018) % (Math.PI * 2);
    const open = (Math.sin(phase) + 1) / 2;
    ring.material.opacity = .85 - open * .7;
    shackle.material.opacity = .85 - open * .7;
    shackle.position.y = 1.4 + open * 0.6;
    pm.opacity = open * .9;
    for (let i = 0; i < N; i++) {
      const h = home[i], s = open * 2.2;
      p[i * 3] = h.x + (Math.random() - .5) * s;
      p[i * 3 + 1] = h.y + (Math.random() - .5) * s;
      p[i * 3 + 2] = h.z + (Math.random() - .5) * s;
    }
    g.attributes.position.needsUpdate = true;
    r.render(sc, cam);
  });
}
