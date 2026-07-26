/* Bloch sphere, draggable. One qubit steered around its sphere. */
import * as THREE from 'three';
import { C, makeRenderer, loop } from './common.js';

export default function bloch(el: HTMLElement): void {
  const r = makeRenderer(el), sc = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, .1, 100);
  cam.position.set(0, 0, 6); r.__cam = cam;
  const grp = new THREE.Group(); sc.add(grp);

  grp.add(new THREE.Mesh(new THREE.SphereGeometry(2, 28, 20),
    new THREE.MeshBasicMaterial({ color: C.cyan, wireframe: true, transparent: true, opacity: .14 })));

  for (const [c, ax] of [[C.gold, 'y'], [C.violet, 'x'], [C.rose, 'z']] as const) {
    const pts: THREE.Vector3[] = [];
    for (let a = 0; a <= 64; a++) {
      const t = a / 64 * Math.PI * 2;
      if (ax === 'y') pts.push(new THREE.Vector3(Math.cos(t) * 2, 0, Math.sin(t) * 2));
      if (ax === 'x') pts.push(new THREE.Vector3(0, Math.cos(t) * 2, Math.sin(t) * 2));
      if (ax === 'z') pts.push(new THREE.Vector3(Math.cos(t) * 2, Math.sin(t) * 2, 0));
    }
    grp.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: c, transparent: true, opacity: .3 })));
  }

  const state = new THREE.Group(); grp.add(state);
  const arrow = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 2, C.gold, .35, .2);
  state.add(arrow);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(.12, 16, 16), new THREE.MeshBasicMaterial({ color: C.gold }));
  state.add(tip);

  let th = 0.6, ph = 0.5;
  function upd() {
    const v = new THREE.Vector3(Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph));
    arrow.setDirection(v); tip.position.copy(v.clone().multiplyScalar(2));
  }
  upd();

  let drag = false, px = 0, py = 0;
  el.style.touchAction = 'none';
  el.addEventListener('pointerdown', (e) => { drag = true; px = e.clientX; py = e.clientY; e.preventDefault(); });
  addEventListener('pointerup', () => { drag = false; });
  el.addEventListener('pointermove', (e) => {
    if (!drag) return;
    e.preventDefault();
    th += (e.clientY - py) * 0.01; ph += (e.clientX - px) * 0.01;
    th = Math.max(.01, Math.min(Math.PI - .01, th));
    px = e.clientX; py = e.clientY;
    upd(); redraw();
  });

  const redraw = loop(() => { grp.rotation.y += drag ? 0 : 0.0025; r.render(sc, cam); });
}
