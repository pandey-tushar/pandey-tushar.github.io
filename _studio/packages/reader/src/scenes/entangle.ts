/* Two spheres. For |Phi+> the outcomes are CORRELATED (both up or both down). */
import * as THREE from 'three';
import { C, makeRenderer, loop, readouts } from './common.js';

export default function entangle(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.set(0, 0, 8); r.__cam = cam;

  function orb(x: number, c: number) {
    const g = new THREE.Group(); g.position.x = x;
    g.add(new THREE.Mesh(new THREE.SphereGeometry(1.2, 24, 18),
      new THREE.MeshBasicMaterial({ color: c, wireframe: true, transparent: true, opacity: .2 })));
    const ar = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 1.2, C.gold, .3, .2);
    g.add(ar); g.userData.ar = ar; sc.add(g); return g;
  }
  const A = orb(-2.6, C.cyan), B = orb(2.6, C.violet);
  const lk = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-2.6, 0, 0), new THREE.Vector3(2.6, 0, 0)]),
    new THREE.LineBasicMaterial({ color: C.rose, transparent: true, opacity: .5 }));
  sc.add(lk);

  let spin = true;
  let rt: ReturnType<typeof setTimeout> | undefined;
  const readout = el.querySelector('.rl');
  const say = readouts(el);
  el.querySelector('[data-act=measure]')?.addEventListener('click', () => {
    clearTimeout(rt);
    spin = false;
    const up = Math.random() > .5, d = up ? 1 : -1;
    A.userData.ar.setDirection(new THREE.Vector3(0, d, 0));
    B.userData.ar.setDirection(new THREE.Vector3(0, d, 0));
    if (readout) {
      readout.textContent = up
        ? say('measuredUp', 'measured: A=↑  B=↑ (correlated)')
        : say('measuredDown', 'measured: A=↓  B=↓ (correlated)');
    }
    redraw();
    rt = setTimeout(() => {
      spin = true;
      if (readout) readout.textContent = say('restored', 'superposition restored');
      redraw();
    }, 2600);
  });

  const redraw = loop((t) => {
    if (spin) {
      const a = t * 0.002;
      A.userData.ar.setDirection(new THREE.Vector3(Math.sin(a), Math.cos(a), 0));
      B.userData.ar.setDirection(new THREE.Vector3(Math.sin(a), Math.cos(a), 0));
    }
    lk.material.opacity = spin ? .5 : .12;
    r.render(sc, cam);
  });
}
