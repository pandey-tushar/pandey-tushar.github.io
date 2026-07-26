/* A glowing state that decays; the slider is noise, that is temperature. */
import * as THREE from 'three';
import { C, makeRenderer, loop, readouts } from './common.js';

export default function decohere(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.z = 6; r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  const N = 600, g = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3), home: THREE.Vector3[] = [];
  for (let i = 0; i < N; i++) {
    const th = Math.acos(2 * Math.random() - 1), ph = Math.random() * Math.PI * 2;
    const v = new THREE.Vector3(Math.sin(th) * Math.cos(ph), Math.sin(th) * Math.sin(ph), Math.cos(th)).multiplyScalar(2);
    pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z; home.push(v.clone());
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pm = new THREE.PointsMaterial({
    color: C.cyan, size: .07, transparent: true, opacity: .9, blending: THREE.AdditiveBlending,
  });
  grp.add(new THREE.Points(g, pm));

  let noise = 0.2;
  const readout = el.querySelector('.rl');
  const say = readouts(el);
  el.querySelector<HTMLInputElement>('input[type=range]')?.addEventListener('input', (e) => {
    noise = Number((e.target as HTMLInputElement).value) / 100;
    if (readout) {
      readout.textContent = say(
        'rate', 'decoherence rate: {rate}   (coherence time ∝ 1/rate)', { rate: noise.toFixed(2) },
      );
    }
    redraw();
  });

  const p = g.attributes.position.array as Float32Array;
  const redraw = loop(() => {
    grp.rotation.y += 0.003;
    for (let i = 0; i < N; i++) {
      const h = home[i], s = noise * 1.4;
      p[i * 3] = h.x + (Math.random() - .5) * s;
      p[i * 3 + 1] = h.y + (Math.random() - .5) * s;
      p[i * 3 + 2] = h.z + (Math.random() - .5) * s;
    }
    g.attributes.position.needsUpdate = true;
    pm.color.setHex(noise < .33 ? C.cyan : noise < .66 ? C.violet : C.rose);
    pm.opacity = 1 - noise * .55;
    r.render(sc, cam);
  });
}
