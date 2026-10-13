// Lesson 2 "Run it live": tableau simulation of the logical CNOT in the browser, with a check heatmap.
import { layers, runShots, REF_LAYER } from './cnotlive.js';
import { el, X_STABS, Z_STABS, checkName } from './patch.js';
import { BW, phasesOf, drawStrip } from './strip.js';

const LW = 92, RH = 15;
const pct = (x) => `${(100 * x).toFixed(1)}%`;

// Check k of a round: patch k >> 3; (k & 7) < 4 is X_STABS[k & 3], else Z_STABS[k & 3] (cnotlive.js).
function checkLabel(k) {
  const j = k & 7;
  return `${'AB'[k >> 3]} ${checkName(j < 4 ? 'X' : 'Z', (j < 4 ? X_STABS : Z_STABS)[j & 3])}`;
}

export function initLive(root) {
  root.innerHTML = `
  <form class="live-form" id="live-form">
    <label>Shots <output id="lv-shots-out">300</output>
      <input type="range" id="lv-shots" min="100" max="1000" step="100" value="300"></label>
    <label>Readout
      <select id="lv-basis"><option value="Z">Z (both patches)</option><option value="X">X (both patches)</option></select></label>
    <label>Noise p per gate <output id="lv-p-out">0.003</output>
      <input type="range" id="lv-p" min="0" max="0.02" step="0.001" value="0.003"></label>
    <fieldset id="lv-inj-box" disabled>
      <legend><label><input type="checkbox" id="lv-inj"> Inject one error</label></legend>
      <label>Pauli <select id="lv-pauli"><option>X</option><option>Y</option><option>Z</option></select></label>
      <label>Qubit <input type="number" id="lv-q" min="0" max="17" value="4"></label>
      <label>After layer <select id="lv-layer"></select></label>
    </fieldset>
    <button type="submit" id="lv-run">Run</button>
    <span id="lv-status" class="muted" role="status"></span>
  </form>
  <div class="stats" id="lv-stats"></div>
  <div class="heat-scroll"><div class="heat-inner" id="lv-heat"></div></div>
  <p class="legend" id="lv-legend" hidden></p>`;
  const $ = (id) => root.querySelector(`#${id}`);
  const shots = $('lv-shots'), p = $('lv-p'), basis = $('lv-basis'), layerSel = $('lv-layer');
  shots.addEventListener('input', () => { $('lv-shots-out').textContent = shots.value; });
  p.addEventListener('input', () => { $('lv-p-out').textContent = (+p.value).toFixed(3); });
  // the error controls only apply while the box is ticked (a disabled fieldset leaves its legend usable)
  $('lv-inj').addEventListener('change', () => { $('lv-inj-box').disabled = !$('lv-inj').checked; });

  function fillLayers() {
    const L = layers(basis.value), keep = layerSel.value;
    layerSel.replaceChildren(...L.map((l, t) => {
      const o = document.createElement('option');
      o.value = t; o.textContent = `${t + 1}: ${l.phase}`;
      return o;
    }));
    // default: right after B is encoded, so the error meets the logical CNOT and the next check round
    layerSel.value = keep && keep < L.length ? keep : String(REF_LAYER);
  }
  basis.addEventListener('change', fillLayers);
  fillLayers();

  $('live-form').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const q = Math.max(0, Math.min(17, parseInt($('lv-q').value, 10) || 0));
    const inject = $('lv-inj').checked ? { pauli: $('lv-pauli').value, qubit: q, afterLayer: +layerSel.value } : null;
    const args = { shots: +shots.value, basis: basis.value, inject, p: +p.value, seed: 1 + Math.floor(Math.random() * 1e9) };
    $('lv-run').disabled = true;
    $('lv-status').textContent = 'Running...';
    setTimeout(() => {
      try {
        const t0 = performance.now();
        const res = runShots(args);
        $('lv-status').textContent = `${args.shots} shots in ${Math.round(performance.now() - t0)} ms.`;
        show(res, args);
      } catch (e) {
        console.error(e);
        $('lv-status').textContent = `Run failed: ${e.message}`;
      } finally {
        $('lv-run').disabled = false;
      }
    }, 30);
  });

  function show(res, args) {
    $('lv-stats').innerHTML = `
      <div class="card"><div class="big">${pct(res.agree)}</div><div class="lbl">the two logical bits agree (kept shots; ideal 100%)</div></div>
      <div class="card"><div class="big">${pct(res.discard)}</div><div class="lbl">discarded by the checks</div></div>`;
    const L = layers(args.basis);
    const ops = L.flatMap((l, t) => l.gates.map((g) => ({ ...g, t, phase: l.phase })));
    const heat = $('lv-heat');
    heat.replaceChildren();
    const W = LW + L.length * BW, H = 16 * RH + 4;
    heat.style.minWidth = `${W}px`;
    const strip = document.createElement('div');
    strip.className = 'strip';
    strip.style.marginLeft = `${(100 * LW) / W}%`;
    drawStrip(strip, L.map((l) => ({ phase: l.phase, gates: l.gates })), phasesOf(ops, L.length - 1), null, true);
    strip.style.width = `${(100 * (W - LW)) / W}%`;
    strip.style.minWidth = '';
    heat.appendChild(strip);
    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img', 'aria-label': 'Firing rate of each check in each round' }, heat);
    svg.style.display = 'block';
    for (let k = 0; k < 16; k++) {
      const y = k * RH + (k >= 8 ? 4 : 0);
      el('text', { x: LW - 6, y: y + RH - 4, class: 'hlab', 'text-anchor': 'end' }, svg).textContent = checkLabel(k);
      L.forEach((_, t) => {
        const row = res.checkRate[t];
        const v = row ? row[k] : null;
        const x = LW + t * BW;
        const cell = el('rect', { x: x + 1, y: y + 1, width: BW - 2, height: RH - 2 }, svg);
        if (v === null || v === undefined) {
          cell.setAttribute('class', 'und');
          el('title', {}, cell).textContent = `${checkLabel(k)}, layer ${t + 1}: not running`;
        } else {
          cell.setAttribute('fill', v > 0 ? 'var(--bad)' : 'var(--card)');
          cell.setAttribute('fill-opacity', v > 0 ? (0.15 + 0.85 * v).toFixed(3) : 1);
          cell.setAttribute('stroke', 'var(--line)');
          el('title', {}, cell).textContent = `${checkLabel(k)}, layer ${t + 1}: fired in ${pct(v)} of shots`;
        }
      });
    }
    if (args.inject) {
      const x = LW + (args.inject.afterLayer + 1) * BW;
      el('line', { x1: x, y1: 0, x2: x, y2: H, stroke: 'var(--bad)', 'stroke-width': 2.5, 'stroke-dasharray': '4 3' }, svg);
    }
    const leg = $('lv-legend');
    leg.hidden = false;
    leg.innerHTML = '<span class="sw sw-fire"></span> fires (share of shots) <span class="sw sw-off"></span> not checked yet' + (args.inject ? ' <span class="sw sw-inj"></span> injected error' : '');
  }
}
