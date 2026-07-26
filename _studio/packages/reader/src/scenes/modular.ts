/* Modular chips linked by photonic beams. */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function modular(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.set(0, 1.5, 9); cam.lookAt(0, 0, 0); r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  const chips: THREE.Vector3[] = [];
  const layout: [number, number, number][] = [[-3, 0, 0], [3, 0, 0], [0, 0, -3], [0, 0, 3], [0, 2.4, 0]];
  layout.forEach((p, i) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.3, .25, 1.3),
      new THREE.MeshBasicMaterial({ color: i === 4 ? C.gold : C.cyan, transparent: true, opacity: .6 }));
    m.position.set(p[0], p[1], p[2]); grp.add(m);
    const w = new THREE.Mesh(new THREE.BoxGeometry(1.34, .28, 1.34),
      new THREE.MeshBasicMaterial({ color: C.violet, wireframe: true, transparent: true, opacity: .5 }));
    w.position.copy(m.position); grp.add(w);
    /* a few qubits inside each module */
    for (let q = 0; q < 4; q++) {
      const dot = new THREE.Mesh(new THREE.SphereGeometry(.06, 8, 8), new THREE.MeshBasicMaterial({ color: C.gold }));
      dot.position.set(p[0] + (q % 2 ? .3 : -.3), p[1] + .16, p[2] + (q < 2 ? .3 : -.3));
      grp.add(dot);
    }
    chips.push(m.position);
  });

  const beams: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>[] = [];
  for (let i = 0; i < 4; i++) {
    const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints([chips[i], chips[4]]),
      new THREE.LineBasicMaterial({ color: C.cyan, transparent: true, opacity: .5 }));
    grp.add(ln); beams.push(ln);
  }
  const ph = new THREE.Mesh(new THREE.SphereGeometry(.1, 12, 12), new THREE.MeshBasicMaterial({ color: C.gold }));
  grp.add(ph);

  loop((t) => {
    grp.rotation.y = t * 0.0004;
    const period = 1600, k = (t % period) / period, src = Math.floor(t / period) % 4;
    ph.position.lerpVectors(chips[src], chips[4], k);
    beams.forEach((b, i) => { b.material.opacity = i === src ? .9 : .25; });
    r.render(sc, cam);
  });
}
