/* The site switch and nav, shared by every page. The pre-paint snippet in <head> has already put
   data-pref and data-theme on <html>; this keeps them in step. */
(function(){
"use strict";
var d = document.documentElement;
var mq = matchMedia("(prefers-color-scheme: light)");

/* one-time move of the book editions' old key onto the site key */
try{
  var old = localStorage.getItem("qd-theme");
  if (old !== null) {
    if (localStorage.getItem("tp-theme") === null && (old === "light" || old === "dark")) {
      localStorage.setItem("tp-theme", old);
      d.dataset.pref = old;
    }
    localStorage.removeItem("qd-theme");
  }
}catch(e){}

var PREF = d.dataset.pref || "auto";
var toggles = document.querySelectorAll(".tp-toggle");

function say(){
  var g = PREF === "auto" ? "\u25d0" : PREF === "light" ? "\u263c" : "\u263d";
  var w = PREF === "auto" ? "Auto" : PREF === "light" ? "Light" : "Dark";
  for (var i = 0; i < toggles.length; i++) {
    var t = toggles[i];
    t.innerHTML = '<b aria-hidden="true">' + g + "</b><span>" + w + "</span>";
    t.setAttribute("aria-label",
      "Theme: " + w + (PREF === "auto" ? " (following your system)" : "") + ". Click to change.");
  }
}
function apply(tell){
  var light = PREF === "auto" ? mq.matches : PREF === "light";
  var theme = light ? "light" : "dark";
  var was = d.dataset.theme;
  d.dataset.theme = theme;
  d.dataset.pref = PREF;
  var mt = document.querySelector('meta[name="theme-color"]');
  if (mt) mt.setAttribute("content", light ? "#f7f4ed" : "#0d1320");
  say();
  if (tell || was !== theme) {
    document.dispatchEvent(new CustomEvent("tp-theme", { detail: { theme: theme, pref: PREF } }));
  }
}
apply(false);

for (var i = 0; i < toggles.length; i++) {
  toggles[i].addEventListener("click", function(){
    PREF = PREF === "auto" ? "light" : PREF === "light" ? "dark" : "auto";
    try { localStorage.setItem("tp-theme", PREF); } catch(e){}
    apply(true);
  });
}
if (mq.addEventListener) {
  mq.addEventListener("change", function(){ if (PREF === "auto") apply(true); });
}

/* the current page in the nav: an exact path, or any page inside a section
   whose link ends in a slash */
var here = location.pathname.replace(/index\.html$/, "");
var navs = document.querySelectorAll(".tp-nav");
for (var n = 0; n < navs.length; n++) {
  var nav = navs[n], links = nav.querySelectorAll("a"), cur = null;
  for (var j = 0; j < links.length; j++) {
    var u = new URL(links[j].getAttribute("href"), location.href);
    if (u.hash || u.origin !== location.origin) continue;
    var p = u.pathname.replace(/index\.html$/, "");
    if (p === here || (p !== "/" && p.slice(-1) === "/" && here.indexOf(p) === 0)) {
      links[j].setAttribute("aria-current", "page"); cur = links[j];
    }
  }
  if (cur && nav.scrollWidth > nav.clientWidth) {
    nav.scrollLeft = cur.offsetLeft - (nav.clientWidth - cur.offsetWidth) / 2;
  }
  var edge = function(nav){ return function(){
    if (nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 2) nav.setAttribute("data-end", "");
    else nav.removeAttribute("data-end");
  }; }(nav);
  nav.addEventListener("scroll", edge, { passive: true });
  window.addEventListener("resize", edge, { passive: true });
  edge();
}

/* the footer year: a button that reads like the text around it; pressed, an even
   year shows itself as a sum of two primes, one of them in a twin pair */
function prime(n){ if (n < 2) return false; for (var k = 2; k * k <= n; k++) if (n % k === 0) return false; return true; }
function twin(n){ return prime(n) && (prime(n - 2) || prime(n + 2)); }
var fp = document.querySelector("footer.tp-foot > p"), tn = fp && fp.firstChild;
var ym = tn && tn.nodeType === 3 && /\d{4}/.exec(tn.data), Y = ym ? +ym[0] : 1, sum = null;
for (var a = 2; Y % 2 === 0 && a <= Y / 2 && !sum; a++)
  if (prime(a) && prime(Y - a) && (twin(a) || twin(Y - a))) sum = Y + " = " + a + " + " + (Y - a);
if (sum) {
  var st = document.createElement("style");
  st.textContent = ".tp-foot .tp-yr{font:inherit;color:inherit;letter-spacing:inherit;line-height:inherit;" +
    "text-transform:inherit;background:none;border:0;border-radius:0;padding:0;margin:0;cursor:text;-webkit-appearance:none;appearance:none}";
  document.head.appendChild(st);
  var yr = tn.splitText(ym.index), yb = document.createElement("button");
  yr.splitText(4);
  yb.type = "button"; yb.className = "tp-yr"; yb.textContent = String(Y);
  yb.setAttribute("aria-label", "Year " + Y);
  yr.parentNode.replaceChild(yb, yr);
  yb.addEventListener("click", function(){
    yb.textContent = yb.textContent === String(Y) ? sum : String(Y);
    yb.setAttribute("aria-label", "Year " + yb.textContent);
  });
}

/* for whoever opens the console */
console.log([
  "A repetition code: nineteen bits, each with a letter. A check reads 1 where its two neighbours differ.",
  "  k e l o w r t g s u i c n f a b m l x",
  "   0 1 0 1 0 0 1 1 0 1 0 1 0 1 1 0 1 1",
  "Some bits flipped; assume as few as the checks allow. The flipped letters spell a path on this site."
].join("\n"));
})();

/* TP.live: light canvas animation for any page. TP.live.add(canvas, scene)
   registers a scene {still, dpr, setup(w, h), step(dt), draw(g, w, h, t)}. A
   scene is sized and drawn once it comes within a window of the screen, so its
   first raster happens off screen. One loop at about 30 fps paints only scenes
   on screen, stops in a hidden tab, runs only the scenes inside an open sheet
   while one is open, and under reduced motion paints each once at t = still. TP.live.C holds the --tp-
   colours (hex), kept current across theme changes; TP.live.rgba(hex, a)
   tints one. */
(function(){
"use strict";
var TP = window.TP = window.TP || {};
var still = matchMedia("(prefers-reduced-motion: reduce)");
var C = {}, scenes = [], raf = 0, last = 0, io = null, near = null, ro = null, top = null;
function colors(){
  var cs = getComputedStyle(document.documentElement);
  ["acc", "warm", "ink", "dim", "rule", "void", "void2"].forEach(function(k){ C[k] = cs.getPropertyValue("--tp-" + k).trim(); });
}
function rgba(h, a){ var n = parseInt(h.slice(1), 16); return "rgba(" + (n >> 16) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + Math.max(0, Math.min(1, a)).toFixed(3) + ")"; }
function clamp(x){ return x < 0 ? 0 : x > 1 ? 1 : x; }
function ss(a, b, x){ var t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); }
function find(cv){ for (var i = 0; i < scenes.length; i++) if (scenes[i].cv === cv) return scenes[i]; }
function size(s){
  if (!s.near) return;
  var r = s.cv.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, s.dpr || 2);
  if (!r.width || !r.height) return;
  s.w = r.width; s.h = r.height; s.d = d;
  s.cv.width = Math.round(s.w * d); s.cv.height = Math.round(s.h * d);
  if (s.setup) s.setup(s.w, s.h);
  paint(s);
}
function paint(s){
  if (!s.w) return;
  s.g.setTransform(s.d, 0, 0, s.d, 0, 0);
  s.g.clearRect(0, 0, s.w, s.h);
  s.draw(s.g, s.w, s.h, still.matches ? s.still || 0 : s.t);
}
function awake(s){ return s.on && (!top || top.contains(s.cv)); }
function running(){
  if (document.hidden || still.matches) return false;
  for (var i = 0; i < scenes.length; i++) if (awake(scenes[i])) return true;
  return false;
}
function kick(){ if (!raf && running()) { last = 0; raf = requestAnimationFrame(tick); } }
function tick(now){
  raf = 0;
  if (!running()) return;
  raf = requestAnimationFrame(tick);
  if (last && now - last < 32) return;
  var dt = last ? Math.min(now - last, 100) / 1000 : 0;
  last = now;
  for (var i = 0; i < scenes.length; i++) {
    var s = scenes[i];
    if (!awake(s)) continue;
    s.t += dt;
    if (s.step) s.step(dt);
    paint(s);
  }
}
/* the sheet events do not bubble; catch them on the way down */
function sheet(){ top = document.querySelector("dialog.tp-sheet[open]"); kick(); }
function add(cv, s){
  if (!cv || !window.IntersectionObserver || !window.ResizeObserver) return null;
  if (!io) {
    colors();
    /* on screen means in the window below the sticky header, not just touching it */
    var bar = document.querySelector(".tp-bar"), cut = (bar ? bar.offsetHeight : 0) + 2;
    io = new IntersectionObserver(function(es){
      es.forEach(function(e){ var s = find(e.target); if (s) s.on = e.isIntersecting; });
      kick();
    }, { rootMargin: "-" + cut + "px 0px -2px" });
    near = new IntersectionObserver(function(es){
      es.forEach(function(e){ var s = find(e.target); if (s && e.isIntersecting && !s.near) { s.near = true; size(s); } });
    }, { rootMargin: "100% 0px" });
    ro = new ResizeObserver(function(es){ es.forEach(function(e){ var s = find(e.target); if (s) size(s); }); });
    document.addEventListener("visibilitychange", kick);
    document.addEventListener("tp-sheet-open", sheet, true);
    document.addEventListener("tp-sheet-close", sheet, true);
    document.addEventListener("tp-theme", function(){ colors(); scenes.forEach(size); });
    if (still.addEventListener) still.addEventListener("change", function(){ scenes.forEach(paint); kick(); });
  }
  s.cv = cv; s.g = cv.getContext("2d"); s.t = s.still || 0; s.on = false; s.near = false; s.w = 0;
  scenes.push(s); ro.observe(cv); io.observe(cv); near.observe(cv);
  return s;
}
TP.live = { add: add, C: C, rgba: rgba, clamp: clamp, ss: ss, still: still };
})();

/* TP.live.fig: the figure fields behind a hero (.tp-hero) and a pane, for any
   page. A <canvas data-fig="name"> is mounted on load: inside a hero or a pane
   it is a field over the whole box, quieted near the words; anywhere else (a
   sheet) it is the same figure drawn plainly. Each field is dim structure past
   every edge, ink for the rest, the accent for paths and warm for the one
   highlighted thing, at one calm pace. TP.live.fig.name(field) returns a scene
   for TP.live.add; TP.live.kit holds the helpers for a page's own figures. */
