/* The site switch and nav, shared by every page but the homepage (which runs
   the same switch inline). The pre-paint snippet in <head> has already put
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
  if (mt) mt.setAttribute("content", light ? "#eef1f8" : "#0b1122");
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
})();
