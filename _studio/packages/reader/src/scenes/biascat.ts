/* Noise-biased cat qubit: poles stable, equator jitters (bit-flip protected). */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function biascat(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.set(0, 0, 6); r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  grp.add(new THREE.Mesh(new THREE.SphereGeometry(2, 26, 18),
    new THREE.MeshBasicMaterial({ color: C.violet, wireframe: true, transparent: true, opacity: .12 })));

  const pole = (y: number, c: number) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(.26, 20, 20), new THREE.MeshBasicMaterial({ color: c }));
    m.position.y = y; grp.add(m);
  };
  pole(2, C.cyan); pole(-2, C.gold);

  const N = 260, g = new THREE.BufferGeometry(), pos = new Float32Array(N * 3), base: THREE.Vector3[] = [];
  for (let i = 0; i < N; i++) {
    const ph = Math.random() * Math.PI * 2, lat = (Math.random() - .5) * 0.5;
    const v = new THREE.Vector3(Math.cos(ph) * 2, lat * 2, Math.sin(ph) * 2);
    pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z; base.push(v.clone());
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  grp.add(new THREE.Points(g, new THREE.PointsMaterial({
    color: C.rose, size: .06, transparent: true, opacity: .8, blending: THREE.AdditiveBlending,
  })));

  const p = g.attributes.position.array as Float32Array;
  loop(() => {
    grp.rotation.y += 0.004;
    for (let i = 0; i < N; i++) {
      const b = base[i];
      p[i * 3] = b.x + (Math.random() - .5) * .9;
      p[i * 3 + 1] = b.y + (Math.random() - .5) * .9;
      p[i * 3 + 2] = b.z + (Math.random() - .5) * .9;
    }
    g.attributes.position.needsUpdate = true;
    r.render(sc, cam);
  });
}