(function(){
"use strict";
var TP = window.TP, live = TP && TP.live;
if (!live) return;
var C = live.C, rgba = live.rgba, clamp = live.clamp, ss = live.ss, reduce = live.still;
function rnd(n){ return (Math.random() * n) | 0; }
function host(cv){ return cv.closest(".tp-pane, .tp-hero"); }
/* the words over a figure, as a box in its canvas */
function words(cv){
  var p = host(cv), t = p && p.querySelector(".tp-pane-text, .tp-hero-text");
  if (!t) return null;
  var c = cv.getBoundingClientRect(), r = t.getBoundingClientRect();
  return { l: r.left - c.left, r: r.right - c.left, t: r.top - c.top, b: r.bottom - c.top };
}
/* a weight that quiets the figure near the words (1 everywhere without them) */
function calm(b, pad){
  return function(x, y){
    if (!b) return 1;
    var dx = Math.max(b.l - x, 0, x - b.r), dy = Math.max(b.t - y, 0, y - b.b);
    return .1 + .9 * ss(0, pad, Math.hypot(dx, dy));
  };
}
/* the room the words leave, as [cx, cy, w, h], for a figure of aspect a */
function room(cv, w, h, a){
  var b = words(cv), gx = Math.max(24, w * .05), gy = Math.max(24, h * .07), best = null, sc = -1;
  if (!b) return [w / 2, h / 2, w * .9, h * .9];
  [[b.r + gx, gy, w - gx - 40, h - gy], [gx, gy, b.l - gx, h - gy], [gx, gy, w - gx, b.t - gy], [gx, b.b + gy, w - gx, h - gy]].forEach(function(r, i){
    var rw = r[2] - r[0], rh = r[3] - r[1], f = Math.min(rw, rh * a) * (i > 1 && w >= 896 ? .75 : 1);
    if (rw > 0 && rh > 0 && f > sc) { sc = f; best = [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2, rw, rh]; }
  });
  return best || [w / 2, h / 2, w * .9, h * .9];
}
/* a book's cover (img.tp-pane-cover), stood in the room the words leave */
function cover(cv, w, h){
  var im = cv.parentNode.querySelector(".tp-pane-cover");
  if (!im) return null;
  var R = room(cv, w, h, 2 / 3), ch = Math.min(R[3] * .8, R[2] * .8 * 1.5, 620);
  im.style.cssText = "--x:" + R[0].toFixed(1) + "px;--y:" + R[1].toFixed(1) + "px;--h:" + ch.toFixed(1) + "px";
  return [R[0], R[1], ch, Math.min(R[2], R[3])];
}
/* an offscreen canvas the size of the scene's, for the parts that do not move */
function layer(s){
  var L = s.layer || (s.layer = document.createElement("canvas"));
  L.width = s.cv.width; L.height = s.cv.height;
  var g = L.getContext("2d");
  g.setTransform(s.d, 0, 0, s.d, 0, 0);
  return g;
}
/* a small mask, alpha 1 - W(x, y), and a pass that erases through it */
function mask(W, w, h){
  var n = 8, cw = Math.ceil(w / n), ch = Math.ceil(h / n), m = document.createElement("canvas");
  m.width = cw; m.height = ch;
  var x = m.getContext("2d"), im = x.createImageData(cw, ch);
  for (var j = 0; j < ch; j++) for (var i = 0; i < cw; i++) im.data[(j * cw + i) * 4 + 3] = 255 * (1 - W((i + .5) * n, (j + .5) * n));
  x.putImageData(im, 0, 0);
  return m;
}
function hush(g, m, w, h){
  g.globalCompositeOperation = "destination-out"; g.drawImage(m, 0, 0, w, h); g.globalCompositeOperation = "source-over";
}
/* a lit check: a warm halo, ring and core */
function lit(g, x, y, r, a){
  g.beginPath(); g.arc(x, y, r * 1.25, 0, 7);
  g.fillStyle = rgba(C.warm, .16 * a); g.fill();
  g.strokeStyle = rgba(C.warm, .6 * a); g.lineWidth = 1.25; g.stroke();
  g.beginPath(); g.arc(x, y, r * .45, 0, 7); g.fillStyle = rgba(C.warm, a); g.fill();
}
/* an error event: flipped qubits (ink), the two checks they light (warm),
   then the correction drawn edge by edge from one check to the other (accent) */
function evEnd(ev){ return 1.5 + ev.cor.length * .22 + 1.8; }
function drawEvent(g, ev, R){
  var a = ev.age, tc = 1.5 + ev.cor.length * .22, out = 1 - clamp((a - tc - .9) / .9), m = ev.m, k, s;
  var e = clamp(a / .3) * out * m;
  g.lineCap = "round";
  g.strokeStyle = rgba(C.ink, .85 * e); g.lineWidth = Math.min(2, R * .3);
  g.beginPath();
  for (k = 0; k < ev.err.length; k++) { s = ev.err[k]; g.moveTo(s[0], s[1]); g.lineTo(s[2], s[3]); }
  g.stroke();
  g.fillStyle = rgba(C.ink, e);
  for (k = 0; k < ev.err.length; k++) { s = ev.err[k]; g.beginPath(); g.arc((s[0] + s[2]) / 2, (s[1] + s[3]) / 2, R * .34, 0, 7); g.fill(); }
  var c = clamp((a - .45) / .25) * (1 - clamp((a - tc) / .35)) * m;
  if (c > 0) for (k = 0; k < 2; k++) lit(g, ev.ends[k][0], ev.ends[k][1], R, c);
  g.strokeStyle = rgba(C.acc, out * m); g.lineWidth = Math.min(2.6, R * .38);
  g.beginPath();
  for (k = 0; k < ev.cor.length; k++) {
    var q = clamp((a - 1.5 - k * .22) / .22);
    if (q <= 0) break;
    s = ev.cor[k]; g.moveTo(s[0], s[1]); g.lineTo(s[0] + (s[2] - s[0]) * q, s[1] + (s[3] - s[1]) * q);
  }
  g.stroke();
}
function segs(pts){ var o = []; for (var i = 1; i < pts.length; i++) o.push([pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]]); return o; }
/* a random walk of 1 to n steps from (i, j) inside ok(x, y), and the
   correction: a shortest path between its two ends, one leg then the other */
function walk(i, j, n, ok){
  var path = [[i, j]], seen = {}, x = i, y = j;
  seen[i + "," + j] = 1;
  for (var k = 0; k < n; k++) {
    var D = [[1, 0], [-1, 0], [0, 1], [0, -1]].sort(function(){ return Math.random() - .5; });
    for (var d = 0; d < 4; d++) {
      var nx = x + D[d][0], ny = y + D[d][1];
      if (!ok(nx, ny) || seen[nx + "," + ny]) continue;
      x = nx; y = ny; seen[x + "," + y] = 1; path.push([x, y]); break;
    }
  }
  var cor = [[i, j]], cx = i, cy = j, hx = Math.random() < .5;
  for (var leg = 0; leg < 2; leg++, hx = !hx) {
    while (hx ? cx !== x : cy !== y) { if (hx) cx += x > cx ? 1 : -1; else cy += y > cy ? 1 : -1; cor.push([cx, cy]); }
  }
  return { path: path, cor: cor, x: x, y: y };
}
/* events that age, die and are replaced at a calm rate */
function tick(s, life, gap){
  return function(dt){
    if (!s.w) return;
    s.ev.forEach(function(e){ e.age += dt; });
    s.ev = s.ev.filter(function(e){ return e.age < life(e); });
    if ((s.next -= dt) <= 0 && s.ev.length < s.max) { s.spawn(0); s.next = gap + Math.random() * 1.2; }
  };
}
/* a spot for an event: inside the box by a margin, clear of the words and of the other events */
function free(s, x, y, gap, W){
  return x > s.w * .06 && x < s.w * .94 && y > s.h * .08 && y < s.h * .92 && W(x, y) >= .9 &&
    !s.ev.some(function(e){ return Math.hypot(e.x - x, e.y - y) < gap; });
}

/* ---------- a toric code lattice, errors found and corrected; lights near the pointer ---------- */
function lattice(pane){
  var H = { still: 0, dpr: pane ? 1 : 1.5, ev: [], next: .4, px: -1e4, py: -1e4, tx: -1e4, ty: -1e4, hover: true };
  H.pt = function(i, j){ return [H.ox + i * H.S, H.oy + j * H.S]; };
  H.setup = function(w, h){
    var S = H.S = w < 640 ? 40 : 52, i, j, W = calm(pane && words(H.cv), 2.2 * S);
    H.cols = Math.ceil(w / S) + 1; H.rows = Math.ceil(h / S) + 1;
    H.ox = (w - (H.cols - 1) * S) / 2; H.oy = (h - (H.rows - 1) * S) / 2;
    H.wt = new Float32Array(H.cols * H.rows);
    for (j = 0; j < H.rows; j++) for (i = 0; i < H.cols; i++) H.wt[j * H.cols + i] = W(H.ox + i * S, H.oy + j * S) * ss(0, h * .12, H.oy + j * S);
    var g = layer(H);
    g.lineWidth = 1;
    for (j = 0; j < H.rows; j++) for (i = 0; i < H.cols; i++) {
      var a = H.wt[j * H.cols + i], p = H.pt(i, j);
      if (i + 1 < H.cols) { g.strokeStyle = rgba(C.dim, .3 * (a + H.wt[j * H.cols + i + 1]) / 2); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0] + S, p[1]); g.stroke(); }
      if (j + 1 < H.rows) { g.strokeStyle = rgba(C.dim, .3 * (a + H.wt[(j + 1) * H.cols + i]) / 2); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0], p[1] + S); g.stroke(); }
      g.fillStyle = rgba(C.ink, .55 * a); g.beginPath(); g.arc(p[0], p[1], 1.7, 0, 7); g.fill();
    }
    H.max = w < 992 ? 3 : 6;
    H.ev = [];
    [.9, 1.75, 2.3, 3.0, .2, 3.6].slice(0, H.max).forEach(function(age){ H.spawn(age); });
  };
  H.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(H.cols - 2), j = 1 + rnd(H.rows - 2), wgt = H.wt[j * H.cols + i];
      if (wgt < .5) continue;
      if (H.ev.some(function(e){ return Math.abs(e.i - i) + Math.abs(e.j - j) < 5; })) continue;
      var w = walk(i, j, 1 + rnd(3), function(x, y){ return x >= 1 && y >= 1 && x <= H.cols - 2 && y <= H.rows - 2; });
      if (w.path.length < 2) continue;
      if (w.path.concat(w.cor).some(function(q){ return H.wt[q[1] * H.cols + q[0]] < .4; })) continue;
      H.ev.push({ i: i, j: j, age: age, m: .45 + .55 * wgt,
        err: segs(w.path.map(function(q){ return H.pt(q[0], q[1]); })),
        cor: segs(w.cor.map(function(q){ return H.pt(q[0], q[1]); })),
        ends: [H.pt(i, j), H.pt(w.x, w.y)] });
      return;
    }
  };
  H.step = function(dt){
    H.ev.forEach(function(e){ e.age += dt; });
    H.ev = H.ev.filter(function(e){ return e.age < evEnd(e); });
    if ((H.next -= dt) <= 0 && H.ev.length < H.max) { H.spawn(0); H.next = .6 + Math.random() * .9; }
    if (H.tx > -1e3) { var f = Math.min(1, dt * 7); H.px += (H.tx - H.px) * f; H.py += (H.ty - H.py) * f; }
  };
  H.draw = function(g, w, h){
    g.drawImage(H.layer, 0, 0, w, h);
    if (H.tx > -1e3 && !reduce.matches) {
      var S = H.S, R = 180, i0 = Math.max(0, Math.floor((H.px - H.ox - R) / S)), i1 = Math.min(H.cols - 1, Math.ceil((H.px - H.ox + R) / S));
      var j0 = Math.max(0, Math.floor((H.py - H.oy - R) / S)), j1 = Math.min(H.rows - 1, Math.ceil((H.py - H.oy + R) / S));
      g.lineWidth = 1;
      for (var j = j0; j <= j1; j++) for (var i = i0; i <= i1; i++) {
        var p = H.pt(i, j), f = 1 - Math.hypot(p[0] - H.px, p[1] - H.py) / R;
        if (f <= 0) continue;
        f *= f * (.35 + .65 * H.wt[j * H.cols + i]);
        g.strokeStyle = rgba(C.acc, .55 * f);
        g.beginPath();
        if (i < i1) { g.moveTo(p[0], p[1]); g.lineTo(p[0] + S, p[1]); }
        if (j < j1) { g.moveTo(p[0], p[1]); g.lineTo(p[0], p[1] + S); }
        g.stroke();
        g.fillStyle = rgba(C.acc, f); g.beginPath(); g.arc(p[0], p[1], 1.7 + 1.6 * f, 0, 7); g.fill();
      }
    }
    for (var k = 0; k < H.ev.length; k++) drawEvent(g, H.ev[k], 8);
  };
  return H;
}

