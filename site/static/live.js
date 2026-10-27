/* Live instruments: /api/live (Server-Sent Events, "stats" every 2 s, closed while the tab is hidden). Formats match
   the daemon's (fr-FR / en-GB; sizes in base 1024, one decimal from 1 Ko / 1 KB). No storage, no cookie.
   Cut shown after 12 s without news only; two short streams (HTTPS filters) switch to /api/stats every 5 s. */
(function () {
"use strict";
var d = document, fr = d.documentElement.lang === "fr", els = d.querySelectorAll("[data-live]");
if (!els.length || !window.EventSource || !window.fetch) return;
var nf = function (o) { return new Intl.NumberFormat(fr ? "fr-FR" : "en-GB", o).format; };
var n0 = nf({ maximumFractionDigits: 0 }), n1 = nf({ minimumFractionDigits: 1, maximumFractionDigits: 1 });
var U = fr ? ["o", "Ko", "Mo", "Go", "To"] : ["B", "KB", "MB", "GB", "TB"];
function bytes(b) {
  var i = 0;
  while (i < 4 && Math.round(b * 10) / 10 >= 1024) { b /= 1024; i++; }
  return (i ? n1(b) : n0(b)) + " " + U[i];
}
var F = { bytes_hour: bytes, bytes_total: bytes, ram_used: bytes, ram_total: bytes, cpu_percent: n1, ram_percent: n1 };
var root = d.querySelector("[data-live-root]"), st = d.querySelector("[data-live-status]");
var say = d.querySelector("[data-live-say]"), es = null, retry = 0, last = 0, seen = "", calm = 0;
var opened = 0, short = 0, poll = 0, quiet = 0;
// Processor and memory move all the time: shown every 10 s, not at each event, to spare the corner of the eye.
var SLOW = { cpu_percent: 1, ram_percent: 1, ram_used: 1 };
function state(on) {
  root.setAttribute("data-state", on ? "on" : "off");
  st.textContent = st.getAttribute(on ? "data-on" : "data-off");
}
function apply(j) {
  var t = j.ram_total_bytes, v = { ram_used: j.ram_used_bytes, ram_total: t, ram_percent: t > 0 ? j.ram_used_bytes / t * 100 : null };
  ["uses_hour", "uses_hour_protocol", "bytes_hour", "docs_total", "docs_protocol", "bytes_total", "visitors_total",
    "visitors_today", "cpu_percent"].forEach(function (k) { v[k] = j[k]; });
  var now = Date.now(), slow = now - calm >= 1e4;
  function ok(x) { return typeof x === "number" && isFinite(x); }
  if (slow) calm = now;
  [].forEach.call(els, function (e) {
    var k = e.getAttribute("data-live"), s;
    if (!ok(v[k]) || SLOW[k] && !slow) return;
    s = (F[k] || n0)(v[k]);
    if (e.textContent !== s) e.textContent = s;
  });
  [].forEach.call(d.querySelectorAll("[data-meter]"), function (m) {
    var p = v[m.getAttribute("data-meter")];
    if (!ok(p) || !slow) return;
    m.firstElementChild.style.transform = "scaleX(" + Math.max(0, Math.min(1, p / 100)) + ")";
    m.classList.add("on");
  });
  // Screen readers: one polite sentence, only when usage or visitors change, at most once a minute.
  var key = v.uses_hour + "/" + v.visitors_total;
  if (!seen) { seen = key; last = now; }
  else if (key !== seen && now - last >= 6e4) {
    seen = key;
    last = now;
    say.textContent = say.getAttribute("data-tpl").replace("{u}", n0(v.uses_hour)).replace("{v}", n0(v.visitors_total));
  }
}
// 12 s without news: "reconnecting"; a stream still open but silent (buffered by a filter) gives way to /api/stats.
function off() { state(false); if (es) { short = 2; stop(); connect(); } }
function fresh(j) {
  apply(j);
  state(true);
  retry = 0;
  clearTimeout(quiet);
  quiet = setTimeout(off, 12e3);
}
function stop() {
  if (es) { es.close(); es = null; }
  clearInterval(poll);
  poll = 0;
}
function read() {
  if (d.hidden) return;
  fetch("/api/stats", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; })
    .then(function (j) { if (j) fresh(j); }, function () { /* next try in 5 s */ });
}
function connect() {
  if (es || poll || d.hidden) return;
  if (short >= 2) { read(); poll = setInterval(read, 5e3); return; }
  es = new EventSource("/api/live");
  opened = Date.now();
  es.addEventListener("stats", function (e) {
    try { fresh(JSON.parse(e.data)); } catch (_) { /* malformed event: ignored */ }
  });
  es.onerror = function () {
    var age = Date.now() - opened;
    if (age >= 6e4) short = 0;
    else if (age < 2e4 && ++short >= 2) { stop(); connect(); return; }
    opened = Date.now();
    if (es && es.readyState === 2) { es = null; setTimeout(connect, Math.min(6e4, 5000 * ++retry)); }
  };
}
// Hidden: nothing open, no count-down; shown: 12 s for news before "reconnecting".
function show() {
  clearTimeout(quiet);
  if (d.hidden) return stop();
  quiet = setTimeout(off, 12e3);
  connect();
}
d.addEventListener("visibilitychange", show);
show();
})();
