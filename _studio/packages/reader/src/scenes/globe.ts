/* Quantum internet globe: entanglement links arcing between ground stations. */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function globe(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.z = 6; r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  grp.add(new THREE.Mesh(new THREE.SphereGeometry(2, 32, 24),
    new THREE.MeshBasicMaterial({ color: C.cyan, wireframe: true, transparent: true, opacity: .12 })));

  const cities: THREE.Vector3[] = [];
  for (let i = 0; i < 14; i++) {
    const th = Math.acos(2 * Math.random() - 1), ph = Math.random() * Math.PI * 2;
    const v = new THREE.Vector3(Math.sin(th) * Math.cos(ph), Math.sin(th) * Math.sin(ph), Math.cos(th)).multiplyScalar(2);
    const m = new THREE.Mesh(new THREE.SphereGeometry(.05, 10, 10), new THREE.MeshBasicMaterial({ color: C.gold }));
    m.position.copy(v); grp.add(m); cities.push(v);
  }
  for (let k = 0; k < 10; k++) {
    const a = cities[Math.floor(Math.random() * cities.length)];
    const b = cities[Math.floor(Math.random() * cities.length)];
    if (a === b) continue;
    const mid = a.clone().add(b).multiplyScalar(.5).setLength(2.4 + a.distanceTo(b) * 0.5);
    const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
    grp.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(30)),
      new THREE.LineBasicMaterial({ color: C.violet, transparent: true, opacity: .5 })));
  }

  loop(() => { grp.rotation.y += 0.004; r.render(sc, cam); });
}