/* ---------- requests from three tenants stream through a grid ---------- */
function tokens(pane){
  var T = { still: 0, dpr: pane ? 1 : 2, lanes: [] };
  function gen(L){
    if (L.left > 0) { L.left--; return L.who; }
    if (L.gap > 0) { L.gap--; return 0; }
    L.who = 1 + rnd(3); L.left = 1 + rnd(7); L.gap = 2 + rnd(9);
    return L.who;
  }
  T.setup = function(w, h){
    var p = T.p = pane ? Math.max(14, Math.min(26, h / 26)) : Math.max(7, Math.min(18, h / 10)), r, c;
    T.rows = pane ? Math.floor((h - p) / p) : Math.max(3, Math.min(18, Math.floor((h - 2 * p) / p)));
    T.cols = Math.max(4, Math.floor((w - (pane ? p : 2 * p)) / p));
    T.x0 = (w - T.cols * p) / 2; T.y0 = (h - T.rows * p) / 2;
    var W = calm(pane && words(T.cv), 4 * p), s = p * .72, o = (p - s) / 2;
    T.wt = new Float32Array(T.rows * T.cols);
    for (r = 0; r < T.rows; r++) for (c = 0; c < T.cols; c++) T.wt[r * T.cols + c] = W(T.x0 + (c + .5) * p, T.y0 + (r + .5) * p);
    var g = layer(T);
    g.lineWidth = 1;
    for (r = 0; r < T.rows; r++) for (c = 0; c < T.cols; c++) {
      g.strokeStyle = rgba(C.dim, .22 * T.wt[r * T.cols + c]);
      g.strokeRect(T.x0 + c * p + o, T.y0 + r * p + o, s, s);
    }
    T.lanes = [];
    for (r = 0; r < T.rows; r++) {
      var L = { cells: [], off: 0, v: 3.2 + Math.random() * 2.6, left: 0, gap: rnd(6), who: 0 };
      for (c = 0; c < T.cols + 2; c++) L.cells.unshift(gen(L));
      T.lanes.push(L);
    }
  };
  T.step = function(dt){
    T.lanes.forEach(function(L){
      L.off += L.v * dt;
      while (L.off >= 1) { L.off -= 1; L.cells.unshift(gen(L)); L.cells.pop(); }
    });
  };
  T.draw = function(g, w, h){
    var p = T.p, s = p * .72, o = (p - s) / 2, ink = [null, C.acc, C.warm, C.ink];
    g.drawImage(T.layer, 0, 0, w, h);
    for (var r = 0; r < T.rows; r++) {
      var L = T.lanes[r], y = T.y0 + r * p + o;
      for (var c = 0; c < L.cells.length; c++) {
        var who = L.cells[c];
        if (!who) continue;
        var x = T.x0 + (c - 1 + L.off) * p + o, mid = (x - T.x0) / (T.cols * p);
        var ci = Math.max(0, Math.min(T.cols - 1, Math.round(c - 1 + L.off)));
        var a = ss(-.02, .1, mid) * ss(1.02, .86, mid) * (who === 3 ? .7 : 1) * (pane ? .36 : 1) * T.wt[r * T.cols + ci];
        if (a <= 0) continue;
        g.fillStyle = rgba(ink[who], a);
        g.fillRect(x, y, s, s);
      }
    }
  };
  return T;
}

/* ---------- errors on a honeycomb, the decoder pairs them ---------- */
function semion(pane){
  var M = { still: 0, dpr: pane ? 1 : 2, ev: [], next: .3, max: pane ? 4 : 2 };
  M.setup = function(w, h){
    var s = M.s = pane ? Math.max(16, Math.min(32, h / 15)) : Math.max(9, Math.min(22, h / (h < 160 ? 5.5 : 11))), dx = s * Math.sqrt(3) / 2, i, j;
    var cols = Math.ceil(w / dx) + 2, rows = Math.ceil(h / (1.5 * s)) + 2;
    var ox = (w - (cols - 1) * dx) / 2, oy = (h - (rows - 1) * 1.5 * s) / 2 - .25 * s;
    M.p = []; M.nb = [];
    for (j = 0; j < rows; j++) for (i = 0; i < cols; i++) {
      M.p.push([ox + i * dx, oy + j * 1.5 * s + ((i + j) & 1 ? 0 : .5 * s)]);
      var n = [];
      if (i > 0) n.push(j * cols + i - 1);
      if (i < cols - 1) n.push(j * cols + i + 1);
      if ((i + j) & 1) { if (j > 0) n.push((j - 1) * cols + i); } else if (j < rows - 1) n.push((j + 1) * cols + i);
      M.nb.push(n);
    }
    M.W = calm(pane && words(M.cv), 3 * s);
    var g = layer(M);
    g.strokeStyle = rgba(C.dim, .32); g.lineWidth = 1; g.beginPath();
    for (var k = 0; k < M.p.length; k++) for (var q = 0; q < M.nb[k].length; q++) if (M.nb[k][q] > k) {
      var a = M.p[k], b = M.p[M.nb[k][q]]; g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]);
    }
    g.stroke();
    /* closed loops, the ground state's kind of string */
    g.strokeStyle = rgba(C.ink, .3); g.lineWidth = Math.min(1.8, s * .1); g.lineJoin = "round";
    for (var t = 0; t < (pane ? 3 : 2); t++) {
      var li = 2 + rnd(cols - 6), lj = 1 + rnd(rows - 3);
      if ((li + lj) & 1) li++;
      var L = [[li, lj], [li + 1, lj], [li + 2, lj], [li + 2, lj + 1], [li + 1, lj + 1], [li, lj + 1]].map(function(z){ return M.p[z[1] * cols + z[0]]; });
      if (L.some(function(z){ return !z; })) continue;
      g.beginPath(); g.moveTo(L[0][0], L[0][1]); for (var e = 1; e < 6; e++) g.lineTo(L[e][0], L[e][1]); g.closePath(); g.stroke();
    }
    if (pane) hush(g, mask(M.W, w, h), w, h);
    M.ev = [];
    M.spawn(2.05); M.spawn(.5);
    if (pane) { M.spawn(3.1); M.spawn(1.2); }
  };
  M.spawn = function(age){
    var w = M.w, h = M.h;
    for (var tries = 0; tries < 40; tries++) {
      var a = rnd(M.p.length), pa = M.p[a];
      if (pa[0] < w * .12 || pa[0] > w * .88 || pa[1] < h * .18 || pa[1] > h * .82) continue;
      if (M.ev.some(function(e){ return Math.hypot(e.c[0] - pa[0], e.c[1] - pa[1]) < M.s * 5; })) continue;
      var path = [a], seen = {}, n = 2 + rnd(3), v = a;
      seen[a] = 1;
      for (var k = 0; k < n; k++) {
        var opts = M.nb[v].filter(function(u){ var q = M.p[u]; return !seen[u] && q[0] > 8 && q[0] < w - 8 && q[1] > 8 && q[1] < h - 8; });
        if (!opts.length) break;
        v = opts[rnd(opts.length)]; seen[v] = 1; path.push(v);
      }
      if (path.length < 3 || path.some(function(z){ return M.W(M.p[z][0], M.p[z][1]) < .9; })) continue;
      var prev = {}, queue = [a], b = v;
      prev[a] = -1;
      while (queue.length && !(b in prev)) {
        var u = queue.shift(), ns = M.nb[u].slice().sort(function(){ return Math.random() - .5; });
        for (var q = 0; q < ns.length; q++) if (!(ns[q] in prev)) { prev[ns[q]] = u; queue.push(ns[q]); }
      }
      var cor = [];
      for (var x = b; x !== -1; x = prev[x]) cor.unshift(M.p[x]);
      M.ev.push({ c: pa, age: age, m: 1, err: segs(path.map(function(z){ return M.p[z]; })), cor: segs(cor), ends: [pa, M.p[b]] });
      return;
    }
  };
  M.step = function(dt){
    M.ev.forEach(function(e){ e.age += dt; });
    M.ev = M.ev.filter(function(e){ return e.age < evEnd(e); });
    if ((M.next -= dt) <= 0 && M.ev.length < M.max) { M.spawn(0); M.next = (pane ? .7 : 1.2) + Math.random() * 1.2; }
  };
  M.draw = function(g, w, h){
    g.drawImage(M.layer, 0, 0, w, h);
    for (var k = 0; k < M.ev.length; k++) drawEvent(g, M.ev[k], M.s * .4);
  };
  return M;
}

