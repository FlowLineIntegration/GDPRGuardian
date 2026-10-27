/* Workspace: a session queue sent one request at a time, same origin; results in this tab's memory only (no cookie,
   no IndexedDB; Web Storage keeps the chosen mode only, never a text); files sent as "document.<ext>"; Retry-After
   honoured. Texts: #i18n. */
(function () {
"use strict";
var d = document, form = d.getElementById("ck");
if (!form || !window.AbortController) return;
var fr = d.documentElement.lang === "fr", NB = " ";
function each(l, f) { [].forEach.call(l, f); }
function q(s, r) { return (r || d).querySelector(s); }
function el(tag, cls, text) { var e = d.createElement(tag); e.className = cls || ""; if (text != null) e.textContent = text; return e; }
var T = {};
each(d.querySelectorAll("#i18n [data-k]"), function (li) { T[li.dataset.k] = li.textContent; });
["r", "d", "mo"].forEach(function (p) {
  each((T[p] || "").split("|"), function (s) { var i = s.indexOf("="); if (i > 0) T[p + ":" + s.slice(0, i)] = s.slice(i + 1); });
});
function t(k, v) { var s = T[k] || ""; for (var x in v) s = s.split("{" + x + "}").join(v[x]); return s; }
var nf = function (o) { return new Intl.NumberFormat(fr ? "fr-FR" : "en-GB", o).format; };
var n0 = nf({ maximumFractionDigits: 0 }), n1 = nf({ minimumFractionDigits: 1, maximumFractionDigits: 1 });
function tn(k, n) { return t(n > 1 ? k : k + "1", { n: n0(n) }); }
var U = fr ? ["o", "Ko", "Mo", "Go"] : ["B", "KB", "MB", "GB"];
function bytes(b) {
  var i = 0;
  while (i < 3 && Math.round(b * 10) / 10 >= 1024) { b /= 1024; i++; }
  return (i ? n1(b) : n0(b)) + NB + U[i];
}
function dur2(ms) { return ms < 1000 ? [n0(Math.max(1, ms)), "ms"] : [n1(ms / 1000), "s"]; }
function dur(ms) { return dur2(ms).join(NB); }
function pad(n) { return (n < 10 ? "0" : "") + n; }
function stamp() {
  var n = new Date();
  return n.getFullYear() + "-" + pad(n.getMonth() + 1) + "-" + pad(n.getDate()) + "-" + pad(n.getHours()) + pad(n.getMinutes());
}
// "français / English" messages: the page's half.
function half(s) { s = String(s || ""); var i = s.indexOf(" / "); return i < 0 ? s : fr ? s.slice(0, i) : s.slice(i + 3); }

// R: elements by their data-r name; S: the session tiles.
var R = {}, S = {}, S0 = {};
each(d.querySelectorAll("[data-r]"), function (e) { R[e.dataset.r] = e; });
var ta = q("#ck-t"), fin = q("#ck-f"), sel = form.elements.countries, res = R.res, empty = res.firstElementChild;
var ban = R.ban, lat0 = R.lats.textContent, apiKey = d.getElementById("ck-key");
each(d.querySelectorAll("[data-s]"), function (e) { S[e.dataset.s] = e; S0[e.dataset.s] = e.textContent; });
var exts = fin.getAttribute("accept").split(","), TAG = /\[[A-ZÀ-Þ][A-Z0-9_À-Þ]*_\d+\]|<!-- page \d+ -->/g;
// Q: the session, in order; item.st: wait | run | retry | done | err | stop; item.name is shown here only.
var Q = [], seq = 0, texts = 0, cur = null, follow = true, running = null, ctl = null, paused = "", timer = 0, tick = 0;
var pin = "", hot = null, lit = [], X = {}, ran = 0, vis = null;

function say(m) { R.st.textContent = m; }
function ext(name) { var m = /\.[A-Za-z0-9]+$/.exec(name); return m ? m[0].toLowerCase() : ""; }
function open(it) { return /^(wait|run|retry)$/.test(it.st); }
// --- mode (fort by default), sent as the API and the MCP take it: mode, disable, rules.
var cu = R.cu, kf = form.elements.keep, MK = "gg-mode";
function mode() { return form.querySelector("[name=mode]:checked").value; }
function off() { return [].filter.call(R.cats.querySelectorAll("input"), function (b) { return !b.checked; }).map(function (b) { return b.value; }); }
// Codes to keep, "SKU-###### LOT-@@@@-###": # one digit, @ one letter, the rest as written (a letter A too); each one
// a keep rule, with at least one fixed letter or digit (never a bare "##########": keep rules win in every mode).
// Invalid: false, said under the field; none: null.
function keep() {
  var c = kf.value.split(/[\s,;]+/).filter(Boolean), bad = c.filter(function (x) { return !/^[\w.\/#@-]{2,40}$/.test(x); })[0];
  var fix = c.filter(function (x) { return !/[A-Za-z0-9]/.test(x); })[0];
  var msg = bad ? t("kbad", { c: bad }) : fix ? t("kfix", { c: fix }) : c.length > 20 ? t("kmax") : "";
  R.kerr.textContent = msg;
  kf.setAttribute("aria-invalid", !!msg);
  return msg ? false : c.length ? { rules: c.map(function (x, i) {
    return { label: (/^[A-Za-z]+/.exec(x) || ["CODE"])[0].toUpperCase().slice(0, 24) + "_" + (i + 1), action: "keep",
      pattern: x.replace(/#+|@+|[^#@]/g, function (m) {
        var n = m.length > 1 ? "{" + m.length + "}" : "";
        return m[0] === "#" ? "[0-9]" + n : m[0] === "@" ? "[A-Z]" + n : m === "." ? "\\." : m;
      }) };
  }) } : null;
}
function modeOk() {
  if (mode() !== "personnalise" || keep() !== false) return true;
  say(R.kerr.textContent);
  kf.focus();
  return false;
}
function opts() {
  var m = mode(), o = { countries: sel.value, label: sel.options[sel.selectedIndex].text, mode: m, ml: t("mo:" + m),
    explain: form.elements.explain.checked };
  if (m === "personnalise") { o.disable = off(); o.rules = keep(); }
  return o;
}
// Remembered in this browser, the settings only; the page works without storage.
function remember() {
  cu.hidden = mode() !== "personnalise";
  try { localStorage.setItem(MK, JSON.stringify({ m: mode(), off: off(), k: kf.value })); } catch (e) { /* none */ }
}

// --- queue
function push(it) {
  Object.assign(it, { id: ++seq, st: "wait", tries: 0, o: opts() });
  Q.push(it);
  // The service's own limits, refused here without sending (413, 415); a text's length in characters (code points).
  if (it.file ? it.size > 50 * 1048576 : it.text.replace(/[\ud800-\udbff](?=[\udc00-\udfff])/g, "").length > 1e6) fail(it, 413, 0, 0, 1);
  else if (it.file && exts.indexOf(it.ext) < 0) fail(it, 415, 0, 0, 1);
  return it;
}
// A single refused item keeps its own message; a batch says how many were refused before sending.
function added(list) {
  var e = list.filter(function (x) { return x.st === "err"; }).length;
  if (!list.length) return;
  if (list.length > 1) say(t("add", { n: n0(list.length) }) + (e ? " " + tn("addErr", e) : ""));
  else if (!e) say(t("add1", { l: list[0].name }));
  follow = true;
  select(list[0]);
  pump();
}
function addFiles(files) {
  var list = [];
  if (!modeOk()) return;
  each(files || [], function (f) {
    var x = ext(f.name);
    list.push(push({ file: f, name: f.name, ext: x, kind: x.slice(1).toUpperCase() || "?", size: f.size }));
  });
  added(list);
}
function addText(v) { added([push({ text: v, name: t("tname", { n: n0(++texts) }), kind: t("text"), ext: "", size: new Blob([v]).size })]); }
function submit() {
  var v = ta.value;
  if (!v.trim()) { say(t("empty")); ta.focus(); return; }
  if (!modeOk()) return;
  ta.value = "";
  addText(v);
  ta.focus();
}

// One request at a time; an item waiting for its Retry-After holds the queue.
function pump() {
  clearTimeout(timer);
  for (var i = 0, now = Date.now(); !running && !paused && i < Q.length; i++) {
    var it = Q[i];
    if (it.st === "retry") {
      if (it.at > now) { timer = setTimeout(pump, it.at - now + 30); break; }
      it.st = "wait";
    }
    if (it.st === "wait") { send(it); break; }
  }
  draw();
  // A batch that ends says its outcome (the queue header keeps it).
  if (!running && !paused && ran && !Q.some(open)) { if (ran > 1 && R.qn.textContent) say(t("fin", { s: R.qn.textContent })); ran = 0; }
}

// XHR, not fetch: upload progress (it.up). No cookie exists on this origin to send.
function send(it) {
  var o = it.o, x = new XMLHttpRequest(), start = performance.now(), body,
    f = { countries: o.countries, label_language: fr ? "fr" : "en", explain: o.explain };
  // fort is the service's default: sent only when another mode is chosen (an engine before 1.0.2 refuses "mode").
  if (o.mode !== "fort") f.mode = o.mode;
  if (o.disable && o.disable.length) f.disable = o.disable;
  if (o.rules) f.rules = o.rules;
  if (it.file) {
    body = new FormData();
    body.append("file", it.file, "document" + it.ext);
    // Form fields: disable comma-separated, rules as JSON text.
    for (var k in f) body.append(k, k === "rules" ? JSON.stringify(f[k]) : "" + f[k]);
  } else { f.text = it.text; body = JSON.stringify(f); }
  running = it;
  ctl = x;
  ran++;
  Object.assign(it, { st: "run", t0: Date.now(), t1: it.file ? 0 : Date.now(), why: "", up: it.file ? 0 : 1 });
  x.open("POST", "/v1/anonymize/" + (it.file ? "file" : "text"));
  if (!it.file) x.setRequestHeader("Content-Type", "application/json");
  // Clé API, en mémoire seulement / API key, kept in memory only.
  if (apiKey.value.trim()) x.setRequestHeader("Authorization", "Bearer " + apiKey.value.trim());
  // The service's bounds: the body within 15 s + size at 131072 B/s, then two deadlines of 60 s + size / 25e4 B/s
  // (one maximal job ahead, then this one), 30 s margin. tests/server/test_big_documents.py checks these numbers.
  x.timeout = (165 + it.size * (1 / 131072 + 2 / 25e4)) * 1e3;
  x.upload.onprogress = function (e) { if (e.lengthComputable) it.up = e.loaded / e.total; };
  x.upload.onload = function () { it.up = 1; it.t1 = Date.now(); };
  x.ontimeout = function () { it.why = "time"; };
  // Deferred: an abort (Stop, Clear) ends the request before its handler runs, as a rejected fetch did.
  x.onloadend = function () { setTimeout(end); };
  x.send(body);
  function end() {
    var s = x.status, ms = performance.now() - start, j = null, p = dur2(ms);
    if (s) {
      try { j = JSON.parse(x.responseText); } catch (_) { j = null; }
      R.lat.textContent = p[0];
      R.latu.textContent = p[1];
      R.lats.textContent = s < 400 ? t("sub", { k: it.kind, s: bytes(it.size) }) : t("subErr", { c: s });
      if (s > 199 && s < 300 && j) done(it, j, ms); else fail(it, s, j, x.getResponseHeader("Retry-After"));
    } else if (it.why === "time") fail(it, "time"); else if (it.why) it.st = "stop"; else fail(it, 0);
    if (running === it) running = ctl = null;
    if (follow && Q.indexOf(it) >= 0 && /done|err/.test(it.st)) {
      select(it);
      // Phones: the result sits below the input; bring it into view.
      if (res.getBoundingClientRect().top > innerHeight - 80) res.parentNode.scrollIntoView();
    }
    else if (it === cur) show();
    pump();
  }
}

function done(it, j, ms) {
  var r = j.report || {}, ent = r.entities || {}, m;
  // am: the mode the service says it applied (none from an engine without modes).
  Object.assign(it, { st: "done", ms: ms, out: typeof j.text === "string" ? j.text : String(j.markdown || ""), rep: r,
    am: typeof r.mode === "string" ? T["mo:" + r.mode] || r.mode : "",
    pages: j.pages || 0, warn: [].concat(j.warnings || [], r.warnings || []).filter(function (w, i, a) { return a.indexOf(w) === i; }), dropped: j.dropped || {} });
  it.total = typeof r.total_replaced === "number" ? r.total_replaced : Object.keys(ent).reduce(function (s, k) { return s + ent[k]; }, 0);
  it.N = {};
  TAG.lastIndex = 0;
  while ((m = TAG.exec(it.out))) if (m[0][0] === "[") it.N[m[0]] = (it.N[m[0]] || 0) + 1;
  it.tags = Object.keys(it.N).length;
  say(t("sayDone", { l: it.name, m: it.total ? tn("men", it.total) : t("none") }));
}

// Retry-After in seconds, as the service and nginx send it; 10 s when absent.
function retryAfter(v) { var n = Math.ceil(v); return n > 0 ? Math.min(n, 600) : 10; }

// s: HTTP status, 0 (network) or "time" (no answer in time); local: refused here, before sending.
function fail(it, s, j, ra, local) {
  var e = j && j.error || {}, k = "eGen", b = "", h = "", p;
  if (s === 429 || s === 503) {
    it.note = T[e.code] || "";
    if (++it.tries <= 3) {
      it.st = "retry";
      it.at = Date.now() + retryAfter(ra) * 1000;
      return say(t("retryLong"));
    }
    it.tries = 0;
    h = t("hold" + s);
  } else if (!s || s === 502 || s === 504) {
    p = t(s ? "e502" : "eNet").split("|");
    h = p[0] + ". " + p[1];
  }
  if (h) { paused = h; it.st = "wait"; return say(h); }
  if (s === 422) { k = "e422"; b = T[e.code] || half(e.message) || t("invalid_request"); }
  // A short item that gets no answer in time: the service is busy, splitting it would not help.
  else if (s === "time") k = it.size > 1048576 ? "eTime" : "eTimeS";
  else if ([401, 403, 408, 413, 415, 501].indexOf(s) >= 0) {
    k = "e" + s;
    // The service names the limit reached (file, text, converted document, pages...).
    if (s === 413) b = half(e.message);
  }
  else b = half(e.message);
  p = t(k).split("|");
  it.st = "err";
  it.err = { h: p[0], b: b || p[1] || "", c: local || !+s ? "" : "HTTP " + s, ref: /^(413|415|422|time)$/.test(s) };
  say(t("sayErr", { l: it.name, c: it.err.b || it.err.h }));
}

// --- drawing
// Time left before the next try: seconds, minutes beyond 60 s.
function left(it) { var s = Math.max(1, Math.ceil((it.at - Date.now()) / 1000)); return s > 60 ? n0(Math.ceil(s / 60)) + NB + "min" : n0(s) + NB + "s"; }
// While a file uploads: its share sent; then the time since the upload ended.
function busy(it, k, sep) { return it.up < 1 ? t("up", { p: n0(it.up * 100 | 0) }) : t(k) + sep + n0((Date.now() - (it.t1 || it.t0)) / 1000 | 0) + NB + "s"; }
function state(it) {
  var s = it.st;
  if (s === "run") return busy(it, "run", " · ");
  if (s === "retry") return t("retry", { s: left(it) });
  if (s === "done") return (it.total ? tn("men", it.total) : t("none")) + " · " + dur(it.ms);
  if (s === "err") return it.err.h;
  return t(s);
}
function row(it) {
  if (!it.li) {
    var li = it.li = el("li"), b = it.b = el("button");
    [["i", pad(it.id)], ["nm", it.name], ["z", (it.file ? it.kind + " · " : "") + bytes(it.size)], ["s"]]
      .forEach(function (x) { it.s = b.appendChild(el("span", x[0], x[1])); });
    b.addEventListener("click", function () { follow = it === Q[Q.length - 1]; select(it); });
    li.appendChild(b);
    R.ql.appendChild(li);
  }
  it.li.dataset.st = it.st;
  it.b.setAttribute("aria-current", it === cur);
  it.s.textContent = state(it);
}
// Counts as words, nonzero only: "4 terminés · 2 refusés · 3 en file".
function sum(c) { return c.filter(function (x) { return x[1]; }).map(function (x) { return tn(x[0], x[1]); }).join(" · "); }
// Keeps a queue row in view inside the list, without scrolling the page.
function seen(it) {
  var l = R.ql, a = it.li.getBoundingClientRect(), b = l.getBoundingClientRect();
  l.scrollTop += a.top < b.top ? a.top - b.top : a.bottom > b.bottom ? a.bottom - b.bottom : 0;
}
function draw() {
  var n = 0, w = 0, e = 0, men = 0, tags = 0, vol = 0, ms = 0, live = 0;
  Q.forEach(function (it) {
    row(it);
    if (it.st === "done") { n++; men += it.total; tags += it.tags; vol += it.size; ms += it.ms; }
    else if (open(it)) { w++; live += it.st !== "wait"; }
    else e += it.st === "err";
  });
  var v = { docs: n0(n), docs2: sum([["qw", w], ["qr", e]]) || t("docs0"), men: n0(men), men2: tags ? tn("men2", tags) : t("men20"),
    vol: bytes(vol), time: n ? dur(ms) : S0.time, time2: n ? t("time2", { t: dur(ms / n) }) : S0.time2 };
  for (var k in v) S[k].textContent = v[k];
  R.qn.textContent = sum([["qd", n], ["qr", e], ["qw", w]]);
  R.qe.hidden = !!Q.length;
  R.zip.disabled = !n;
  R.stop.disabled = !running;
  if (follow && running && running !== vis) seen(vis = running);
  R.hold.hidden = !paused;
  R.hold.firstChild.textContent = paused;
  if (cur && open(cur)) note();
  if (live && !tick) tick = setInterval(function () {
    if (!Q.some(function (x) { return /run|retry/.test(x.st); })) { clearInterval(tick); tick = 0; }
    draw();
  }, 1000);
}

function select(it) {
  var prev = cur;
  cur = it;
  if (prev && prev.li) row(prev);
  if (it) { row(it); seen(it); }
  show();
}
function show() {
  var it = cur, ok = it && it.st === "done";
  pin = "";
  hot = null;
  lit = [];
  R.rep.hidden = !ok;
  ban.hidden = true;
  R.copy.disabled = R.dl.disabled = !ok;
  R.redo.hidden = R.rm.hidden = !it;
  R.orig.hidden = !it || it.text == null;
  res.textContent = "";
  if (!it) { R.what.textContent = ""; res.appendChild(empty); return; }
  R.what.textContent = [pad(it.id) + " · " + it.name, it.file && it.kind, it.pages && tn("pages", it.pages), bytes(it.size),
    ok && dur(it.ms), it.o.label, ok ? it.am : it.o.ml].filter(Boolean).join(" · ");
  if (ok) return render(it);
  if (it.st === "err") {
    each(ban.querySelectorAll("b,span,code"), function (e, i) { e.textContent = [it.err.h, it.err.b, it.err.c][i]; });
    ban.classList.toggle("ref", it.err.ref);
    ban.hidden = false;
    return;
  }
  res.appendChild(el("p", "st"));
  note();
}
function note() {
  var p = res.firstChild, it = cur, n = 0;
  if (!p || p.className !== "st") return;
  for (var i = 0; i < Q.length && Q[i] !== it; i++) n += open(Q[i]);
  p.textContent = it.st === "wait" ? paused || t("before", { n: n0(n) })
    : it.st === "run" ? busy(it, "busy", " ")
    : it.st === "retry" ? [it.note, t("retryLong"), t("retryIn", { s: left(it) })].filter(Boolean).join(" ") : t(it.st);
}

function num(g) { return +g.slice(g.lastIndexOf("_") + 1, -1); }
// Built node by node, never parsed as HTML; odd numbers filled, even outlined. Then the report.
function render(it) {
  var text = it.out, s = text.slice(0, 2e5), pre = el("pre", "out"), last = 0, m, g, mk, b = s.lastIndexOf("[");
  var r = it.rep, ent = r.entities || {}, dist = {}, p = R.ledger, ul = R.warn, parts = [], tb = R.xrows, xs = r.explain || [];
  // The preview cut never splits a placeholder.
  if (s !== text && b > 2e5 - 40 && s.indexOf("]", b) < 0) s = s.slice(0, b);
  TAG.lastIndex = 0;
  while ((m = TAG.exec(s))) {
    g = m[0];
    pre.appendChild(d.createTextNode(s.slice(last, m.index)));
    if (g[0] === "<") mk = el("span", "pg", g);
    else {
      mk = el("mark", num(g) % 2 ? "p1" : "p2", g);
      mk.dataset.k = g;
    }
    pre.appendChild(mk);
    last = TAG.lastIndex;
  }
  pre.appendChild(d.createTextNode(s.slice(last)));
  if (s !== text) res.appendChild(el("p", "notice", t("cut", { n: n0(2e5) })));
  res.appendChild(pre);
  res.scrollTop = 0;
  for (var k in it.N) { var y = k.slice(1, k.lastIndexOf("_")); dist[y] = (dist[y] || 0) + 1; }
  p.textContent = "";
  Object.keys(ent).sort(function (a, b) { return ent[b] - ent[a] || (a < b ? -1 : 1); }).forEach(function (k, i) {
    var n = dist[k] || 0;
    if (i) p.appendChild(d.createTextNode(" · "));
    p.appendChild(el("span", null, k + " " + n0(ent[k]) + (n && n < ent[k] ? " (" + tn("tag", n) + ")" : "")));
  });
  X = {};
  tb.textContent = "";
  R.xpl.hidden = !xs.length;
  xs.forEach(function (x, i) {
    if (x.tag) (X[x.tag] = X[x.tag] || []).push(x);
    if (i >= 1000) return;
    var tr = el("tr"), tag = el("td"), why = el("td", null, x.reason), gl = T["r:" + x.reason], b;
    if (x.tag) {
      b = el("button", "tg " + (num(x.tag) % 2 ? "p1" : "p2"), x.tag);
      tr.dataset.k = b.dataset.k = x.tag;
      b.setAttribute("aria-pressed", false);
      tag.appendChild(b);
    } else tag.textContent = t("kept", { l: x.kept || "" });
    if (gl) why.appendChild(el("span", "xg", gl));
    [tag, el("td", null, x.rule), why, el("td", null, n0(x.count || 1))].forEach(function (c) { tr.appendChild(c); });
    tb.appendChild(tr);
  });
  ul.textContent = "";
  it.warn.forEach(function (w) { ul.appendChild(el("li", null, half(w))); });
  Object.keys(it.dropped).forEach(function (k) { parts.push((T["d:" + k] || k.replace(/_/g, " ")) + " " + n0(it.dropped[k])); });
  if (parts.length) ul.appendChild(el("li", null, t("dropped", { l: parts.join(", ") })));
  ul.hidden = !ul.firstChild;
  R.notice.textContent = r.notice || "";
  inspect("");
}

// Hover previews, click or tap pins; keyboard: the table's tag buttons. The inspector line says why.
function light(k) {
  if (k === hot) return;
  hot = k;
  each(lit, function (e) { e.classList.remove("on"); });
  lit = [];
  if (k) each(d.querySelectorAll('mark[data-k="' + k + '"],tr[data-k="' + k + '"]'), function (e) { e.classList.add("on"); lit.push(e); });
  inspect(k);
}
function inspect(k) {
  var n = cur && cur.N && cur.N[k], rules = [], why = [];
  R.insp.classList.toggle("idle", !n);
  if (!n) return (R.insp.textContent = t("insp"));
  (X[k] || []).forEach(function (x) {
    var g = T["r:" + x.reason] || x.reason;
    if (rules.indexOf(x.rule) < 0) rules.push(x.rule);
    if (why.indexOf(g) < 0) why.push(g);
  });
  R.insp.textContent = [k, tn("men", n), rules.join(", "), why.join(" ; ")].filter(Boolean).join(" · ");
}
function key(e) { var x = e.target.closest("[data-k]"); return x ? x.dataset.k : ""; }
function ready() { return cur && cur.st === "done"; }
[res, R.xpl].forEach(function (z) {
  z.addEventListener("mouseover", function (e) { if (ready()) light(key(e) || pin); });
  z.addEventListener("mouseleave", function () { if (ready()) light(pin); });
  z.addEventListener("click", function (e) {
    var k = key(e);
    if (!k || !ready()) return;
    pin = pin === k ? "" : k;
    hot = null;
    light(pin);
    each(R.xrows.querySelectorAll("button"), function (b) { b.setAttribute("aria-pressed", b.dataset.k === pin); });
  });
});
R.xpl.addEventListener("focusin", function (e) { if (ready()) light(key(e) || pin); });

// --- results out: copy, .md, .zip
function fileName(it, s) { return t("file", { n: pad(it.id), k: it.file ? it.ext.slice(1) : t("text"), d: s }); }
function save(blob, name) {
  var url = URL.createObjectURL(blob), a = Object.assign(el("a"), { href: url, download: name });
  d.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
}
function copy() {
  if (!ready()) return say(t("nores"));
  var ko = function () { say(t("nocopy")); };
  if (navigator.clipboard) navigator.clipboard.writeText(cur.out).then(function () { say(t("copied")); }, ko);
  else ko();
}
function download() {
  if (ready()) save(new Blob([cur.out], { type: "text/markdown;charset=utf-8" }), fileName(cur, stamp()));
  else say(t("nores"));
}
var CRC;
function crc32(u) {
  var c, x = -1, i, k;
  if (!CRC) for (CRC = new Int32Array(256), i = 0; i < 256; CRC[i++] = c) for (c = i, k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ c >>> 1 : c >>> 1;
  for (i = 0; i < u.length; i++) x = CRC[(x ^ u[i]) & 255] ^ x >>> 8;
  return (x ^ -1) >>> 0;
}
// ZIP, "stored" entries with UTF-8 names (flag 0x800): local headers, central directory, end record.
function zip(files) {
  var parts = [], dir = [], off = 0, size = 0, w = new Date();
  var tm = w.getHours() << 11 | w.getMinutes() << 5 | w.getSeconds() >> 1;
  var dt = (w.getFullYear() - 1980) << 9 | (w.getMonth() + 1) << 5 | w.getDate();
  function rec(len, sig, v16, v32) {
    var v = new DataView(new ArrayBuffer(len));
    [[0, sig]].concat(v32).forEach(function (x) { v.setUint32(x[0], x[1], true); });
    v16.forEach(function (x) { v.setUint16(x[0], x[1], true); });
    return v;
  }
  files.forEach(function (f) {
    var c = crc32(f.data), n = f.data.length, l = f.name.length;
    parts.push(rec(30, 0x04034b50, [[4, 20], [6, 0x800], [10, tm], [12, dt], [26, l]], [[14, c], [18, n], [22, n]]), f.name, f.data);
    dir.push(rec(46, 0x02014b50, [[4, 20], [6, 20], [8, 0x800], [12, tm], [14, dt], [28, l]], [[16, c], [20, n], [24, n], [42, off]]), f.name);
    off += 30 + l + n;
    size += 46 + l;
  });
  dir.push(rec(22, 0x06054b50, [[8, files.length], [10, files.length]], [[12, size], [16, off]]));
  return new Blob(parts.concat(dir), { type: "application/zip" });
}
R.zip.addEventListener("click", function () {
  var enc = new TextEncoder(), s = stamp(), files = [];
  Q.forEach(function (it) { if (it.st === "done") files.push({ name: enc.encode(fileName(it, s)), data: enc.encode(it.out) }); });
  if (files.length) save(zip(files), t("zip", { d: s }));
});
R.copy.addEventListener("click", copy);
R.dl.addEventListener("click", download);

// --- item actions, clearing
function abort(why) { if (running) { running.why = why; ctl.abort(); } }
R.stop.addEventListener("click", function () { abort("stop"); back(); });
R.redo.addEventListener("click", function () {
  var it = cur;
  if (!it || it === running) return;
  Object.assign(it, { o: opts(), st: "wait", tries: 0 });
  follow = true;
  show();
  pump();
});
// Never over a draft.
R.orig.addEventListener("click", function () { if (ta.value.trim()) say(t("busyIn")); else ta.value = cur.text; ta.focus(); });
R.rm.addEventListener("click", function () {
  var i = Q.indexOf(cur), next;
  if (i < 0) return;
  if (cur === running) abort("stop");
  cur.li.remove();
  Q.splice(i, 1);
  next = Q[i] || Q[i - 1] || null;
  select(next);
  pump();
  (next ? next.b : ta).focus();
});
function back() { (cur ? cur.b : ta).focus(); }
R.resume.addEventListener("click", function () { paused = ""; pump(); back(); });
R.clear.addEventListener("click", function () {
  abort("clear");
  running = ctl = vis = null;
  // Every trace of the session in the page: queue, last report (hidden but still in the DOM), banner, inspector.
  paused = ta.value = R.ql.textContent = "";
  [R.xrows, R.ledger, R.warn, R.notice, R.insp].concat([].slice.call(ban.querySelectorAll("b,span,code"))).forEach(function (e) { e.textContent = ""; });
  Q = [];
  X = {};
  seq = texts = ran = 0;
  follow = true;
  R.lat.textContent = "—";
  R.latu.textContent = "";
  R.lats.textContent = lat0;
  select(null);
  pump();
  say(t("cleared"));
  ta.focus();
});

// --- input: submit, keys, paste and drop anywhere
form.addEventListener("submit", function (e) { e.preventDefault(); submit(); });
// The example goes straight to the queue: a draft in the input stays as it is.
q("[data-ex]").addEventListener("click", function () { if (modeOk()) addText(this.getAttribute("data-ex")); });
form.querySelector(".md").addEventListener("change", remember);
cu.addEventListener("change", remember);
kf.addEventListener("input", function () { keep(); remember(); });
// Enter in the codes field does not send the text; Ctrl + Enter still does.
kf.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) e.preventDefault(); });
fin.addEventListener("change", function () { addFiles(fin.files); fin.value = ""; });
sel.addEventListener("change", function () { R.hint.hidden = sel.value === "FR"; });
d.addEventListener("keydown", function (e) {
  var m = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  if (m && k === "enter") { e.preventDefault(); submit(); }
  else if (m && e.shiftKey && k === "c") { e.preventDefault(); copy(); }
  else if (m && !e.shiftKey && k === "s") { e.preventDefault(); download(); }
  else if (k === "escape" && !e.defaultPrevented) {
    if (panel()) close();
    // Only from the input itself, and as an edit: Ctrl + Z brings the text back.
    else if (e.target === ta && ta.value) { ta.select(); edit(""); say(t("esc")); }
  }
});
// Text changes the browser can undo; plain assignment where execCommand is gone.
function edit(s) { if (!d.execCommand(s ? "insertText" : "delete", false, s)) ta.setRangeText(s, ta.selectionStart, ta.selectionEnd, "end"); }
d.addEventListener("paste", function (e) {
  var c = e.clipboardData, g = e.target, s = c && c.getData("text/plain");
  if (!c) return;
  // Pasted files are documents; but a copy from Word or Excel also carries a picture of itself: the text wins.
  if (c.files.length && !(s && [].every.call(c.files, function (f) { return /^image\//.test(f.type); }))) { e.preventDefault(); return addFiles(c.files); }
  if (g === ta || g.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(g.tagName) || !s) return;
  // Pasted outside the input: inserted at its caret, the draft kept.
  e.preventDefault();
  ta.focus();
  edit(s);
  say(t("pasted"));
});
var depth = 0, root = d.documentElement;
function files(e) { return e.dataTransfer && [].indexOf.call(e.dataTransfer.types, "Files") >= 0; }
function over(on) { root.classList.toggle("drag", on); if (!on) depth = 0; }
addEventListener("dragenter", function (e) { if (files(e)) { e.preventDefault(); depth++; over(true); } });
addEventListener("dragleave", function (e) { if (files(e) && --depth <= 0) over(false); });
addEventListener("dragover", function (e) { if (files(e)) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; } });
addEventListener("drop", function (e) { if (files(e)) { e.preventDefault(); over(false); addFiles(e.dataTransfer.files); } });

// --- learn-more panels: :target shows them; here focus, Esc and the way back
// Closing replaces the panel's history entry: Back then leaves the page as it was before the panel.
var home = q(".app").id, opener = null;
function panel() {
  var p = location.hash.length > 1 && d.getElementById(location.hash.slice(1));
  return p && p.classList.contains("pn") ? p : null;
}
function close() { location.replace("#" + home); }
function onHash() {
  var p = panel();
  each(d.querySelectorAll(".more a"), function (a) { a.setAttribute("aria-current", !!p && a.hash === "#" + p.id); });
  // Hidden, a video plays on.
  each(d.querySelectorAll(".pn video"), function (v) { if (v.closest(".pn") !== p) v.pause(); });
  if (p) { p.scrollTop = 0; q("h2", p).focus({ preventScroll: true }); return; }
  if (opener) opener.focus();
  opener = null;
}
var mail = 0;
d.addEventListener("click", function (e) {
  var a = e.target.closest("a[href^='#']"), p = a && d.getElementById(a.hash.slice(1));
  if (e.target.closest("a[href^='mailto:']")) mail = Date.now();
  if (!p) return;
  if (p.classList.contains("pn")) opener = opener || a;
  else if (p.id === home) { e.preventDefault(); close(); }
});
addEventListener("hashchange", onHash);
// Leaving the page (language, reload, a link in this tab) would wipe the session: the browser asks first. Not for
// an e-mail link, which some browsers announce as an unload although the page stays.
addEventListener("beforeunload", function (e) { if ((Q.length || ta.value) && Date.now() - mail > 2e3) { e.preventDefault(); e.returnValue = ""; } });

R.dz.firstChild.textContent = t("dropHint");
if (/Mac|iP/.test(navigator.platform)) { R.keys.textContent = R.keys.textContent.split("Ctrl").join("⌘"); for (var k in T) T[k] = T[k].split("Ctrl").join("⌘"); }
// Categories of the custom mode (#i18n "cats"), all masked at first; then the settings this browser kept.
each((T.cats || "").split("|"), function (s) {
  var i = s.indexOf("="), l = el("label", "chk"), b = el("input");
  b.type = "checkbox"; b.name = "cat"; b.value = s.slice(0, i); b.checked = true;
  l.append(b, el("span", "", s.slice(i + 1)));
  R.cats.append(l);
});
try {
  var st = JSON.parse(localStorage.getItem(MK)) || {};
  each(form.elements.mode, function (r) { if (r.value === st.m) r.checked = true; });
  each(R.cats.querySelectorAll("input"), function (b) { b.checked = (st.off || []).indexOf(b.value) < 0; });
  if (typeof st.k === "string") { kf.value = st.k; keep(); }
} catch (e) { /* no storage: fort */ }
cu.hidden = mode() !== "personnalise";
R.go.disabled = false;
R.hint.hidden = sel.value === "FR";
onHash();
if (!panel() && matchMedia("(pointer:fine)").matches) ta.focus({ preventScroll: true });
draw();
})();
