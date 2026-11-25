/* The article pages' heroes (lib/article.css): a live figure behind the title
   of each paper, note, lesson and tool, in the homepage's manner. Each figure
   is one kind of field: dim structure past every edge, quiet near the words,
   warm for the highlighted thing (an error's checks, an erased qubit, a
   crossing), the accent for paths (a correction, a growing cluster, a check's
   reach) and ink for the rest. TP.live (lib/site.js) runs them at about 30 fps,
   only on screen and in a visible tab, as still frames under reduced motion.
   The cue under the words scrolls to the text below the hero. */
document.addEventListener("DOMContentLoaded", function(){
"use strict";
var heroes = document.querySelectorAll(".ar-hero");
var reduce = matchMedia("(prefers-reduced-motion: reduce)");

Array.prototype.forEach.call(heroes, function(hero){
  var cue = hero.querySelector(".ar-cue");
  if (!cue) return;
  cue.addEventListener("click", function(e){
    var bar = document.querySelector(".tp-bar"), to = document.getElementById(cue.getAttribute("href").slice(1));
    e.preventDefault();
    scrollTo({ top: hero.getBoundingClientRect().bottom + scrollY - (bar ? bar.offsetHeight : 0), behavior: reduce.matches ? "auto" : "smooth" });
    if (to) {
      if (!to.hasAttribute("tabindex") && !/^(A|BUTTON|INPUT|SELECT|TEXTAREA)$/.test(to.tagName)) to.setAttribute("tabindex", "-1");
      to.focus({ preventScroll: true });
    }
  });
});

if (!window.TP || !TP.live) return;
var live = TP.live, C = live.C, rgba = live.rgba, clamp = live.clamp, ss = live.ss;
function rnd(n){ return (Math.random() * n) | 0; }
function pick(a){ return a[rnd(a.length)]; }

/* the words over the figure as boxes in its canvas, each with how far the
   quiet reaches around it (the title block fully, the course row and the cue
   less), and a weight that is 1 away from them and about 0.08 on them */
function boxes(s){
  var c = s.cv.getBoundingClientRect(), out = [];
  [[".ar-text", 1], [".ar-in > nav", .45], [".ar-cue", .45]].forEach(function(q){
    var el = s.hero.querySelector(q[0]);
    if (!el) return;
    var r = el.getBoundingClientRect();
    if (r.width && r.height) out.push({ l: r.left - c.left, r: r.right - c.left, t: r.top - c.top, b: r.bottom - c.top, k: q[1] });
  });
  return out;
}
function calm(B, pad){
  return function(x, y){
    var m = 1;
    for (var i = 0; i < B.length; i++) {
      var b = B[i], dx = Math.max(b.l - x, 0, x - b.r), dy = Math.max(b.t - y, 0, y - b.b);
      m = Math.min(m, .08 + .92 * ss(0, pad * b.k, Math.hypot(dx, dy)));
    }
    return m;
  };
}
/* the centre of the room the words leave: beside them on a wide screen, above them otherwise */
function room(s, w, h){
  var b = boxes(s)[0];
  if (!b) return [w * .6, h * .45];
  if (w - b.r > w * .3) return [(b.r + w) / 2, h * .42];
  return [w * .55, Math.max(h * .2, b.t * .5)];
}
/* an offscreen canvas the size of the scene's, for the parts that do not move */
function layer(s){
  var L = s.layer || (s.layer = document.createElement("canvas"));
  L.width = s.cv.width; L.height = s.cv.height;
  var g = L.getContext("2d");
  g.setTransform(s.d, 0, 0, s.d, 0, 0);
  return g;
}
/* the static layer is erased through 1 - W, so it fades by the words on any ground */
function hush(g, W, w, h){
  var n = 8, cw = Math.ceil(w / n), ch = Math.ceil(h / n), m = document.createElement("canvas");
  m.width = cw; m.height = ch;
  var x = m.getContext("2d"), im = x.createImageData(cw, ch);
  for (var j = 0; j < ch; j++) for (var i = 0; i < cw; i++) im.data[(j * cw + i) * 4 + 3] = 255 * (1 - W((i + .5) * n, (j + .5) * n));
  x.putImageData(im, 0, 0);
  g.globalCompositeOperation = "destination-out"; g.drawImage(m, 0, 0, w, h); g.globalCompositeOperation = "source-over";
}
function segs(pts){ var o = []; for (var i = 1; i < pts.length; i++) o.push([pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]]); return o; }

/* an error event: the flipped qubits (ink: a stroke along the chain, a dot on
   each qubit), the two checks at its ends (warm), then the correction drawn
   segment by segment from one end to the other (accent) */
function evEnd(ev){ return 1.5 + ev.cor.length * .22 + 1.9; }
function drawEvent(g, ev, R){
  var a = ev.age, tc = 1.5 + ev.cor.length * .22, out = 1 - clamp((a - tc - .9) / .9), m = ev.m, k, s;
  var e = clamp(a / .3) * out * m;
  g.lineCap = "round";
  g.strokeStyle = rgba(C.ink, .8 * e); g.lineWidth = Math.min(2, R * .3);
  g.beginPath();
  for (k = 0; k < ev.err.length; k++) { s = ev.err[k]; g.moveTo(s[0], s[1]); g.lineTo(s[2], s[3]); }
  g.stroke();
  g.fillStyle = rgba(C.ink, e);
  for (k = 0; k < ev.err.length; k++) { s = ev.err[k]; g.beginPath(); g.arc((s[0] + s[2]) / 2, (s[1] + s[3]) / 2, R * .34, 0, 7); g.fill(); }
  var c = clamp((a - .45) / .25) * (1 - clamp((a - tc) / .35)) * m;
  if (c > 0) for (k = 0; k < 2; k++) {
    var p = ev.ends[k];
    if (ev.tile) {
      g.fillStyle = rgba(C.warm, .14 * c); g.fillRect(p[0] - ev.tile, p[1] - ev.tile, 2 * ev.tile, 2 * ev.tile);
      g.strokeStyle = rgba(C.warm, .55 * c); g.lineWidth = 1.25; g.strokeRect(p[0] - ev.tile, p[1] - ev.tile, 2 * ev.tile, 2 * ev.tile);
    } else {
      g.beginPath(); g.arc(p[0], p[1], R * 1.25, 0, 7);
      g.fillStyle = rgba(C.warm, .16 * c); g.fill();
      g.strokeStyle = rgba(C.warm, .6 * c); g.lineWidth = 1.25; g.stroke();
    }
    g.beginPath(); g.arc(p[0], p[1], R * .45, 0, 7); g.fillStyle = rgba(C.warm, c); g.fill();
  }
  g.strokeStyle = rgba(C.acc, out * m); g.lineWidth = Math.min(2.6, R * .38);
  g.beginPath();
  for (k = 0; k < ev.cor.length; k++) {
    var q = clamp((a - 1.5 - k * .22) / .22);
    if (q <= 0) break;
    s = ev.cor[k]; g.moveTo(s[0], s[1]); g.lineTo(s[0] + (s[2] - s[0]) * q, s[1] + (s[3] - s[1]) * q);
  }
  g.stroke();
}
/* a random walk of up to n steps from (i, j) inside ok(x, y) with the four
   steps D, and the correction: a shortest path between its two ends, one leg
   along D[0] or D[1], then one along D[2] or D[3] */
function walk(i, j, n, ok, D){
  var path = [[i, j]], seen = {}, x = i, y = j;
  seen[i + "," + j] = 1;
  for (var k = 0; k < n; k++) {
    var o = D.slice().sort(function(){ return Math.random() - .5; });
    for (var d = 0; d < 4; d++) {
      var nx = x + o[d][0], ny = y + o[d][1];
      if (!ok(nx, ny) || seen[nx + "," + ny]) continue;
      x = nx; y = ny; seen[x + "," + y] = 1; path.push([x, y]); break;
    }
  }
  return { path: path, x: x, y: y };
}
/* the shortest path on a square lattice (steps along x, then y, or the other way) */
function straight(i, j, x, y){
  var cor = [[i, j]], cx = i, cy = j, hx = Math.random() < .5;
  for (var leg = 0; leg < 2; leg++, hx = !hx)
    while (hx ? cx !== x : cy !== y) { if (hx) cx += x > cx ? 1 : -1; else cy += y > cy ? 1 : -1; cor.push([cx, cy]); }
  return cor;
}
/* a scene that keeps up to max error events alive, spawning one every gap seconds */
function events(s, gap){
  s.step = function(dt){
    s.ev.forEach(function(e){ e.age += dt; });
    s.ev = s.ev.filter(function(e){ return e.age < (s.end || evEnd)(e); });
    if ((s.next -= dt) <= 0 && s.ev.length < s.max) { s.spawn(0); s.next = gap + Math.random() * gap; }
  };
}
function far(s, x, y, d){ return !s.ev.some(function(e){ return Math.hypot(e.x - x, e.y - y) < d; }); }

var MAKE = {
  /* a rotated surface code: qubits on the corners of square tiles, the Z
     tiles shaded. An X error flips a chain of qubits, the Z tiles at its two
     ends fire, and the shortest chain between them is the correction. */
  patch: function(hero){
    var P = { still: 0, dpr: 1, ev: [], next: .5, hero: hero, end: evEnd };
    P.c = function(i, j){ return [P.ox + (i + .5) * P.S, P.oy + (j + .5) * P.S]; };
    P.setup = function(w, h){
      var S = P.S = w < 640 ? 36 : 48, i, j;
      P.cols = Math.ceil(w / S) + 2; P.rows = Math.ceil(h / S) + 2;
      P.ox = (w - P.cols * S) / 2; P.oy = (h - P.rows * S) / 2;
      P.W = calm(boxes(P), 3 * S);
      var g = layer(P);
      for (j = 0; j < P.rows; j++) for (i = 0; i < P.cols; i++) if (!((i + j) & 1)) {
        g.fillStyle = rgba(C.dim, .05); g.fillRect(P.ox + i * S, P.oy + j * S, S, S);
      }
      g.strokeStyle = rgba(C.dim, .2); g.lineWidth = 1; g.beginPath();
      for (i = 0; i <= P.cols; i++) { g.moveTo(P.ox + i * S, 0); g.lineTo(P.ox + i * S, h); }
      for (j = 0; j <= P.rows; j++) { g.moveTo(0, P.oy + j * S); g.lineTo(w, P.oy + j * S); }
      g.stroke();
      g.fillStyle = rgba(C.ink, .5);
      for (j = 0; j <= P.rows; j++) for (i = 0; i <= P.cols; i++) { g.beginPath(); g.arc(P.ox + i * S, P.oy + j * S, 1.7, 0, 7); g.fill(); }
      hush(g, P.W, w, h);
      P.max = w < 640 ? 2 : 4; P.ev = [];
      [1.9, .7, 2.8, 1.3].slice(0, P.max).forEach(function(a){ P.spawn(a); });
    };
    /* Z tiles are (i + j) even; a step to a diagonal neighbour crosses the qubit they share */
    var D = [[1, 1], [-1, -1], [1, -1], [-1, 1]];
    P.spawn = function(age){
      for (var tries = 0; tries < 40; tries++) {
        var i = 2 + rnd(P.cols - 4), j = 2 + rnd(P.rows - 4);
        if ((i + j) & 1) i++;
        var c = P.c(i, j);
        if (P.W(c[0], c[1]) < .9 || !far(P, c[0], c[1], P.S * 5)) continue;
        var ok = function(x, y){ var q = P.c(x, y); return x >= 1 && y >= 1 && x <= P.cols - 2 && y <= P.rows - 2 && P.W(q[0], q[1]) > .85; };
        var wk = walk(i, j, 1 + rnd(3), ok, D);
        if (wk.path.length < 2 || (wk.x === i && wk.y === j)) continue;
        /* the correction in the tiles' own diagonal axes: u = (i + j) / 2, v = (i - j) / 2 */
        var du = ((wk.x - i) + (wk.y - j)) / 2, dv = ((wk.x - i) - (wk.y - j)) / 2, cor = [[i, j]], x = i, y = j, k;
        for (k = 0; k < Math.abs(du); k++) { x += Math.sign(du); y += Math.sign(du); cor.push([x, y]); }
        for (k = 0; k < Math.abs(dv); k++) { x += Math.sign(dv); y -= Math.sign(dv); cor.push([x, y]); }
        if (!cor.every(function(q){ return ok(q[0], q[1]) || (q[0] === i && q[1] === j); })) continue;
        P.ev.push({ x: c[0], y: c[1], age: age, m: .5 + .5 * P.W(c[0], c[1]), tile: P.S * .5,
          err: segs(wk.path.map(function(q){ return P.c(q[0], q[1]); })),
          cor: segs(cor.map(function(q){ return P.c(q[0], q[1]); })),
          ends: [c, P.c(wk.x, wk.y)] });
        return;
      }
    };
    events(P, .7);
    P.draw = function(g, w, h){
      g.drawImage(P.layer, 0, 0, w, h);
      for (var k = 0; k < P.ev.length; k++) drawEvent(g, P.ev[k], P.S * .22);
    };
    return P;
  },

  /* repetition codes, one per row: qubits on the line, a check between each
     pair of neighbours. A run of flips lights the two checks at its ends, and
     the vote flips the run back. */
  rep: function(hero){
    var R = { still: 0, dpr: 1, ev: [], next: .4, hero: hero, end: evEnd };
    R.q = function(k, r){ return [R.ox + k * R.S, R.oy + r * R.G]; };  /* k integer: a check, k + .5: a qubit */
    R.setup = function(w, h){
      var S = R.S = w < 640 ? 34 : 44, G = R.G = S * 1.6, k, r;
      R.cols = Math.ceil(w / S) + 2; R.rows = Math.ceil(h / G) + 1;
      R.ox = (w - R.cols * S) / 2; R.oy = (h - (R.rows - 1) * G) / 2;
      R.W = calm(boxes(R), 3 * S);
      var g = layer(R);
      g.lineWidth = 1;
      for (r = 0; r < R.rows; r++) {
        var y = R.oy + r * G;
        g.strokeStyle = rgba(C.dim, .24); g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
        for (k = 0; k <= R.cols; k++) {
          var x = R.ox + k * S, d = 3.4;
          g.beginPath(); g.moveTo(x, y - d); g.lineTo(x + d, y); g.lineTo(x, y + d); g.lineTo(x - d, y); g.closePath();
          g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
          g.strokeStyle = rgba(C.dim, .5); g.stroke();
          g.beginPath(); g.arc(x + S / 2, y, 3, 0, 7);
          g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
          g.strokeStyle = rgba(C.ink, .55); g.stroke();
        }
      }
      hush(g, R.W, w, h);
      R.max = w < 640 ? 3 : 5; R.ev = [];
      [1.8, .6, 2.6, 1.2, .2].slice(0, R.max).forEach(function(a){ R.spawn(a); });
    };
    R.spawn = function(age){
      for (var tries = 0; tries < 40; tries++) {
        var r = rnd(R.rows), k = 1 + rnd(R.cols - 5), n = 1 + rnd(3), a = R.q(k, r), b = R.q(k + n, r);
        if (Math.min(R.W(a[0], a[1]), R.W(b[0], b[1]), R.W((a[0] + b[0]) / 2, a[1])) < .9 || !far(R, a[0], a[1], R.S * 5)) continue;
        var pts = []; for (var i = 0; i <= n; i++) pts.push(R.q(k + i, r));
        R.ev.push({ x: a[0], y: a[1], age: age, m: .55 + .45 * R.W(a[0], a[1]), err: segs(pts), cor: segs(pts), ends: [a, b] });
        return;
      }
    };
    events(R, .6);
    R.draw = function(g, w, h){
      g.drawImage(R.layer, 0, 0, w, h);
      for (var k = 0; k < R.ev.length; k++) drawEvent(g, R.ev[k], R.S * .2);
    };
    return R;
  },

  /* union-find decoding on a square lattice of checks: an error lights two
     checks, a cluster grows from each by half an edge at a time (accent), and
     where they meet the correction joins them */
  uf: function(hero){
    var U = { still: 0, dpr: 1, ev: [], next: .5, hero: hero };
    U.pt = function(i, j){ return [U.ox + i * U.S, U.oy + j * U.S]; };
    U.setup = function(w, h){
      var S = U.S = w < 640 ? 38 : 50, i, j;
      U.cols = Math.ceil(w / S) + 2; U.rows = Math.ceil(h / S) + 2;
      U.ox = (w - (U.cols - 1) * S) / 2; U.oy = (h - (U.rows - 1) * S) / 2;
      U.W = calm(boxes(U), 3 * S);
      var g = layer(U);
      g.strokeStyle = rgba(C.dim, .28); g.lineWidth = 1; g.beginPath();
      for (i = 0; i < U.cols; i++) { g.moveTo(U.ox + i * S, 0); g.lineTo(U.ox + i * S, h); }
      for (j = 0; j < U.rows; j++) { g.moveTo(0, U.oy + j * S); g.lineTo(w, U.oy + j * S); }
      g.stroke();
      g.fillStyle = rgba(C.ink, .55);
      for (j = 0; j < U.rows; j++) for (i = 0; i < U.cols; i++) { g.beginPath(); g.arc(U.ox + i * S, U.oy + j * S, 1.8, 0, 7); g.fill(); }
      hush(g, U.W, w, h);
      U.max = w < 640 ? 2 : 3; U.ev = [];
      [3.0, 1.2, 2.1].slice(0, U.max).forEach(function(a){ U.spawn(a); });
    };
    var D = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    U.spawn = function(age){
      for (var tries = 0; tries < 40; tries++) {
        var i = 2 + rnd(U.cols - 4), j = 2 + rnd(U.rows - 4), c = U.pt(i, j);
        if (U.W(c[0], c[1]) < .9 || !far(U, c[0], c[1], U.S * 6)) continue;
        var ok = function(x, y){ var q = U.pt(x, y); return x >= 1 && y >= 1 && x <= U.cols - 2 && y <= U.rows - 2 && U.W(q[0], q[1]) > .85; };
        var wk = walk(i, j, 2 + rnd(3), ok, D), dist = Math.abs(wk.x - i) + Math.abs(wk.y - j);
        if (dist < 2) continue;
        var cor = straight(i, j, wk.x, wk.y);
        U.ev.push({ x: c[0], y: c[1], age: age, m: .5 + .5 * U.W(c[0], c[1]), a: [i, j], b: [wk.x, wk.y], half: dist / 2,
          grow: .9 + dist * .35, err: segs(wk.path.map(function(q){ return U.pt(q[0], q[1]); })),
          cor: segs(cor.map(function(q){ return U.pt(q[0], q[1]); })), ends: [c, U.pt(wk.x, wk.y)] });
        return;
      }
    };
    /* the clusters grow for e.grow seconds to radius half the distance, then the
       correction draws as in an error event, shifted by the growth */
    U.end = function(e){ return e.grow + evEnd(e); };
    events(U, .9);
    U.draw = function(g, w, h){
      g.drawImage(U.layer, 0, 0, w, h);
      for (var n = 0; n < U.ev.length; n++) {
        var e = U.ev[n], a = e.age, t0 = .8, gr = clamp((a - t0) / (e.grow - t0)), fade = 1 - clamp((a - e.grow - 1.4) / 1.2);
        var r = gr * e.half, S = U.S;
        if (gr > 0 && fade > 0) {
          g.strokeStyle = rgba(C.acc, .45 * fade * e.m); g.lineWidth = 3; g.lineCap = "round";
          g.beginPath();
          [e.a, e.b].forEach(function(o){
            var R0 = Math.ceil(r);
            for (var dx = -R0; dx <= R0; dx++) for (var dy = -R0; dy <= R0; dy++) {
              var d0 = Math.abs(dx) + Math.abs(dy);
              if (d0 >= r) continue;
              var p = U.pt(o[0] + dx, o[1] + dy);
              [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function(s){
                var d1 = Math.abs(dx + s[0]) + Math.abs(dy + s[1]);
                if (d1 <= d0) return;
                var f = Math.min(1, r - d0);
                g.moveTo(p[0], p[1]); g.lineTo(p[0] + s[0] * S * f, p[1] + s[1] * S * f);
              });
            }
          });
          g.stroke();
        }
        /* the error and its checks from the start; the correction once the clusters meet */
        var shown = { age: a < e.grow ? Math.min(a, 1.4) : a - e.grow + 1.4, m: e.m, err: e.err, cor: e.cor, ends: e.ends };
        drawEvent(g, shown, S * .2);
      }
    };
    return U;
  },

  /* the logical error rate against the physical, on log axes: one line per
     distance, steeper as the distance grows, crossing near the threshold; the
     crossings of neighbouring pairs drift. A sweep in p marks where each
     curve stands; a crossing it passes lights warm. */
  curves: function(hero){
    var K = { still: 6, dpr: 1, hero: hero };
    /* the logical rate rises with p: up the screen to the right */
    K.y = function(Ln, x){ return K.y0 + Ln.c - Ln.m * (x - K.x0); };
    K.setup = function(w, h){
      var o = room(K, w, h);
      K.x0 = o[0]; K.y0 = o[1];
      K.W = calm(boxes(K), Math.min(w, h) * .14);
      var dec = K.dec = Math.max(90, Math.min(w, h) * .3), g = layer(K), x, y, k;
      /* log grid: decades and their 2..9 ticks, past every edge */
      g.lineWidth = 1;
      for (var axis = 0; axis < 2; axis++) {
        var L = axis ? h : w, o0 = axis ? K.y0 : K.x0;
        for (var d = -Math.ceil(o0 / dec) - 1; d * dec + o0 < L + dec; d++) for (k = 1; k < 10; k++) {
          var v = o0 + (d + Math.log10(k)) * dec;
          if (v < -1 || v > L + 1) continue;
          g.strokeStyle = rgba(C.dim, k === 1 ? .3 : .1);
          g.beginPath();
          if (axis) { g.moveTo(0, v); g.lineTo(w, v); } else { g.moveTo(v, 0); g.lineTo(v, h); }
          g.stroke();
        }
      }
      /* four distances, slopes (d + 1) / 2 in decades per decade, scaled to the screen; the crossing of
         each neighbouring pair moves a little along p */
      var sl = Math.min(.5, h / w * .55);
      K.lines = []; var c = 0;
      [3, 5, 7, 9].forEach(function(dd, i){
        var m = (dd + 1) / 2 * sl;
        if (i) c += (m - K.lines[i - 1].m) * (i - 2) * dec * .09;
        K.lines.push({ d: dd, m: m, c: c });
      });
      K.cross = [];
      for (k = 0; k + 1 < K.lines.length; k++) {
        var A = K.lines[k], B = K.lines[k + 1], X = (B.c - A.c) / (B.m - A.m);
        K.cross.push([K.x0 + X, K.y0 + A.c - A.m * X]);
      }
      K.lines.forEach(function(Ln, i){
        g.strokeStyle = rgba(C.ink, .22 + .1 * i); g.lineWidth = 1.4; g.beginPath();
        for (x = -10; x <= w + 10; x += 6) { y = K.y(Ln, x); if (x === -10) g.moveTo(x, y); else g.lineTo(x, y); }
        g.stroke();
      });
      hush(g, K.W, w, h);
      K.span = w * 1.1;
    };
    K.draw = function(g, w, h, t){
      g.drawImage(K.layer, 0, 0, w, h);
      var per = 16, u = (t % per) / per, xs = -w * .05 + u * K.span, fade = ss(0, .06, u) * ss(1, .9, u), k;
      /* samples left behind by the sweep, every 46px, with error bars that shrink with the run */
      var step = 46;
      for (var x = step / 2; x < Math.min(xs, w); x += step) {
        var age = (xs - x) / K.span;
        K.lines.forEach(function(Ln){
          var y = K.y(Ln, x), wt = K.W(x, y);
          if (y < -10 || y > h + 10 || wt < .3) return;
          var a = .55 * fade * wt, e = 10 * (1 - ss(0, .5, age)) + 2;
          g.strokeStyle = rgba(C.ink, a); g.lineWidth = 1;
          g.beginPath(); g.moveTo(x, y - e); g.lineTo(x, y + e); g.stroke();
          g.fillStyle = rgba(C.ink, a); g.beginPath(); g.arc(x, y, 2.2, 0, 7); g.fill();
        });
      }
      /* the sweep */
      if (xs > 0 && xs < w) {
        g.strokeStyle = rgba(C.acc, .35 * fade); g.lineWidth = 1;
        g.beginPath(); g.moveTo(xs, 0); g.lineTo(xs, h); g.stroke();
        K.lines.forEach(function(Ln){
          var y = K.y(Ln, xs), wt = K.W(xs, y);
          g.fillStyle = rgba(C.acc, fade * wt); g.beginPath(); g.arc(xs, y, 3.4, 0, 7); g.fill();
        });
      }
      /* the crossings, lit once the sweep has passed them */
      for (k = 0; k < K.cross.length; k++) {
        var p = K.cross[k], lit = ss(0, 40, xs - p[0]) * fade * K.W(p[0], p[1]);
        if (lit <= 0) continue;
        g.beginPath(); g.arc(p[0], p[1], 9, 0, 7);
        g.fillStyle = rgba(C.warm, .14 * lit); g.fill();
        g.strokeStyle = rgba(C.warm, .6 * lit); g.lineWidth = 1.25; g.stroke();
        g.beginPath(); g.arc(p[0], p[1], 3, 0, 7); g.fillStyle = rgba(C.warm, lit); g.fill();
      }
    };
    return K;
  },

  /* a graph of thoughts down the hero: each thought leads to one or two in the
     next layer. A query expands layer by layer (accent); a thought judged
     complex (warm) opens a small nested graph of its own before it answers. */
  graph: function(hero){
    var G = { still: 2.6, dpr: 1, ev: [], next: .4, hero: hero };
    function near(x, list){ return list.slice().sort(function(a, b){ return Math.abs(G.n[a].x - x) - Math.abs(G.n[b].x - x); }); }
    G.setup = function(w, h){
      var s = G.s = w < 640 ? 44 : 58, i, j;
      var rows = Math.ceil(h / s) + 2, cols = Math.ceil(w / s) + 2, ox = (w - (cols - 1) * s) / 2, oy = (h - (rows - 1) * s) / 2;
      G.W = calm(boxes(G), 2.5 * s);
      G.n = []; G.row = [];
      for (j = 0; j < rows; j++) {
        var R = [];
        for (i = 0; i < cols; i++) if (Math.random() < .68) {
          R.push(G.n.length);
          G.n.push({ x: ox + (i + (j & 1 ? .25 : -.25) + (Math.random() - .5) * .5) * s, y: oy + (j + (Math.random() - .5) * .3) * s, out: [] });
        }
        G.row.push(R);
      }
      for (j = 0; j + 1 < rows; j++) {
        var A = G.row[j], B = G.row[j + 1];
        A.forEach(function(u){
          var c = near(G.n[u].x, B);
          if (c.length) G.n[u].out.push(c[0]);
          if (c.length > 1 && Math.random() < .45 && Math.abs(G.n[c[1]].x - G.n[u].x) < 1.6 * s) G.n[u].out.push(c[1]);
        });
        B.forEach(function(v){
          if (!A.some(function(u){ return G.n[u].out.indexOf(v) >= 0; })) { var u = near(G.n[v].x, A)[0]; if (u != null) G.n[u].out.push(v); }
        });
      }
      var g = layer(G);
      g.strokeStyle = rgba(C.dim, .3); g.lineWidth = 1; g.beginPath();
      G.n.forEach(function(a){ a.out.forEach(function(v){ g.moveTo(a.x, a.y); g.lineTo(G.n[v].x, G.n[v].y); }); });
      g.stroke();
      G.n.forEach(function(a){
        g.beginPath(); g.arc(a.x, a.y, 3, 0, 7);
        g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
        g.strokeStyle = rgba(C.ink, .5); g.stroke();
      });
      hush(g, G.W, w, h);
      G.max = w < 640 ? 2 : 4; G.ev = [];
      [2.7, .8, 3.6, 1.6].slice(0, G.max).forEach(function(a){ G.spawn(a); });
    };
    G.spawn = function(age){
      var w = G.w, h = G.h;
      for (var tries = 0; tries < 40; tries++) {
        var a = rnd(G.n.length), A = G.n[a];
        if (A.x < w * .05 || A.x > w * .95 || A.y < h * .04 || A.y > h * .62) continue;
        if (G.W(A.x, A.y) < .9 || !far(G, A.x, A.y, G.s * 4)) continue;
        var D = 3, front = [a], E = [], seen = {}, ok = true, cx = -1;
        seen[a] = 1;
        for (var d = 0; d < D && ok && front.length; d++) {
          var nf = [];
          front.forEach(function(u){
            var o = G.n[u].out.slice().sort(function(){ return Math.random() - .5; }), take = o.length > 1 && front.length < 3 && Math.random() < .55 ? 2 : 1;
            for (var q = 0; q < Math.min(take, o.length); q++) { E.push([u, o[q], d]); if (!seen[o[q]]) { seen[o[q]] = 1; nf.push(o[q]); } }
          });
          ok = nf.every(function(v){ return G.W(G.n[v].x, G.n[v].y) > .8 && G.n[v].y < h - 8; });
          if (d === 0 && nf.length) cx = pick(nf);
          front = nf;
        }
        if (!ok || !front.length || cx < 0) continue;
        G.ev.push({ x: A.x, y: A.y, a: a, age: age, E: E, end: front, cx: cx, rot: Math.random() * 6.3 });
        return;
      }
    };
    /* layer d draws from 1 + 0.5 d s; the complex thought's nested graph opens at 1.5 s and answers by 3 s */
    function tEnd(){ return 1 + 3 * .5 + 1.4 + 2.4; }
    G.step = function(dt){
      G.ev.forEach(function(e){ e.age += dt; });
      G.ev = G.ev.filter(function(e){ return e.age < tEnd(e); });
      if ((G.next -= dt) <= 0 && G.ev.length < G.max) { G.spawn(0); G.next = .8 + Math.random() * 1.1; }
    };
    G.draw = function(g, w, h){
      g.drawImage(G.layer, 0, 0, w, h);
      G.ev.forEach(function(e){
        var a = e.age, out = 1 - clamp((a - tEnd(e) + 1.2) / 1.2), k;
        g.lineCap = "round";
        e.E.forEach(function(ed){
          var q = clamp((a - 1 - ed[2] * .5 - (ed[2] > 0 ? 1.1 : 0)) / .45);
          if (q <= 0) return;
          var A = G.n[ed[0]], B = G.n[ed[1]];
          g.strokeStyle = rgba(C.acc, .9 * out); g.lineWidth = 2;
          g.beginPath(); g.moveTo(A.x, A.y); g.lineTo(A.x + (B.x - A.x) * q, A.y + (B.y - A.y) * q); g.stroke();
        });
        /* the query */
        var A0 = G.n[e.a], f = clamp(a / .4) * out;
        g.fillStyle = rgba(C.ink, f); g.beginPath(); g.arc(A0.x, A0.y, 4.2, 0, 7); g.fill();
        /* the complex thought and its nested graph */
        var X = G.n[e.cx], c = clamp((a - 1.45) / .3) * out, r = G.s * .42;
        if (c > 0) {
          g.beginPath(); g.arc(X.x, X.y, r, 0, 7);
          g.fillStyle = rgba(C.warm, .1 * c); g.fill();
          g.strokeStyle = rgba(C.warm, .55 * c); g.lineWidth = 1.25; g.stroke();
          var pts = [];
          for (k = 0; k < 3; k++) pts.push([X.x + Math.cos(e.rot + k * 2.09) * r * .55, X.y + Math.sin(e.rot + k * 2.09) * r * .55]);
          var in2 = clamp((a - 1.75) / .5) * out;
          g.strokeStyle = rgba(C.warm, .7 * in2); g.lineWidth = 1;
          g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); g.lineTo(pts[1][0], pts[1][1]); g.lineTo(pts[2][0], pts[2][1]); g.stroke();
          g.fillStyle = rgba(C.warm, in2);
          pts.forEach(function(p){ g.beginPath(); g.arc(p[0], p[1], 2.2, 0, 7); g.fill(); });
        }
        g.fillStyle = rgba(C.warm, c); g.beginPath(); g.arc(X.x, X.y, 3.4, 0, 7); g.fill();
        /* the answers at the last layer */
        var fin = clamp((a - 1 - 3 * .5 - 1.1) / .4) * out;
        if (fin > 0) e.end.forEach(function(v){
          var B = G.n[v];
          g.beginPath(); g.arc(B.x, B.y, 5.5, 0, 7); g.strokeStyle = rgba(C.ink, fin); g.lineWidth = 1.4; g.stroke();
          g.fillStyle = rgba(C.ink, fin); g.beginPath(); g.arc(B.x, B.y, 2.4, 0, 7); g.fill();
        });
      });
    };
    return G;
  },

  /* surface code patches side by side with a free column between them. A
     merge fills a run of the seam with new checks (accent) whose outcomes
     appear one by one (ink for +1, warm for -1), then the patches split. */
  surgery: function(hero){
    var M = { still: 2.2, dpr: 1, ev: [], next: .4, hero: hero };
    M.setup = function(w, h){
      var S = M.S = w < 640 ? 32 : 42, i, j, P = M.P = w < 640 ? 4 : 6;
      M.cols = Math.ceil(w / S) + 2; M.rows = Math.ceil(h / S) + 2;
      M.ox = (w - M.cols * S) / 2; M.oy = (h - M.rows * S) / 2;
      M.W = calm(boxes(M), 3 * S);
      var g = layer(M), seam = function(i){ return (i % (P + 1)) === P; };
      for (j = 0; j < M.rows; j++) for (i = 0; i < M.cols; i++) {
        var x = M.ox + i * S, y = M.oy + j * S;
        if (seam(i)) continue;
        if (!((i + j) & 1)) { g.fillStyle = rgba(C.dim, .05); g.fillRect(x, y, S, S); }
        g.strokeStyle = rgba(C.dim, .2); g.lineWidth = 1; g.strokeRect(x + .5, y + .5, S, S);
      }
      for (i = 0; i < M.cols; i++) if (seam(i)) {
        var sx = M.ox + (i + .5) * S;
        g.setLineDash([2, 5]); g.strokeStyle = rgba(C.dim, .4); g.beginPath(); g.moveTo(sx, 0); g.lineTo(sx, h); g.stroke(); g.setLineDash([]);
      }
      g.fillStyle = rgba(C.ink, .5);
      for (j = 0; j <= M.rows; j++) for (i = 0; i <= M.cols; i++) if (!seam(i) || !seam(i - 1)) {
        g.beginPath(); g.arc(M.ox + i * S, M.oy + j * S, 1.6, 0, 7); g.fill();
      }
      hush(g, M.W, w, h);
      M.seams = []; for (i = 0; i < M.cols; i++) if (seam(i)) M.seams.push(i);
      M.max = w < 640 ? 1 : 3; M.ev = [];
      [2.3, .9, 3.4].slice(0, M.max).forEach(function(a){ M.spawn(a); });
    };
    M.spawn = function(age){
      for (var tries = 0; tries < 40; tries++) {
        var i = pick(M.seams), n = 3 + rnd(3), j = 1 + rnd(Math.max(1, M.rows - n - 2));
        var x = M.ox + (i + .5) * M.S, y0 = M.oy + j * M.S, ok = true;
        for (var k = 0; k <= n; k++) if (M.W(x, y0 + k * M.S) < .9) ok = false;
        if (!ok || !far(M, x, y0, M.S * 6)) continue;
        var out = []; for (k = 0; k < n; k++) out.push(Math.random() < .3);
        M.ev.push({ x: x, y: y0, i: i, j: j, n: n, out: out, age: age });
        return;
      }
    };
    function mEnd(e){ return .6 + e.n * .35 + 2.6; }
    M.step = function(dt){
      M.ev.forEach(function(e){ e.age += dt; });
      M.ev = M.ev.filter(function(e){ return e.age < mEnd(e); });
      if ((M.next -= dt) <= 0 && M.ev.length < M.max) { M.spawn(0); M.next = 1 + Math.random() * 1.2; }
    };
    M.draw = function(g, w, h){
      g.drawImage(M.layer, 0, 0, w, h);
      var S = M.S;
      M.ev.forEach(function(e){
        var a = e.age, out = 1 - clamp((a - mEnd(e) + 1.1) / 1.1), x = M.ox + e.i * S, k;
        /* the two facing edges, joined for the merge */
        var j0 = clamp(a / .5) * out;
        g.strokeStyle = rgba(C.acc, .75 * j0); g.lineWidth = 2; g.lineCap = "round";
        g.beginPath();
        g.moveTo(x, e.y); g.lineTo(x, e.y + e.n * S * j0);
        g.moveTo(x + S, e.y); g.lineTo(x + S, e.y + e.n * S * j0);
        g.stroke();
        for (k = 0; k < e.n; k++) {
          var q = clamp((a - .6 - k * .35) / .3) * out, y = e.y + k * S;
          if (q <= 0) break;
          g.fillStyle = rgba(C.acc, .16 * q); g.fillRect(x, y, S, S);
          g.strokeStyle = rgba(C.acc, .5 * q); g.lineWidth = 1; g.strokeRect(x + .5, y + .5, S - 1, S - 1);
          var cx = x + S / 2, cy = y + S / 2, col = e.out[k] ? C.warm : C.ink;
          if (e.out[k]) { g.beginPath(); g.arc(cx, cy, S * .3, 0, 7); g.fillStyle = rgba(C.warm, .14 * q); g.fill(); }
          g.beginPath(); g.arc(cx, cy, 3.2, 0, 7); g.fillStyle = rgba(col, q); g.fill();
        }
      });
    };
    return M;
  },

  /* a bivariate bicycle code on its torus, the gross code: l = 12, m = 6,
     A = x^3 + y + y^2, B = y^3 + x + x^2. Each cell holds a left and a right
     qubit; a check at a cell acts on the left qubits A takes it to and the
     right qubits B takes it to, so its six lines reach up to three cells. */
  bb: function(hero){ return bbScene(hero, false); },
  /* the same code under erasure: qubits are lost at known places (warm), and
     the checks that touch them, the ones the decoder reads, light (accent) */
  erasure: function(hero){ return bbScene(hero, true); }
};
var BB_A = [[3, 0], [0, 1], [0, 2]], BB_B = [[0, 3], [1, 0], [2, 0]], BB_L = 12, BB_M = 6;
function bbScene(hero, erase){
  var Q = { still: 2, dpr: 1, ev: [], next: .4, hero: hero };
  Q.L = function(i, j){ return [Q.ox + i * Q.S, Q.oy + j * Q.S]; };
  Q.R = function(i, j){ return [Q.ox + (i + .5) * Q.S, Q.oy + (j + .5) * Q.S]; };
  Q.X = function(i, j){ return [Q.ox + (i + .5) * Q.S, Q.oy + j * Q.S]; };
  Q.setup = function(w, h){
    var S = Q.S = w < 640 ? 30 : 40, i, j;
    Q.cols = Math.ceil(w / S) + 2; Q.rows = Math.ceil(h / S) + 2;
    Q.ox = (w - (Q.cols - 1) * S) / 2; Q.oy = (h - (Q.rows - 1) * S) / 2;
    Q.W = calm(boxes(Q), 3 * S);
    var g = layer(Q);
    /* the cells, and the edges of each copy of the 12 by 6 torus a little stronger */
    g.lineWidth = 1;
    for (i = 0; i < Q.cols; i++) { g.strokeStyle = rgba(C.dim, i % BB_L ? .14 : .4); g.beginPath(); g.moveTo(Q.ox + i * S, 0); g.lineTo(Q.ox + i * S, h); g.stroke(); }
    for (j = 0; j < Q.rows; j++) { g.strokeStyle = rgba(C.dim, j % BB_M ? .14 : .4); g.beginPath(); g.moveTo(0, Q.oy + j * S); g.lineTo(w, Q.oy + j * S); g.stroke(); }
    for (j = 0; j < Q.rows; j++) for (i = 0; i < Q.cols; i++) {
      var p = Q.L(i, j), r = Q.R(i, j);
      g.fillStyle = rgba(C.ink, .5); g.beginPath(); g.arc(p[0], p[1], 1.8, 0, 7); g.fill();
      g.beginPath(); g.arc(r[0], r[1], 2.2, 0, 7);
      g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
      g.strokeStyle = rgba(C.ink, .4); g.stroke();
    }
    hush(g, Q.W, w, h);
    Q.max = w < 640 ? 2 : 3; Q.ev = [];
    [2.1, .7, 3.0].slice(0, Q.max).forEach(function(a){ Q.spawn(a); });
  };
  function inside(p){ return Q.W(p[0], p[1]) > .85 && p[0] > 4 && p[1] > 4 && p[0] < Q.w - 4 && p[1] < Q.h - 4; }
  /* the six qubits of the check at (i, j), as points */
  function reach(i, j){
    return BB_A.map(function(o){ return Q.L(i + o[0], j + o[1]); }).concat(BB_B.map(function(o){ return Q.R(i + o[0], j + o[1]); }));
  }
  Q.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(Q.cols - 5), j = 1 + rnd(Q.rows - 5), c = Q.X(i, j), lines = [], lost = [];
      if (!inside(c) || !far(Q, c[0], c[1], Q.S * 6)) continue;
      if (!erase) {
        var r = reach(i, j);
        if (!r.every(inside)) continue;
        r.forEach(function(p){ lines.push([c, p]); });
        Q.ev.push({ x: c[0], y: c[1], age: age, hub: [c], lines: lines, lost: [] });
        return;
      }
      /* two or three erased left qubits near (i, j); each is touched by the three checks A maps onto it */
      var n = 2 + rnd(2), ok = true, hubs = [];
      for (var k = 0; k < n && ok; k++) {
        var qi = i + rnd(3), qj = j + rnd(3), q = Q.L(qi, qj);
        if (!inside(q) || lost.some(function(p){ return p[0] === q[0] && p[1] === q[1]; })) { ok = false; break; }
        lost.push(q);
        BB_A.forEach(function(o){ var x = Q.X(qi - o[0], qj - o[1]); if (!inside(x)) ok = false; lines.push([x, q]); hubs.push(x); });
      }
      if (!ok) continue;
      Q.ev.push({ x: c[0], y: c[1], age: age, hub: hubs, lines: lines, lost: lost });
      return;
    }
  };
  function qEnd(){ return 4.6; }
  Q.step = function(dt){
    Q.ev.forEach(function(e){ e.age += dt; });
    Q.ev = Q.ev.filter(function(e){ return e.age < qEnd(e); });
    if ((Q.next -= dt) <= 0 && Q.ev.length < Q.max) { Q.spawn(0); Q.next = .9 + Math.random() * 1.1; }
  };
  Q.draw = function(g, w, h){
    g.drawImage(Q.layer, 0, 0, w, h);
    var S = Q.S;
    Q.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.4) / 1.2), f = clamp(a / .4) * out, q = clamp((a - .5) / .9) * out;
      var W = function(p){ return Q.W(p[0], p[1]); };
      /* erased qubits first, then the checks' lines; a plain check: the check, then its reach */
      e.lost.forEach(function(p){
        g.strokeStyle = rgba(C.warm, f * W(p)); g.lineWidth = 1.5; g.strokeRect(p[0] - S * .2, p[1] - S * .2, S * .4, S * .4);
        g.fillStyle = rgba(C.warm, .2 * f * W(p)); g.fillRect(p[0] - S * .2, p[1] - S * .2, S * .4, S * .4);
      });
      g.lineCap = "round"; g.lineWidth = 1.6;
      e.lines.forEach(function(l){
        var A = l[0], B = l[1];
        if (e.lost.length) { var t = A; A = B; B = t; }
        g.strokeStyle = rgba(C.acc, .8 * out * Math.min(W(A), W(B)));
        g.beginPath(); g.moveTo(A[0], A[1]); g.lineTo(A[0] + (B[0] - A[0]) * q, A[1] + (B[1] - A[1]) * q); g.stroke();
        if (q >= 1) { g.fillStyle = rgba(C.acc, out * W(B)); g.beginPath(); g.arc(B[0], B[1], 2.8, 0, 7); g.fill(); }
      });
      if (!e.lost.length) e.hub.forEach(function(p){
        g.fillStyle = rgba(C.warm, .16 * f); g.beginPath(); g.arc(p[0], p[1], S * .32, 0, 7); g.fill();
        g.fillStyle = rgba(C.warm, f); g.fillRect(p[0] - 3.5, p[1] - 3.5, 7, 7);
      });
    });
  };
  return Q;
}

Array.prototype.forEach.call(heroes, function(hero){
  var cv = hero.querySelector("canvas.ar-viz"), make = MAKE[hero.getAttribute("data-art")];
  if (!cv || !make) return;
  var s = live.add(cv, make(hero));
  /* the quiet around the words follows them once Geist has loaded */
  if (s && document.fonts && document.fonts.ready) document.fonts.ready.then(function(){
    if (!s.w) return;
    s.setup(s.w, s.h);
    if (reduce.matches) { s.g.setTransform(s.d, 0, 0, s.d, 0, 0); s.g.clearRect(0, 0, s.w, s.h); s.draw(s.g, s.w, s.h, s.still || 0); }
  });
});
});