/* ---------- a graph of thoughts; a thought branches and merges down it ---------- */
function graph(pane){
  var G = { still: 2.4, dpr: pane ? 1 : 2, ev: [], next: .4, max: pane ? 4 : 2 };
  function near(x, list){ return list.slice().sort(function(a, b){ return Math.abs(G.n[a].x - x) - Math.abs(G.n[b].x - x); }); }
  G.setup = function(w, h){
    var z = Math.min(h, w * 1.4), s = G.s = pane ? Math.max(40, Math.min(64, z / 12)) : Math.max(26, Math.min(44, z / 8)), i, j;
    var rows = Math.ceil(h / s) + 2, cols = Math.ceil(w / s) + 2, ox = (w - (cols - 1) * s) / 2, oy = (h - (rows - 1) * s) / 2;
    G.W = calm(pane && words(G.cv), 2.5 * s);
    G.n = []; G.row = [];
    for (j = 0; j < rows; j++) {
      var R = [];
      for (i = 0; i < cols; i++) if (Math.random() < .7) {
        R.push(G.n.length);
        G.n.push({ x: ox + (i + (j & 1 ? .25 : -.25) + (Math.random() - .5) * .5) * s, y: oy + (j + (Math.random() - .5) * .35) * s, out: [] });
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
    var g = layer(G), r = pane ? 3 : 2.4;
    g.strokeStyle = rgba(C.dim, .3); g.lineWidth = 1;
    g.beginPath();
    G.n.forEach(function(a){ a.out.forEach(function(v){ g.moveTo(a.x, a.y); g.lineTo(G.n[v].x, G.n[v].y); }); });
    g.stroke();
    G.n.forEach(function(a){
      g.beginPath(); g.arc(a.x, a.y, r, 0, 7);
      g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
      g.strokeStyle = rgba(C.ink, .5); g.stroke();
    });
    if (pane) hush(g, mask(G.W, w, h), w, h);
    G.ev = [];
    G.spawn(2.6); G.spawn(.6);
    if (pane) { G.spawn(3.6); G.spawn(1.5); }
  };
  G.spawn = function(age){
    var w = G.w, h = G.h;
    for (var tries = 0; tries < 40; tries++) {
      var a = rnd(G.n.length), A = G.n[a];
      if (A.x < w * .06 || A.x > w * .94 || A.y < h * .06 || A.y > h * .6) continue;
      if (G.W(A.x, A.y) < .9 || G.ev.some(function(e){ return Math.hypot(e.x - A.x, e.y - A.y) < G.s * 4; })) continue;
      var D = 3 + rnd(3), front = [a], E = [], seen = {}, ok = true;
      seen[a] = 1;
      for (var d = 0; d < D && ok && front.length; d++) {
        var nf = [];
        front.forEach(function(u){
          var o = G.n[u].out.slice().sort(function(){ return Math.random() - .5; }), take = o.length > 1 && front.length < 3 && Math.random() < .5 ? 2 : 1;
          for (var q = 0; q < Math.min(take, o.length); q++) { E.push([u, o[q], d]); if (!seen[o[q]]) { seen[o[q]] = 1; nf.push(o[q]); } }
        });
        ok = nf.every(function(v){ return G.W(G.n[v].x, G.n[v].y) > .8 && G.n[v].y < h - 8; });
        front = nf;
      }
      if (!ok || !front.length) continue;
      G.ev.push({ x: A.x, y: A.y, a: a, age: age, E: E, end: front, D: D });
      return;
    }
  };
  function tEnd(e){ return 1 + e.D * .45 + 2.5; }
  G.step = function(dt){
    G.ev.forEach(function(e){ e.age += dt; });
    G.ev = G.ev.filter(function(e){ return e.age < tEnd(e); });
    if ((G.next -= dt) <= 0 && G.ev.length < G.max) { G.spawn(0); G.next = (pane ? .7 : 1.2) + Math.random() * 1.2; }
  };
  /* a thought: the subproblem it expands (warm), its branches (accent), where they land (ink) */
  G.draw = function(g, w, h){
    g.drawImage(G.layer, 0, 0, w, h);
    var R = 9, k;
    g.lineCap = "round";
    G.ev.forEach(function(e){
      var a = e.age, tc = 1 + e.D * .45, out = 1 - clamp((a - tc - 1.6) / .9), c = clamp((a - .2) / .3) * (1 - clamp((a - tc) / .5));
      if (c > 0) lit(g, e.x, e.y, R, c);
      g.strokeStyle = rgba(C.acc, out); g.lineWidth = 2.2;
      g.beginPath();
      for (k = 0; k < e.E.length; k++) {
        var q = clamp((a - 1 - e.E[k][2] * .45) / .45);
        if (q <= 0) continue;
        var u = G.n[e.E[k][0]], v = G.n[e.E[k][1]];
        g.moveTo(u.x, u.y); g.lineTo(u.x + (v.x - u.x) * q, u.y + (v.y - u.y) * q);
      }
      g.stroke();
      var f = clamp((a - tc) / .3) * out;
      if (f > 0) { g.fillStyle = rgba(C.ink, f); e.end.forEach(function(v){ g.beginPath(); g.arc(G.n[v].x, G.n[v].y, R * .38, 0, 7); g.fill(); }); }
    });
  };
  return G;
}

/* ---------- one Lissajous knot diagram across the whole box; its crossings drift ---------- */
function gcd(a, b){ return b ? gcd(b, a % b) : a; }
function knot(pane){
  var K = { still: 3, dpr: pane ? 1 : 2 }, NB = 24;
  K.setup = function(w, h){
    var z = Math.min(h, w * 1.4), s = pane ? Math.max(38, Math.min(54, z / 15)) : Math.max(28, Math.min(40, z / 9)), pad = s;
    K.ax = w / 2 + pad; K.ay = h / 2 + pad;
    var fx = Math.max(2, Math.round(K.ay / s)), fy = Math.max(3, Math.round(K.ax / s)), fz = fx + fy;
    while (gcd(fx, fy) > 1) fy++;
    while (gcd(fz, fx) > 1 || gcd(fz, fy) > 1) fz++;
    K.f = [fx, fy, fz];
    K.n = Math.min(3600, Math.round(2 * Math.PI * Math.hypot(K.ax * fx, K.ay * fy) / Math.SQRT2 / 12));
    K.W = calm(pane && words(K.cv), 2.2 * s);
    K.mask = pane ? mask(K.W, w, h) : null;
  };
  K.draw = function(g, w, h, t){
    var n = K.n, f = K.f, p = .3 + t * .012, q = .7 + t * .035, cx = w / 2, cy = h / 2, P = [], i, b, k;
    for (i = 0; i <= n; i++) {
      var u = 2 * Math.PI * i / n;
      P.push([cx + K.ax * Math.cos(f[0] * u + p), cy + K.ay * Math.cos(f[1] * u), Math.cos(f[2] * u + q)]);
    }
    var run = [(t * .0035) % 1, ((t * .0035) + .5) % 1], len = 360 / (2 * Math.PI * Math.hypot(K.ax * f[0], K.ay * f[1]) / Math.SQRT2);
    function on(i){ for (var r = 0; r < 2; r++) { var d = (i / n - run[r] + 1) % 1; if (d < len) return true; } return false; }
    var B = [];
    for (b = 0; b < NB; b++) B.push([]);
    for (i = 0; i < n; i++) {
      var a = P[i], c = P[i + 1];
      if (Math.max(a[0], c[0]) < -8 || Math.min(a[0], c[0]) > w + 8 || Math.max(a[1], c[1]) < -8 || Math.min(a[1], c[1]) > h + 8) continue;
      B[Math.min(NB - 1, Math.floor(((a[2] + c[2]) / 2 + 1) / 2 * NB))].push(i);
    }
    for (b = 0; b < NB; b++) {
      var S = B[b], dep = b / (NB - 1), A = [];
      if (!S.length) continue;
      g.globalCompositeOperation = "destination-out"; g.lineCap = "butt"; g.lineWidth = 8; g.beginPath();
      for (k = 0; k < S.length; k++) { g.moveTo(P[S[k]][0], P[S[k]][1]); g.lineTo(P[S[k] + 1][0], P[S[k] + 1][1]); }
      g.stroke();
      g.globalCompositeOperation = "source-over"; g.lineCap = "round"; g.lineWidth = 1.25;
      g.strokeStyle = rgba(C.dim, .28 + .4 * dep); g.beginPath();
      for (k = 0; k < S.length; k++) {
        if (on(S[k])) { A.push(S[k]); continue; }
        g.moveTo(P[S[k]][0], P[S[k]][1]); g.lineTo(P[S[k] + 1][0], P[S[k] + 1][1]);
      }
      g.stroke();
      if (A.length) {
        g.strokeStyle = rgba(C.acc, .55 + .45 * dep); g.lineWidth = 2.2; g.beginPath();
        for (k = 0; k < A.length; k++) { g.moveTo(P[A[k]][0], P[A[k]][1]); g.lineTo(P[A[k] + 1][0], P[A[k] + 1][1]); }
        g.stroke();
      }
    }
    run.forEach(function(r){
      var m = P[Math.floor((r + len) % 1 * n)];
      g.beginPath(); g.arc(m[0], m[1], 9, 0, 7); g.fillStyle = rgba(C.warm, .16); g.fill();
      g.beginPath(); g.arc(m[0], m[1], 4, 0, 7); g.fillStyle = C.warm; g.fill();
    });
    if (K.mask) hush(g, K.mask, w, h);
  };
  return K;
}

/* ---------- a field of Bloch spheres, their states precessing ---------- */
function bloch(pane){
  var B = { still: 1.1, dpr: pane ? 1 : 1.5, ev: [], next: .5, max: 3 }, tl = .36;
  B.setup = function(w, h){
    B.at = cover(B.cv, w, h);
    var s = B.s = Math.max(52, Math.min(84, Math.min(h, w * 1.4) / 9)), R = B.R = s * .32, i, j;
    B.cols = Math.ceil(w / s) + 1; B.rows = Math.ceil(h / s) + 1;
    B.ox = (w - (B.cols - 1) * s) / 2; B.oy = (h - (B.rows - 1) * s) / 2;
    B.W = calm(pane && words(B.cv), 2 * s);
    B.mask = mask(B.W, w, h);
    var g = layer(B);
    g.lineWidth = 1;
    g.strokeStyle = rgba(C.dim, .32); g.beginPath();
    for (j = 0; j < B.rows; j++) for (i = 0; i < B.cols; i++) { var x = B.ox + i * s, y = B.oy + j * s; g.moveTo(x + R, y); g.arc(x, y, R, 0, 7); }
    g.stroke();
    g.strokeStyle = rgba(C.dim, .2); g.beginPath();
    for (j = 0; j < B.rows; j++) for (i = 0; i < B.cols; i++) { g.moveTo(B.ox + i * s + R, B.oy + j * s); g.ellipse(B.ox + i * s, B.oy + j * s, R, R * Math.sin(tl), 0, 0, Math.PI); }
    g.stroke();
    B.ev = []; B.spawn(2.2); B.spawn(.4); B.spawn(1.3);
  };
  function th(j){ return .7 + .5 * Math.sin(j * 1.3); }
  function tip(i, j, t, R){
    var x = B.ox + i * B.s, y = B.oy + j * B.s, a = th(j), ph = t * .3 - i * .42 - j * .2, lr = R * Math.sin(a), ly = y - R * Math.cos(a) * Math.cos(tl);
    return [x, y, x + lr * Math.cos(ph), ly + lr * Math.sin(ph) * Math.sin(tl), lr, ly];
  }
  B.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(B.cols - 2), j = 1 + rnd(B.rows - 2), x = B.ox + i * B.s, y = B.oy + j * B.s;
      if (B.W(x, y) < .9 || B.ev.some(function(e){ return Math.abs(e.i - i) + Math.abs(e.j - j) < 4; })) continue;
      if (B.at && Math.abs(x - B.at[0]) < B.at[2] / 3 + B.s && Math.abs(y - B.at[1]) < B.at[2] / 2 + B.s) continue;
      B.ev.push({ i: i, j: j, age: age });
      return;
    }
  };
  B.step = function(dt){
    B.ev.forEach(function(e){ e.age += dt; });
    B.ev = B.ev.filter(function(e){ return e.age < 4.6; });
    if ((B.next -= dt) <= 0 && B.ev.length < B.max) { B.spawn(0); B.next = 1 + Math.random() * 1.4; }
  };
  B.draw = function(g, w, h, t){
    g.drawImage(B.layer, 0, 0, w, h);
    var i, j, p;
    g.strokeStyle = rgba(C.ink, .55); g.lineWidth = 1.2; g.lineCap = "round";
    g.beginPath();
    for (j = 0; j < B.rows; j++) for (i = 0; i < B.cols; i++) { p = tip(i, j, t, B.R); g.moveTo(p[0], p[1]); g.lineTo(p[2], p[3]); }
    g.stroke();
    if (pane) hush(g, B.mask, w, h);
    B.ev.forEach(function(e){
      var f = clamp(e.age / .5) * (1 - clamp((e.age - 3.6) / 1)), q = tip(e.i, e.j, t, B.R), r = 3.2;
      g.strokeStyle = rgba(C.acc, .8 * f); g.lineWidth = 1.6;
      g.beginPath(); g.ellipse(q[0], q[5], q[4], q[4] * Math.sin(tl), 0, 0, 7); g.stroke();
      g.strokeStyle = rgba(C.ink, f); g.lineWidth = 1.6; g.beginPath(); g.moveTo(q[0], q[1]); g.lineTo(q[2], q[3]); g.stroke();
      g.beginPath(); g.arc(q[2], q[3], r * 2.2, 0, 7); g.fillStyle = rgba(C.warm, .2 * f); g.fill();
      g.beginPath(); g.arc(q[2], q[3], r, 0, 7); g.fillStyle = rgba(C.warm, f); g.fill();
    });
  };
  return B;
}

/* ---------- a field of circles; three at a time find their common region ---------- */
function polar(pane){
  var Y = { still: 2, dpr: pane ? 1 : 1.5, ev: [], next: .6, max: 3 };
  Y.setup = function(w, h){
    Y.at = cover(Y.cv, w, h);
    var d = Y.sp = Math.max(80, Math.min(128, Math.min(h, w * 1.4) / 5.6)), dy = d * Math.sqrt(3) / 2, i, j;
    Y.r = d * .64; Y.cols = Math.ceil(w / d) + 3; Y.rows = Math.ceil(h / dy) + 3;
    Y.ox = (w - (Y.cols - 1) * d) / 2; Y.oy = (h - (Y.rows - 1) * dy) / 2; Y.dy = dy;
    Y.W = calm(pane && words(Y.cv), 1.2 * d);
    var g = layer(Y);
    g.strokeStyle = rgba(C.dim, .26); g.lineWidth = 1; g.beginPath();
    for (j = 0; j < Y.rows; j++) for (i = 0; i < Y.cols; i++) { var p = Y.c(i, j); g.moveTo(p[0] + Y.r, p[1]); g.arc(p[0], p[1], Y.r, 0, 7); }
    g.stroke();
    hush(g, mask(Y.W, w, h), w, h);
    Y.ev = []; Y.spawn(2); Y.spawn(.6); Y.spawn(3.4);
  };
  Y.c = function(i, j){ return [Y.ox + (i + (j & 1 ? .5 : 0)) * Y.sp, Y.oy + j * Y.dy]; };
  Y.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(Y.cols - 3), j = 1 + rnd(Y.rows - 3), k = j & 1;
      var P = [Y.c(i, j), Y.c(i + 1, j), Y.c(i + k, j + 1)], cx = (P[0][0] + P[1][0] + P[2][0]) / 3, cy = (P[0][1] + P[1][1] + P[2][1]) / 3;
      if (cx < Y.r || cx > Y.w - Y.r || cy < Y.r || cy > Y.h - Y.r) continue;
      if (P.some(function(p){ return Y.W(p[0], p[1]) < .8; }) || Y.W(cx, cy) < .95) continue;
      if (Y.at && Math.abs(cx - Y.at[0]) < Y.at[2] / 3 + Y.r && Math.abs(cy - Y.at[1]) < Y.at[2] / 2 + Y.r) continue;
      if (Y.ev.some(function(e){ return Math.hypot(e.x - cx, e.y - cy) < Y.sp * 2.5; })) continue;
      Y.ev.push({ P: P, x: cx, y: cy, age: age });
      return;
    }
  };
  Y.step = function(dt){
    Y.ev.forEach(function(e){ e.age += dt; });
    Y.ev = Y.ev.filter(function(e){ return e.age < 5.4; });
    if ((Y.next -= dt) <= 0 && Y.ev.length < Y.max) { Y.spawn(0); Y.next = 1.2 + Math.random() * 1.4; }
  };
  Y.draw = function(g, w, h){
    g.drawImage(Y.layer, 0, 0, w, h);
    Y.ev.forEach(function(e){
      var f = ss(0, 1, e.age) * (1 - ss(4.2, 5.4, e.age)), k;
      g.save();
      for (k = 0; k < 2; k++) { g.beginPath(); g.arc(e.P[k][0], e.P[k][1], Y.r, 0, 7); g.clip(); }
      g.beginPath(); g.arc(e.P[2][0], e.P[2][1], Y.r, 0, 7); g.fillStyle = rgba(C.acc, .2 * f); g.fill();
      g.restore();
      g.strokeStyle = rgba(C.ink, .6 * f); g.lineWidth = 1.25;
      for (k = 0; k < 3; k++) { g.beginPath(); g.arc(e.P[k][0], e.P[k][1], Y.r, 0, 7); g.stroke(); }
      g.beginPath(); g.arc(e.x, e.y, 3.6, 0, 7); g.fillStyle = rgba(C.warm, f); g.fill();
    });
  };
  return Y;
}

