/* Cosmos zoom: qubit to lattice to stars. Constant-size points so nothing
   blows up into a splat when the camera passes near a shell. */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function cosmos(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(50, el.clientWidth / el.clientHeight, .1, 200);
  cam.position.z = 5; r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  const shellColor = [C.gold, C.cyan, C.violet, C.rose, C.cyan];
  for (let l = 0; l < 5; l++) {
    const N = 80 * (l + 1), g = new THREE.BufferGeometry(), pos = new Float32Array(N * 3);
    const R = 2 + l * 3;
    for (let i = 0; i < N; i++) {
      const th = Math.acos(2 * Math.random() - 1), ph = Math.random() * Math.PI * 2;
      pos[i * 3] = Math.sin(th) * Math.cos(ph) * R;
      pos[i * 3 + 1] = Math.sin(th) * Math.sin(ph) * R;
      pos[i * 3 + 2] = Math.cos(th) * R;
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    grp.add(new THREE.Points(g, new THREE.PointsMaterial({
      color: shellColor[l], size: 1.5 + l * 0.6, sizeAttenuation: false,
      transparent: true, opacity: .7, blending: THREE.AdditiveBlending,
    })));
  }

  loop((t) => {
    grp.rotation.y = t * 0.0003; grp.rotation.x = t * 0.0001;
    cam.position.z = 5 + Math.sin(t * 0.0004) * 3;
    r.render(sc, cam);
  });
}
