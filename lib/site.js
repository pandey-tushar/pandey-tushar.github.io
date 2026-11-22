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