/* ---------- a field of engraved spheres under a moving light ----------
   On the night ground the strokes are the light; on paper they are the shade. */
function plate(pane){
  var E = { still: 2.2, dpr: pane ? 1 : 1.5 };
  E.setup = function(w, h){
    E.at = cover(E.cv, w, h);
    E.R = Math.max(40, Math.min(84, Math.min(h, w * 1.4) / 8)); E.sp = E.R * 2.6; E.st = Math.max(5, Math.min(7, E.R / 10));
    E.mask = mask(calm(pane && words(E.cv), 2 * E.R), w, h);
  };
  E.draw = function(g, w, h, t){
    var R = E.R, sp = E.sp, st = E.st, seg = 12, la = t * .3, b, k, ink = document.documentElement.dataset.theme !== "light";
    var L = [Math.cos(la) * .75, -.5, Math.sin(la) * .5 + .55], ln = Math.hypot(L[0], L[1], L[2]);
    var P = [[], [], [], [], [], [], [], []];
    for (var y = st / 2; y < h; y += st) {
      var j = Math.round(y / sp - .5), cy = (j + .5) * sp;
      for (var x0 = 0; x0 < w; x0 += seg) {
        var xm = x0 + seg / 2, i = Math.round((xm - (j & 1 ? sp / 2 : 0)) / sp - .5), cx = (i + .5) * sp + (j & 1 ? sp / 2 : 0);
        var dx = (xm - cx) / R, dy = (y - cy) / R, q = dx * dx + dy * dy, a;
        if (q < 1) { b = Math.max(0, (dx * L[0] + dy * L[1] + Math.sqrt(1 - q) * L[2]) / ln); a = .05 + .5 * (ink ? b * b : (1 - b) * (1 - b)); }
        else a = .06;
        P[Math.min(7, Math.floor(a * 14))].push(x0, y);
      }
    }
    g.lineWidth = st * .42; g.lineCap = "butt";
    for (b = 0; b < 8; b++) {
      if (!P[b].length) continue;
      g.strokeStyle = rgba(C.ink, (b + .5) / 14); g.beginPath();
      for (k = 0; k < P[b].length; k += 2) { g.moveTo(P[b][k], P[b][k + 1]); g.lineTo(P[b][k] + seg, P[b][k + 1]); }
      g.stroke();
    }
    if (pane) hush(g, E.mask, w, h);
  };
  return E;
}

/* ---------- rows of repetition codes; a bit flips, its two checks light ---------- */
function rep(pane){
  var Rp = { still: 1.9, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 };
  Rp.setup = function(w, h){
    var z = Math.min(h, w * 1.4), s = Rp.s = pane ? Math.max(40, Math.min(68, z / 11)) : Math.max(28, Math.min(44, z / 6)), i, j;
    Rp.dy = s * 1.3; Rp.r = s * .17;
    Rp.cols = Math.ceil(w / s) + 2; Rp.rows = Math.ceil(h / Rp.dy) + 1;
    Rp.ox = (w - (Rp.cols - 1) * s) / 2; Rp.oy = (h - (Rp.rows - 1) * Rp.dy) / 2;
    Rp.W = calm(pane && words(Rp.cv), 2 * s);
    var g = layer(Rp), r = Rp.r, q = r * .9;
    g.lineWidth = 1;
    g.strokeStyle = rgba(C.dim, .3); g.beginPath();
    for (j = 0; j < Rp.rows; j++) { var y = Rp.oy + j * Rp.dy; g.moveTo(0, y); g.lineTo(w, y); }
    g.stroke();
    for (j = 0; j < Rp.rows; j++) for (i = 0; i < Rp.cols; i++) {
      var p = Rp.at(i, j);
      g.globalCompositeOperation = "destination-out";
      g.beginPath(); g.arc(p[0], p[1], r, 0, 7); g.fill();
      g.fillRect(p[0] + s / 2 - q / 2, p[1] - q / 2, q, q);
      g.globalCompositeOperation = "source-over";
      g.strokeStyle = rgba(C.ink, .5); g.beginPath(); g.arc(p[0], p[1], r, 0, 7); g.stroke();
      g.strokeStyle = rgba(C.dim, .55); g.strokeRect(p[0] + s / 2 - q / 2, p[1] - q / 2, q, q);
    }
    if (pane) hush(g, mask(Rp.W, w, h), w, h);
    Rp.ev = []; Rp.spawn(1.9); Rp.spawn(.5);
    if (pane) { Rp.spawn(3.1); Rp.spawn(1.2); }
  };
  Rp.at = function(i, j){ return [Rp.ox + (i + (j & 1 ? .5 : 0)) * Rp.s, Rp.oy + j * Rp.dy]; };
  Rp.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(Rp.cols - 3), j = rnd(Rp.rows), p = Rp.at(i, j);
      if (p[0] < Rp.s || p[0] > Rp.w - Rp.s || p[1] < Rp.r * 3 || p[1] > Rp.h - Rp.r * 3) continue;
      if (Rp.W(p[0] - Rp.s, p[1]) < .9 || Rp.W(p[0] + Rp.s, p[1]) < .9) continue;
      if (Rp.ev.some(function(e){ return Math.abs(e.j - j) + Math.abs(e.i - i) < 4; })) continue;
      Rp.ev.push({ i: i, j: j, age: age });
      return;
    }
  };
  Rp.step = function(dt){
    Rp.ev.forEach(function(e){ e.age += dt; });
    Rp.ev = Rp.ev.filter(function(e){ return e.age < 4.2; });
    if ((Rp.next -= dt) <= 0 && Rp.ev.length < Rp.max) { Rp.spawn(0); Rp.next = (pane ? .7 : 1.2) + Math.random() * 1.2; }
  };
  Rp.draw = function(g, w, h){
    g.drawImage(Rp.layer, 0, 0, w, h);
    var s = Rp.s, r = Rp.r, q = r * .9;
    Rp.ev.forEach(function(e){
      var a = e.age, p = Rp.at(e.i, e.j);
      var f = clamp(a / .3) * (1 - clamp((a - 2.6) / .3));
      var on = clamp((a - .6) / .25) * (1 - clamp((a - 2.6) / .3));
      var fix = clamp((a - 1.9) / .4) * (1 - clamp((a - 3.6) / .6));
      if (f > 0) { g.beginPath(); g.arc(p[0], p[1], r * .62, 0, 7); g.fillStyle = rgba(C.ink, f); g.fill(); }
      if (on > 0) [-1, 1].forEach(function(k){
        var cx = p[0] + k * s / 2;
        g.beginPath(); g.arc(cx, p[1], q * 1.3, 0, 7); g.fillStyle = rgba(C.warm, .16 * on); g.fill();
        g.strokeStyle = rgba(C.warm, .6 * on); g.lineWidth = 1.25; g.stroke();
        g.fillStyle = rgba(C.warm, on); g.fillRect(cx - q / 2, p[1] - q / 2, q, q);
      });
      if (fix > 0) { g.beginPath(); g.arc(p[0], p[1], r + 4, 0, 7); g.strokeStyle = rgba(C.acc, fix); g.lineWidth = 2.2; g.stroke(); }
    });
  };
  return Rp;
}

/* ---------- a toric code drawn past the edges, errors found and corrected ---------- */
function toric(pane){
  var Q = { still: 0, dpr: pane ? 1 : 2, ev: [], next: .4, max: pane ? 4 : 2 };
  function P(q){ return [Q.ox + q[0] * Q.S, Q.oy + q[1] * Q.S]; }
  Q.setup = function(w, h){
    var S = Q.S = pane ? Math.max(48, Math.min(80, Math.min(h, w * 1.4) / 9)) : Math.max(28, Math.min(56, h / 7)), i, j;
    Q.cols = Math.ceil(w / S) + 1; Q.rows = Math.ceil(h / S) + 1;
    Q.ox = (w - (Q.cols - 1) * S) / 2; Q.oy = (h - (Q.rows - 1) * S) / 2;
    var W = calm(pane && words(Q.cv), 1.5 * S);
    Q.wt = new Float32Array(Q.cols * Q.rows);
    for (j = 0; j < Q.rows; j++) for (i = 0; i < Q.cols; i++) Q.wt[j * Q.cols + i] = W(Q.ox + i * S, Q.oy + j * S);
    var g = layer(Q), a, p;
    g.lineWidth = 1;
    for (j = 0; j < Q.rows; j++) for (i = 0; i < Q.cols; i++) {
      a = Q.wt[j * Q.cols + i]; p = P([i, j]);
      if (i + 1 < Q.cols) {
        var ah = (a + Q.wt[j * Q.cols + i + 1]) / 2;
        g.strokeStyle = rgba(C.dim, .3 * ah); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0] + S, p[1]); g.stroke();
        g.fillStyle = rgba(C.ink, .4 * ah); g.beginPath(); g.arc(p[0] + S / 2, p[1], 2.4, 0, 7); g.fill();
      }
      if (j + 1 < Q.rows) {
        var av = (a + Q.wt[(j + 1) * Q.cols + i]) / 2;
        g.strokeStyle = rgba(C.dim, .3 * av); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0], p[1] + S); g.stroke();
        g.fillStyle = rgba(C.ink, .4 * av); g.beginPath(); g.arc(p[0], p[1] + S / 2, 2.4, 0, 7); g.fill();
      }
      g.fillStyle = rgba(C.ink, .5 * a); g.beginPath(); g.arc(p[0], p[1], 3.2, 0, 7); g.fill();
    }
    Q.ev = []; Q.spawn(1.9); Q.spawn(.3);
    if (pane) { Q.spawn(3.2); Q.spawn(1.1); }
  };
  Q.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var i = 1 + rnd(Q.cols - 2), j = 1 + rnd(Q.rows - 2);
      if (Q.wt[j * Q.cols + i] < .7) continue;
      if (Q.ev.some(function(e){ return Math.abs(e.i - i) + Math.abs(e.j - j) < 4; })) continue;
      var w = walk(i, j, 1 + rnd(2), function(x, y){ return x >= 1 && y >= 1 && x < Q.cols - 1 && y < Q.rows - 1; });
      if (w.path.length < 2) continue;
      if (w.path.concat(w.cor).some(function(q){ return Q.wt[q[1] * Q.cols + q[0]] < .6; })) continue;
      Q.ev.push({ i: i, j: j, age: age, m: 1, err: segs(w.path.map(P)), cor: segs(w.cor.map(P)), ends: [P([i, j]), P([w.x, w.y])] });
      return;
    }
  };
  Q.step = function(dt){
    Q.ev.forEach(function(e){ e.age += dt; });
    Q.ev = Q.ev.filter(function(e){ return e.age < evEnd(e); });
    if ((Q.next -= dt) <= 0 && Q.ev.length < Q.max) { Q.spawn(0); Q.next = (pane ? .6 : 1.1) + Math.random() * 1.1; }
  };
  Q.draw = function(g, w, h){
    g.drawImage(Q.layer, 0, 0, w, h);
    for (var k = 0; k < Q.ev.length; k++) drawEvent(g, Q.ev[k], Q.S * .12);
  };
  return Q;
}

/* ---------- quantum circuits: wires, gates and CNOTs; a run lights along a
   wire, gate by gate, to the measurement at its end ---------- */
function circuit(pane){
  var Q = { still: 2.2, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 };
  Q.x = function(i){ return Q.ox + i * Q.s; };
  Q.y = function(j){ return Q.oy + j * Q.s; };
  Q.setup = function(w, h){
    var s = Q.s = pane ? Math.max(44, Math.min(72, Math.min(h, w * 1.4) / 10)) : Math.max(30, Math.min(48, h / 6)), i, j, k;
    Q.cols = Math.ceil(w / s) + 2; Q.rows = Math.ceil(h / s) + 1;
    Q.ox = (w - (Q.cols - 1) * s) / 2; Q.oy = (h - (Q.rows - 1) * s) / 2;
    Q.W = calm(pane && words(Q.cv), 2 * s);
    /* a gate per slot: 1 a one-qubit box, 2 a control, 3 its target on the wire below */
    var G = Q.gate = new Uint8Array(Q.cols * Q.rows);
    for (j = 0; j < Q.rows; j++) for (i = 0; i < Q.cols; i++) {
      k = j * Q.cols + i;
      if (G[k]) continue;
      var r = Math.random();
      if (r < .17) G[k] = 1;
      else if (r < .27 && j + 1 < Q.rows) { G[k] = 2; G[k + Q.cols] = 3; }
    }
    var g = layer(Q), b = Q.b = s * .36, t = s * .15;
    g.lineWidth = 1;
    g.strokeStyle = rgba(C.dim, .3); g.beginPath();
    for (j = 0; j < Q.rows; j++) { g.moveTo(0, Q.y(j)); g.lineTo(w, Q.y(j)); }
    g.stroke();
    for (j = 0; j < Q.rows; j++) for (i = 0; i < Q.cols; i++) {
      var x = Q.x(i), y = Q.y(j), v = G[j * Q.cols + i];
      if (v === 1) {
        g.globalCompositeOperation = "destination-out"; g.fillRect(x - b / 2, y - b / 2, b, b); g.globalCompositeOperation = "source-over";
        g.strokeStyle = rgba(C.dim, .6); g.strokeRect(x - b / 2, y - b / 2, b, b);
      } else if (v === 2) {
        g.strokeStyle = rgba(C.dim, .5); g.beginPath(); g.moveTo(x, y); g.lineTo(x, y + s - t); g.stroke();
        g.fillStyle = rgba(C.ink, .5); g.beginPath(); g.arc(x, y, 3, 0, 7); g.fill();
      } else if (v === 3) {
        g.globalCompositeOperation = "destination-out"; g.beginPath(); g.arc(x, y, t, 0, 7); g.fill(); g.globalCompositeOperation = "source-over";
        g.strokeStyle = rgba(C.dim, .6); g.beginPath(); g.arc(x, y, t, 0, 7);
        g.moveTo(x - t, y); g.lineTo(x + t, y); g.moveTo(x, y - t); g.lineTo(x, y + t); g.stroke();
      }
    }
    if (pane) hush(g, mask(Q.W, w, h), w, h);
    Q.ev = []; Q.spawn(2.4); Q.spawn(.6);
    if (pane) { Q.spawn(3.4); Q.spawn(1.4); }
  };
  Q.spawn = function(age){
    for (var tries = 0; tries < 40; tries++) {
      var j = rnd(Q.rows), n = 3 + rnd(3), i0 = 1 + rnd(Math.max(1, Q.cols - n - 2)), y = Q.y(j), ok = true;
      for (var k = 0; k <= n && ok; k++) ok = Q.W(Q.x(i0 + k), y) >= .9 && Q.x(i0 + k) > Q.s * .5 && Q.x(i0 + k) < Q.w - Q.s * .5;
      if (!ok || y < Q.s * .5 || y > Q.h - Q.s * .5) continue;
      if (Q.ev.some(function(e){ return Math.abs(e.j - j) < 2 && e.i0 < i0 + n + 2 && i0 < e.i0 + e.n + 2; })) continue;
      Q.ev.push({ j: j, i0: i0, n: n, age: age });
      return;
    }
  };
  function end(e){ return .4 + e.n * .35 + 2.6; }
  Q.step = tick(Q, end, pane ? .7 : 1.2);
  /* the input (ink), the run along the wire (accent), the measurement (warm) */
  Q.draw = function(g, w, h){
    g.drawImage(Q.layer, 0, 0, w, h);
    var b = Q.b;
    Q.ev.forEach(function(e){
      var a = e.age, tc = .4 + e.n * .35, out = 1 - clamp((a - tc - 1.6) / .9), x0 = Q.x(e.i0), y = Q.y(e.j);
      var x1 = x0 + e.n * Q.s * clamp((a - .4) / (e.n * .35));
      g.fillStyle = rgba(C.ink, clamp(a / .3) * out); g.beginPath(); g.arc(x0, y, 3.6, 0, 7); g.fill();
      if (x1 > x0) { g.strokeStyle = rgba(C.acc, out); g.lineWidth = 2.2; g.lineCap = "round"; g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y); g.stroke(); }
      var c = clamp((a - tc) / .3) * out;
      if (c > 0) {
        var x = Q.x(e.i0 + e.n);
        g.fillStyle = rgba(C.warm, .16 * c); g.fillRect(x - b * .75, y - b * .75, b * 1.5, b * 1.5);
        g.strokeStyle = rgba(C.warm, .6 * c); g.lineWidth = 1.25; g.strokeRect(x - b * .75, y - b * .75, b * 1.5, b * 1.5);
        g.fillStyle = rgba(C.warm, c); g.fillRect(x - b * .22, y - b * .22, b * .44, b * .44);
      }
    });
  };
  return Q;
}

/* ---------- the integers in rows: primes in ink, the rest dim; a twin pair lights ---------- */
function primes(pane){
  var P = { still: 1.6, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 };
  P.at = function(n){ return [P.ox + (n % P.cols) * P.s, P.oy + Math.floor(n / P.cols) * P.s]; };
  P.setup = function(w, h){
    var s = P.s = pane ? Math.max(22, Math.min(34, Math.min(h, w * 1.4) / 22)) : Math.max(14, Math.min(24, h / 12)), n, k;
    P.cols = Math.ceil(w / s) + 1; P.rows = Math.ceil(h / s) + 1;
    P.ox = (w - (P.cols - 1) * s) / 2; P.oy = (h - (P.rows - 1) * s) / 2;
    var N = P.N = P.cols * P.rows + 3, c = P.comp = new Uint8Array(N);
    c[0] = c[1] = 1;
    for (n = 2; n * n < N; n++) if (!c[n]) for (k = n * n; k < N; k += n) c[k] = 1;
    P.W = calm(pane && words(P.cv), 2.5 * s);
    var g = layer(P);
    for (n = 0; n < P.cols * P.rows; n++) {
      var p = P.at(n);
      if (c[n]) { g.fillStyle = rgba(C.dim, .4); g.beginPath(); g.arc(p[0], p[1], 1.1, 0, 7); g.fill(); }
      else { g.fillStyle = rgba(C.ink, .55); g.beginPath(); g.arc(p[0], p[1], Math.max(2, s * .09), 0, 7); g.fill(); }
    }
    if (pane) hush(g, mask(P.W, w, h), w, h);
    P.ev = []; P.spawn(2.2); P.spawn(.6);
    if (pane) { P.spawn(3.2); P.spawn(1.3); }
  };
  P.spawn = function(age){
    for (var tries = 0; tries < 80; tries++) {
      var n = 3 + rnd(P.cols * P.rows - 6);
      if (P.comp[n] || P.comp[n + 2] || n % P.cols > P.cols - 3) continue;
      var a = P.at(n), b = P.at(n + 2), x = (a[0] + b[0]) / 2;
      if (!free(P, x, a[1], P.s * 6, P.W) || P.W(a[0], a[1]) < .9 || P.W(b[0], b[1]) < .9) continue;
      P.ev.push({ n: n, a: a, b: b, x: x, y: a[1], age: age });
      return;
    }
  };
  P.step = tick(P, function(){ return 4.4; }, pane ? .8 : 1.3);
  /* the pair (warm), the arc that pairs them (accent), the even number between (ink) */
  P.draw = function(g, w, h){
    g.drawImage(P.layer, 0, 0, w, h);
    var s = P.s;
    P.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.4) / 1), c = clamp((a - .2) / .35) * out, q = clamp((a - .8) / .8);
      if (c > 0) { lit(g, e.a[0], e.a[1], s * .34, c); lit(g, e.b[0], e.b[1], s * .34, c); }
      if (q > 0) {
        g.strokeStyle = rgba(C.acc, out); g.lineWidth = 2; g.lineCap = "round"; g.beginPath();
        for (var k = 0; k <= 16 * q; k++) {
          var u = k / 16, x = e.a[0] + (e.b[0] - e.a[0]) * u, y = e.y - Math.sin(u * Math.PI) * s * .9;
          if (k) g.lineTo(x, y); else g.moveTo(x, y);
        }
        g.stroke();
      }
      var f = clamp((a - 1.6) / .3) * out;
      if (f > 0) { g.fillStyle = rgba(C.ink, f); g.beginPath(); g.arc(e.x, e.y, s * .12, 0, 7); g.fill(); }
    });
  };
  return P;
}

/* ---------- pages of dialogue: lines of words in two voices, the second set in;
   a line is read, underlined as it goes, and ends on a question ---------- */
function prose(pane){
  var R = { still: 2, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 };
  R.setup = function(w, h){
    var u = R.u = pane ? Math.max(8, Math.min(12, h / 70)) : Math.max(6, Math.min(9, h / 40)), lh = R.lh = u * 2.8, cw = u * 36, gap = u * 5, c, y;
    R.W = calm(pane && words(R.cv), 4 * u);
    R.lines = [];
    for (var x = -u * 6; x < w; x += cw + gap) {
      var left = 0, voice = rnd(2);
      for (y = (rnd(3) - 1) * lh; y < h + lh; y += lh) {
        if (left <= 0) { left = 2 + rnd(4); voice = 1 - voice; y += lh * .5; }
        left--;
        var x0 = x + (voice ? u * 3 : 0), x1 = x + cw * (left ? 1 : .35 + Math.random() * .5), ws = [], at = x0;
        while (at < x1 - u) { var l = u * (1 + rnd(6)); ws.push([at, Math.min(at + l, x1)]); at += l + u * 1.1; }
        R.lines.push({ y: y, x0: x0, x1: ws.length ? ws[ws.length - 1][1] : x0, ws: ws });
      }
    }
    var g = layer(R);
    g.strokeStyle = rgba(C.dim, .34); g.lineWidth = Math.min(3, u * .3); g.lineCap = "round"; g.beginPath();
    R.lines.forEach(function(L){ L.ws.forEach(function(s){ g.moveTo(s[0], L.y); g.lineTo(s[1], L.y); }); });
    g.stroke();
    if (pane) hush(g, mask(R.W, w, h), w, h);
    R.ev = []; R.spawn(1.8); R.spawn(.5);
    if (pane) { R.spawn(3); R.spawn(1.1); }
  };
  R.spawn = function(age){
    for (var tries = 0; tries < 60; tries++) {
      var L = R.lines[rnd(R.lines.length)];
      if (!L.ws.length || L.x1 - L.x0 < R.u * 14) continue;
      if (!free(R, (L.x0 + L.x1) / 2, L.y, R.lh * 4, R.W) || R.W(L.x0, L.y) < .9 || R.W(L.x1, L.y) < .9 || L.x0 < 8 || L.x1 > R.w - 16) continue;
      R.ev.push({ L: L, x: (L.x0 + L.x1) / 2, y: L.y, age: age });
      return;
    }
  };
  R.step = tick(R, function(){ return 4.6; }, pane ? .8 : 1.3);
  /* the words read (ink), the underline that reads them (accent), the question at the end (warm) */
  R.draw = function(g, w, h){
    g.drawImage(R.layer, 0, 0, w, h);
    var u = R.u;
    R.ev.forEach(function(e){
      var a = e.age, L = e.L, out = 1 - clamp((a - 3.6) / 1), q = clamp((a - .3) / 1.6), xe = L.x0 + (L.x1 - L.x0) * q;
      g.lineCap = "round";
      g.strokeStyle = rgba(C.ink, .9 * out); g.lineWidth = Math.min(3, u * .3); g.beginPath();
      L.ws.forEach(function(s){ if (s[0] < xe) { g.moveTo(s[0], L.y); g.lineTo(Math.min(s[1], xe), L.y); } });
      g.stroke();
      if (q > 0) { g.strokeStyle = rgba(C.acc, out); g.lineWidth = 1.6; g.beginPath(); g.moveTo(L.x0, L.y + u * .9); g.lineTo(xe, L.y + u * .9); g.stroke(); }
      var c = clamp((a - 2) / .3) * out;
      if (c > 0) lit(g, L.x1 + u * 1.8, L.y, u * .9, c);
    });
  };
  return R;
}

/* ---------- a field of crossings: at each, the lines for three code distances,
   the steeper the larger, cross at one point; one at a time lights ---------- */
function crossing(pane){
  var X = { still: 2, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 }, K = [.45, .85, 1.45];
  X.setup = function(w, h){
    var s = X.s = pane ? Math.max(70, Math.min(110, Math.min(h, w * 1.4) / 7)) : Math.max(50, Math.min(76, h / 4)), i, j;
    X.W = calm(pane && words(X.cv), 1.6 * s);
    X.m = [];
    for (j = -1; j * s * .8 < h + s; j++) for (i = -1; i * s < w + s; i++)
      X.m.push({ x: (i + (j & 1 ? .5 : 0)) * s + (Math.random() - .5) * s * .2, y: j * s * .8 + (Math.random() - .5) * s * .15 });
    var g = layer(X), L = X.L = s * .42;
    g.lineWidth = 1;
    g.strokeStyle = rgba(C.dim, .12); g.beginPath();
    for (var x = 0; x < w; x += s / 2) { g.moveTo(x, 0); g.lineTo(x, h); }
    for (var y = 0; y < h; y += s / 2) { g.moveTo(0, y); g.lineTo(w, y); }
    g.stroke();
    X.m.forEach(function(m){
      K.forEach(function(k, n){
        var c = Math.cos(Math.atan(k)) * L, d = Math.sin(Math.atan(k)) * L;
        g.strokeStyle = rgba(C.dim, .3 + n * .14); g.beginPath(); g.moveTo(m.x - c, m.y + d); g.lineTo(m.x + c, m.y - d); g.stroke();
      });
      g.fillStyle = rgba(C.ink, .45); g.beginPath(); g.arc(m.x, m.y, 1.8, 0, 7); g.fill();
    });
    if (pane) hush(g, mask(X.W, w, h), w, h);
    X.ev = []; X.spawn(2); X.spawn(.5);
    if (pane) { X.spawn(3.1); X.spawn(1.2); }
  };
  X.spawn = function(age){
    for (var tries = 0; tries < 60; tries++) {
      var m = X.m[rnd(X.m.length)];
      if (!free(X, m.x, m.y, X.s * 2.2, X.W) || X.W(m.x - X.L, m.y) < .9 || X.W(m.x + X.L, m.y) < .9) continue;
      X.ev.push({ x: m.x, y: m.y, age: age });
      return;
    }
  };
  X.step = tick(X, function(){ return 4.4; }, pane ? .8 : 1.3);
  /* the three lines drawn in (ink, then the accent on the steepest), the crossing (warm) */
  X.draw = function(g, w, h){
    g.drawImage(X.layer, 0, 0, w, h);
    var L = X.L;
    X.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.4) / 1);
      g.lineCap = "round";
      K.forEach(function(k, n){
        var q = clamp((a - n * .35) / .6), c = Math.cos(Math.atan(k)) * L * q, d = Math.sin(Math.atan(k)) * L * q;
        if (q <= 0) return;
        g.strokeStyle = n === 2 ? rgba(C.acc, out) : rgba(C.ink, (.5 + .3 * n) * out); g.lineWidth = n === 2 ? 2.2 : 1.6;
        g.beginPath(); g.moveTo(e.x - c, e.y + d); g.lineTo(e.x + c, e.y - d); g.stroke();
      });
      var c = clamp((a - 1.4) / .3) * out;
      if (c > 0) lit(g, e.x, e.y, 8, c);
    });
  };
  return X;
}

/* ---------- a rotated surface code: qubits on the corners, checks on the faces.
   An error lights the checks of the other kind around it and the correction
   rings it; with seam, two patches merge along a column of checks instead ---------- */
function surface(pane, seam){
  var F = { still: 2, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 4 : 2 };
  F.at = function(i, j){ return [F.ox + i * F.s, F.oy + j * F.s]; };
  F.setup = function(w, h){
    var s = F.s = pane ? Math.max(44, Math.min(72, Math.min(h, w * 1.4) / 10)) : Math.max(30, Math.min(46, h / 6)), i, j;
    F.cols = Math.ceil(w / s) + 1; F.rows = Math.ceil(h / s) + 1;
    F.ox = (w - (F.cols - 1) * s) / 2; F.oy = (h - (F.rows - 1) * s) / 2;
    F.W = calm(pane && words(F.cv), 2 * s);
    var g = layer(F);
    g.lineWidth = 1;
    for (j = 0; j + 1 < F.rows; j++) for (i = 0; i + 1 < F.cols; i++) {
      var p = F.at(i, j);
      if ((i + j) & 1) { g.fillStyle = rgba(C.dim, .07); g.fillRect(p[0], p[1], s, s); }
    }
    g.strokeStyle = rgba(C.dim, .3); g.beginPath();
    for (j = 0; j < F.rows; j++) { g.moveTo(0, F.oy + j * s); g.lineTo(w, F.oy + j * s); }
    for (i = 0; i < F.cols; i++) { g.moveTo(F.ox + i * s, 0); g.lineTo(F.ox + i * s, h); }
    g.stroke();
    g.fillStyle = rgba(C.ink, .5);
    for (j = 0; j < F.rows; j++) for (i = 0; i < F.cols; i++) { g.beginPath(); g.arc(F.ox + i * s, F.oy + j * s, 2.6, 0, 7); g.fill(); }
    if (pane) hush(g, mask(F.W, w, h), w, h);
    F.ev = []; F.spawn(2); F.spawn(.5);
    if (pane) { F.spawn(3.1); F.spawn(1.2); }
  };
  F.spawn = function(age){
    for (var tries = 0; tries < 60; tries++) {
      var i = 1 + rnd(F.cols - 3), j = 1 + rnd(F.rows - (seam ? 5 : 3)), p = F.at(i, j), s = F.s;
      if (seam) {
        if (!free(F, p[0] + s / 2, p[1] + 1.5 * s, s * 4, F.W) || F.W(p[0], p[1]) < .9 || F.W(p[0] + s, p[1] + 3 * s) < .9) continue;
        F.ev.push({ i: i, j: j, x: p[0] + s / 2, y: p[1] + 1.5 * s, age: age });
      } else {
        if (!free(F, p[0], p[1], s * 3.5, F.W) || F.W(p[0] - s, p[1] - s) < .9 || F.W(p[0] + s, p[1] + s) < .9) continue;
        F.ev.push({ i: i, j: j, x: p[0], y: p[1], age: age });
      }
      return;
    }
  };
  F.step = tick(F, function(){ return 4.4; }, pane ? .7 : 1.2);
  F.draw = function(g, w, h){
    g.drawImage(F.layer, 0, 0, w, h);
    var s = F.s;
    F.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.4) / 1), p = F.at(e.i, e.j), k;
      if (seam) {
        /* the seam: its checks drawn in one by one (accent), the qubits it joins (ink), the outcome (warm) */
        g.strokeStyle = rgba(C.acc, out); g.lineWidth = 2;
        for (k = 0; k < 3; k++) { var q = clamp((a - .3 - k * .4) / .4); if (q > 0) { g.globalAlpha = q; g.strokeRect(p[0] + 2, p[1] + k * s + 2, s - 4, s - 4); g.globalAlpha = 1; } }
        var f = clamp((a - 1.5) / .3) * out;
        g.fillStyle = rgba(C.ink, f);
        for (k = 0; k < 4; k++) { g.beginPath(); g.arc(p[0], p[1] + k * s, 3.6, 0, 7); g.arc(p[0] + s, p[1] + k * s, 3.6, 0, 7); g.fill(); }
        var c = clamp((a - 1.9) / .3) * out;
        if (c > 0) lit(g, e.x, e.y, s * .3, c);
        return;
      }
      /* an error (ink), the checks it lights (warm), the correction (accent) */
      var x = p[0], y = p[1], er = clamp(a / .3) * (1 - clamp((a - 2.6) / .3)), on = clamp((a - .6) / .25) * out;
      if (er > 0) { g.fillStyle = rgba(C.ink, er); g.beginPath(); g.arc(x, y, 5, 0, 7); g.fill(); }
      if (on > 0) for (k = 0; k < 4; k++) {
        var ci = e.i - 1 + (k & 1), cj = e.j - 1 + (k >> 1);
        if (!((ci + cj) & 1)) continue;
        var c0 = F.at(ci, cj), lo = on * (1 - clamp((a - 2.6) / .3));
        g.fillStyle = rgba(C.warm, .16 * lo); g.fillRect(c0[0] + 1, c0[1] + 1, s - 2, s - 2);
        g.strokeStyle = rgba(C.warm, .6 * lo); g.lineWidth = 1.25; g.strokeRect(c0[0] + 1, c0[1] + 1, s - 2, s - 2);
        g.fillStyle = rgba(C.warm, lo); g.beginPath(); g.arc(c0[0] + s / 2, c0[1] + s / 2, 3.4, 0, 7); g.fill();
      }
      var fix = clamp((a - 1.9) / .4) * out;
      if (fix > 0) { g.strokeStyle = rgba(C.acc, fix); g.lineWidth = 2.2; g.beginPath(); g.arc(x, y, 10, 0, 7); g.stroke(); }
    });
  };
  return F;
}

/* ---------- Bell pairs across a field; a state at one node is teleported:
   measured with one half of a pair, it appears at the other half ---------- */
function bell(pane){
  var T = { still: 2.6, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 3 : 2 };
  T.setup = function(w, h){
    var s = T.s = pane ? Math.max(54, Math.min(84, Math.min(h, w * 1.4) / 9)) : Math.max(36, Math.min(52, h / 5)), i, j;
    var cols = Math.ceil(w / s) + 2, rows = Math.ceil(h / s) + 2, ox = (w - (cols - 1) * s) / 2, oy = (h - (rows - 1) * s) / 2;
    T.W = calm(pane && words(T.cv), 2 * s);
    T.n = []; T.pairs = [];
    for (j = 0; j < rows; j++) for (i = 0; i < cols; i++)
      T.n.push({ x: ox + i * s + (Math.random() - .5) * s * .3, y: oy + j * s + (Math.random() - .5) * s * .3, i: i, j: j, mate: -1 });
    /* pair each node with a free neighbour to its right or below */
    T.n.forEach(function(a, k){
      if (a.mate >= 0) return;
      var opts = [];
      if (a.i + 1 < cols && T.n[k + 1].mate < 0) opts.push(k + 1);
      if (a.j + 1 < rows && T.n[k + cols].mate < 0) opts.push(k + cols);
      if (!opts.length) return;
      var b = opts[rnd(opts.length)];
      a.mate = b; T.n[b].mate = k; T.pairs.push([k, b]);
    });
    T.cols = cols;
    var g = layer(T);
    g.lineWidth = 1; g.strokeStyle = rgba(C.dim, .32); g.setLineDash([3, 4]); g.beginPath();
    T.pairs.forEach(function(p){ var a = T.n[p[0]], b = T.n[p[1]]; g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); });
    g.stroke(); g.setLineDash([]);
    T.n.forEach(function(a){
      g.beginPath(); g.arc(a.x, a.y, 3.2, 0, 7);
      g.globalCompositeOperation = "destination-out"; g.fill(); g.globalCompositeOperation = "source-over";
      g.strokeStyle = rgba(C.ink, .5); g.stroke();
    });
    if (pane) hush(g, mask(T.W, w, h), w, h);
    T.ev = []; T.spawn(2.4); T.spawn(.5);
    if (pane) T.spawn(3.6);
  };
  T.spawn = function(age){
    for (var tries = 0; tries < 60; tries++) {
      var p = T.pairs[rnd(T.pairs.length)], B = T.n[p[0]], Cn = T.n[p[1]];
      /* A: a node beside B, away from C */
      var cand = [-1, 1, -T.cols, T.cols].map(function(d){ return T.n[p[0] + d]; }).filter(function(A){ return A && A !== Cn && Math.hypot(A.x - B.x, A.y - B.y) < T.s * 1.6; });
      if (!cand.length) continue;
      var A = cand[rnd(cand.length)], x = (A.x + Cn.x) / 2, y = (A.y + Cn.y) / 2;
      if (!free(T, x, y, T.s * 4, T.W) || [A, B, Cn].some(function(q){ return T.W(q.x, q.y) < .9; })) continue;
      T.ev.push({ A: A, B: B, C: Cn, x: x, y: y, age: age });
      return;
    }
  };
  T.step = tick(T, function(){ return 4.8; }, pane ? .9 : 1.4);
  /* the state (warm) at A, A measured with B (ink), the pair B to C (accent), the state at C (warm) */
  T.draw = function(g, w, h){
    g.drawImage(T.layer, 0, 0, w, h);
    T.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.8) / 1), A = e.A, B = e.B, Cn = e.C;
      var s0 = clamp(a / .3) * (1 - clamp((a - 2.2) / .4)), m = clamp((a - .6) / .6), q = clamp((a - 1.3) / .8), s1 = clamp((a - 2.2) / .3) * out;
      if (s0 > 0) lit(g, A.x, A.y, 8, s0);
      g.lineCap = "round";
      if (m > 0) { g.strokeStyle = rgba(C.ink, .85 * out); g.lineWidth = 1.6; g.beginPath(); g.moveTo(A.x, A.y); g.lineTo(A.x + (B.x - A.x) * m, A.y + (B.y - A.y) * m); g.stroke(); }
      if (q > 0) { g.strokeStyle = rgba(C.acc, out); g.lineWidth = 2.2; g.beginPath(); g.moveTo(B.x, B.y); g.lineTo(B.x + (Cn.x - B.x) * q, B.y + (Cn.y - B.y) * q); g.stroke(); }
      if (s1 > 0) lit(g, Cn.x, Cn.y, 8, s1);
    });
  };
  return T;
}

/* ---------- lanes of time with spans on them; a span is drawn out along its
   lane and ends on a milestone ---------- */
function timeline(pane){
  var L = { still: 2.4, dpr: pane ? 1 : 2, ev: [], next: .5, max: pane ? 5 : 2 };
  L.setup = function(w, h){
    var s = L.s = pane ? Math.max(40, Math.min(64, Math.min(h, w * 1.4) / 12)) : Math.max(28, Math.min(44, h / 6)), lh = L.lh = s * .62, i, j;
    L.cols = Math.ceil(w / s) + 1; L.rows = Math.ceil(h / lh) + 1;
    L.ox = (w - (L.cols - 1) * s) / 2; L.oy = (h - (L.rows - 1) * lh) / 2;
    L.W = calm(pane && words(L.cv), 2 * s);
    var g = layer(L);
    g.lineWidth = 1;
    g.strokeStyle = rgba(C.dim, .12); g.beginPath();
    for (i = 0; i < L.cols; i++) { g.moveTo(L.ox + i * s, 0); g.lineTo(L.ox + i * s, h); }
    g.stroke();
    g.strokeStyle = rgba(C.dim, .26); g.beginPath();
    for (j = 0; j < L.rows; j++) { g.moveTo(0, L.oy + j * lh); g.lineTo(w, L.oy + j * lh); }
    g.stroke();
    g.lineCap = "round"; g.lineWidth = 3;
    for (j = 0; j < L.rows; j++) for (i = 0; i < L.cols; i += 1 + rnd(4)) {
      if (Math.random() < .45) continue;
      var n = 1 + rnd(3), x = L.ox + i * s, y = L.oy + j * lh;
      g.strokeStyle = rgba(C.dim, .5); g.beginPath(); g.moveTo(x, y); g.lineTo(x + n * s, y); g.stroke();
      g.fillStyle = rgba(C.ink, .5); g.beginPath(); g.arc(x, y, 2.6, 0, 7); g.fill();
      i += n;
    }
    if (pane) hush(g, mask(L.W, w, h), w, h);
    L.ev = []; L.spawn(2.2); L.spawn(.6);
    if (pane) { L.spawn(3.2); L.spawn(1.3); }
  };
  L.spawn = function(age){
    for (var tries = 0; tries < 60; tries++) {
      var j = rnd(L.rows), n = 2 + rnd(4), i = rnd(Math.max(1, L.cols - n)), x0 = L.ox + i * L.s, x1 = x0 + n * L.s, y = L.oy + j * L.lh;
      if (!free(L, (x0 + x1) / 2, y, L.s * 3, L.W) || L.W(x0, y) < .9 || L.W(x1, y) < .9 || x0 < 8 || x1 > L.w - 8) continue;
      L.ev.push({ x0: x0, x1: x1, x: (x0 + x1) / 2, y: y, age: age });
      return;
    }
  };
  L.step = tick(L, function(){ return 4.4; }, pane ? .7 : 1.2);
  /* where it starts (ink), the span (accent), the milestone it reaches (warm) */
  L.draw = function(g, w, h){
    g.drawImage(L.layer, 0, 0, w, h);
    L.ev.forEach(function(e){
      var a = e.age, out = 1 - clamp((a - 3.4) / 1), q = clamp((a - .3) / 1.4), x = e.x0 + (e.x1 - e.x0) * q;
      g.fillStyle = rgba(C.ink, clamp(a / .3) * out); g.beginPath(); g.arc(e.x0, e.y, 4, 0, 7); g.fill();
      if (q > 0) { g.strokeStyle = rgba(C.acc, out); g.lineWidth = 3; g.lineCap = "round"; g.beginPath(); g.moveTo(e.x0, e.y); g.lineTo(x, e.y); g.stroke(); }
      var c = clamp((a - 1.7) / .3) * out;
      if (c > 0) lit(g, e.x1, e.y, 8, c);
    });
  };
  return L;
}

var FIG = TP.live.fig = { lattice: lattice, tokens: tokens, semion: semion, graph: graph, knot: knot, bloch: bloch, polar: polar,
  plate: plate, rep: rep, toric: toric, circuit: circuit, primes: primes, prose: prose, crossing: crossing,
  surface: function(pane){ return surface(pane, false); }, seam: function(pane){ return surface(pane, true); },
  bell: bell, timeline: timeline };
TP.live.kit = { words: words, calm: calm, room: room, cover: cover, layer: layer, mask: mask, hush: hush, lit: lit,
  drawEvent: drawEvent, evEnd: evEnd, segs: segs, walk: walk };

/* mount every canvas[data-fig]; a figure that follows the pointer listens on its hero or pane */
Array.prototype.forEach.call(document.querySelectorAll("canvas[data-fig]"), function(cv){
  var make = FIG[cv.getAttribute("data-fig")], box = host(cv);
  if (!make) return;
  var s = make(!!box);
  if (!live.add(cv, s) || !s.hover || !box) return;
  box.addEventListener("pointermove", function(e){
    if (e.pointerType === "touch") return;
    var r = cv.getBoundingClientRect();
    s.tx = e.clientX - r.left; s.ty = e.clientY - r.top;
    if (s.px < -1e3) { s.px = s.tx; s.py = s.ty; }
  });
  box.addEventListener("pointerleave", function(){ s.tx = s.ty = s.px = s.py = -1e4; });
});
})();

/* The rail beside a run of panes (.tp-rail in site.css): the link of the pane
   that holds the middle of the window gets aria-current, and the rail shows
   while any pane does. */
(function(){
"use strict";
var rail = document.querySelector(".tp-rail");
if (!rail || !window.IntersectionObserver) return;
var by = new Map(), links = rail.querySelectorAll('a[href^="#"]');
for (var i = 0; i < links.length; i++) {
  var p = document.getElementById(links[i].getAttribute("href").slice(1));
  if (p) by.set(p, links[i]);
}
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){
    var a = by.get(e.target);
    if (e.isIntersecting) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
  });
  rail.toggleAttribute("data-on", !!rail.querySelector("[aria-current]"));
}, { rootMargin: "-49% 0px -50% 0px" });
by.forEach(function(a, p){ io.observe(p); });
})();

/* TP.sheet: full-screen <dialog class="tp-sheet" id="slug"> sheets. A link to
   #slug opens its sheet, grown out of the link; the URL hash names the open
   sheet, so it can be linked and the back button closes it. Esc and any
   .tp-sheet-close button close it too, and focus returns to the link. The
   dialog is modal, so focus stays inside. Fires tp-sheet-open and
   tp-sheet-close on the dialog. TP.sheet.open(id) and TP.sheet.close(). */
(function(){
"use strict";
var TP = window.TP = window.TP || {};
var d = document.documentElement, still = matchMedia("(prefers-reduced-motion: reduce)");
var cur = null, from = null, pushed = false, anim = null;
var EASE = "cubic-bezier(.2,.75,.15,1)", FULL = "inset(0px 0px 0px 0px round 0px)";
function byId(id){ var el = id && document.getElementById(id); return el && el.tagName === "DIALOG" && el.classList.contains("tp-sheet") ? el : null; }
function hashId(){ try { return decodeURIComponent(location.hash.slice(1)); } catch(e){ return ""; } }
/* an id names a sheet, or something inside one: the sheet then opens there */
function target(id){
  var dlg = byId(id), el = !dlg && id && document.getElementById(id);
  if (dlg) return { dlg: dlg, el: null };
  dlg = el && el.closest("dialog.tp-sheet");
  return dlg ? { dlg: dlg, el: el } : null;
}
function reveal(t){ if (t.el) t.el.scrollIntoView({ block: "start" }); }
function link(id){
  var ls = document.querySelectorAll('a[href="#' + id.replace(/["\\]/g, "") + '"]');
  for (var i = 0; i < ls.length; i++) if (!ls[i].closest(".tp-sheet")) return ls[i];
  return null;
}
function box(el){
  var r = el.getBoundingClientRect(), W = innerWidth, H = innerHeight;
  if (r.bottom < 0 || r.top > H || !r.width) return null;
  return "inset(" + r.top + "px " + (W - r.right) + "px " + (H - r.bottom) + "px " + r.left + "px round 10px)";
}
function finish(){ if (anim) { anim.cancel(); anim = null; } }
function show(dlg, el, grow){
  if (cur === dlg) return;
  if (cur) hide(true);
  finish();
  cur = dlg; from = el || link(dlg.id);
  d.classList.add("tp-sheet-open");
  dlg.showModal();
  dlg.scrollTop = 0;
  var c = dlg.querySelector(".tp-sheet-close");
  if (c) c.focus({ preventScroll: true });
  var b = grow && from && !still.matches && dlg.animate ? box(from) : null;
  if (b) {
    anim = dlg.animate([{ clipPath: b }, { clipPath: FULL }], { duration: 460, easing: EASE });
    var inn = dlg.querySelector(".tp-sheet-in");
    if (inn) inn.animate([{ opacity: 0, transform: "translateY(16px)" }, { opacity: 1, transform: "none" }],
      { duration: 420, delay: 150, easing: EASE, fill: "backwards" });
  }
  dlg.dispatchEvent(new CustomEvent("tp-sheet-open"));
}
function hide(now){
  var dlg = cur, back = from;
  if (!dlg) return;
  cur = null; from = null;
  finish();
  var done = function(){
    finish();
    if (dlg.open) dlg.close();
    if (!cur) {
      d.classList.remove("tp-sheet-open");
      if (back) back.focus();
    }
    dlg.dispatchEvent(new CustomEvent("tp-sheet-close"));
  };
  var b = !now && back && !still.matches && dlg.animate && dlg.open ? box(back) : null;
  if (!b) return done();
  anim = dlg.animate([{ clipPath: FULL }, { clipPath: b }], { duration: 320, easing: "cubic-bezier(.4,0,.2,1)", fill: "forwards" });
  anim.onfinish = done;
}
/* the hash is the state: follow it */
function sync(grow){
  var t = target(hashId());
  if (t) { show(t.dlg, null, grow); reveal(t); }
  else { pushed = false; if (cur) hide(); }
}
function request(){
  if (!cur) return;
  if (pushed) { pushed = false; history.back(); }
  else { history.replaceState(history.state, "", location.pathname + location.search); hide(); }
}
var sheets = document.querySelectorAll("dialog.tp-sheet");
if (!sheets.length) return;
document.addEventListener("click", function(e){
  var a = e.target.closest && e.target.closest('a[href^="#"]');
  if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  var id = decodeURIComponent(a.getAttribute("href").slice(1)), t = target(id);
  if (!t) return;
  e.preventDefault();
  if (cur === t.dlg) { reveal(t); return; }
  history.pushState(history.state, "", "#" + id);
  pushed = true;
  show(t.dlg, a.closest(".tp-sheet") ? null : a, true);
  reveal(t);
});
for (var i = 0; i < sheets.length; i++) (function(dlg){
  dlg.addEventListener("cancel", function(e){ e.preventDefault(); request(); });
  /* closed by the browser itself: catch up */
  dlg.addEventListener("close", function(){ if (cur === dlg) request(); });
  dlg.addEventListener("click", function(e){ if (e.target.closest(".tp-sheet-close")) request(); });
})(sheets[i]);
window.addEventListener("popstate", function(){ sync(true); });
window.addEventListener("hashchange", function(){ sync(true); });
sync(false);
TP.sheet = {
  open: function(id){ var dlg = byId(id); if (dlg && cur !== dlg) { history.pushState(history.state, "", "#" + id); pushed = true; show(dlg, null, true); } },
  close: request
};
})();
