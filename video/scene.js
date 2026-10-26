/* Gardien RGPD / GDPR Guardian, launch video.
   One page, one deterministic timeline: render(t) sets every animated property from t alone (no CSS transition or
   animation, no clock), so a frame is identical whenever it is captured. All text comes from facts.<lang>.json; the
   test count, the red-team and real-corpus counts and the confidence index come from ../site/data/quality.json at
   every render (the other figures of the public run are written in the facts files), so
   the video says what the site says and switches from "being measured" to the measured index by itself.
   Two formats from the same source: ?fmt=wide (1920 x 1080, the full video) and ?fmt=social (1080 x 1350, a short
   cut for phone feeds, with larger type and fewer words; facts.<lang>.json "social" overrides the texts).
   Reading rule (owner's brief): every text stays on screen at least 0.35 s per word (short labels count half) and at
   least 2.5 s; a scene lasts until everything it shows could have been read, in order, from its first step. A
   headline and its body arrive together (0.35 s apart) and scenes cross-fade, so no frame holds a headline alone.
   Exposed to render.py: window.READY, window.render(t) -> frame signature, window.TIMELINE, window.transcript(),
   window.readability(), window.posterTime(). */
'use strict';

const FPS = 30, READ = 0.35, MIN_LINE = 2.5, LABEL = 0.5;
// A scene fades out over FADE while the next one starts XF before its end: the next texts arrive (LEAD after its
// start) as the last ones leave, with no blank frame and no two headlines mixed.
const LEAD = 0.3, FADE = 0.5, XF = 0.4, HEAD = 0.35, BREATH = 0.25, LEGIBLE = 0.15; // legible 0.15 s after it starts
const QS = new URLSearchParams(location.search);
const LANG = QS.get('lang') === 'en' ? 'en' : 'fr';
const SOCIAL = QS.get('fmt') === 'social';
const W = SOCIAL ? 1080 : 1920, H = SOCIAL ? 1350 : 1080;
const CAPTURE = QS.has('capture');

const stage = document.getElementById('stage');
const SCENES = [], MEASURE = [];
let F = null, Q = null, CHROME = null, TOTAL = 0, UID = 0;
let SIG = [];

/* ---------- small helpers ---------- */
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = p => 1 - Math.pow(1 - p, 3);
const easeIO = p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const r3 = x => Math.round(x * 1000) / 1000;
const r1 = x => Math.round(x * 10) / 10;
const frames = s => Math.round(s * FPS) / FPS;

function h(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

// Inline markup allowed in facts.*.json: <b> <m> (mono) <mu> (muted) <p0> <p1> <p2> <p3> (placeholders: p1 and p2
// are people, p3 anything else), <n1> <n2> (original names), <arrow/>, and \n for a line break. Everything else is
// escaped.
const TAGS = { b: 'b', m: 'mono', mu: 'mu', p0: 'ph p0', p1: 'ph p1', p2: 'ph p2', p3: 'ph p3', n1: 'nm n1', n2: 'nm n2' };
const ARROW = '<svg class="arr" viewBox="0 0 30 14" aria-hidden="true"><path d="M1 7H27M21 1.5 27 7l-6 5.5"/></svg>';
function rich(src) {
  const re = /<(\/?)(b|m|mu|p0|p1|p2|p3|n1|n2)>|<arrow\/>|\n/g;
  let out = '', i = 0, m;
  while ((m = re.exec(src))) {
    out += esc(src.slice(i, m.index));
    if (m[0] === '\n') out += '<br>';
    else if (m[0] === '<arrow/>') out += ARROW;
    else out += m[1] ? '</span>' : `<span class="${TAGS[m[2]]}">`;
    i = re.lastIndex;
  }
  return out + esc(src.slice(i));
}
function plain(src) {
  return String(src).replace(/<arrow\/>/g, '→').replace(/<\/?(b|m|mu|p0|p1|p2|p3|n1|n2)>/g, '').replace(/\s*\n\s*/g, ' ');
}
function hr(tag, cls, src) { const e = h(tag, cls, rich(src)); e._src = src; return e; }

// Words a viewer reads: tokens with a letter or digit; a run of number groups ("06 12 34 56 78") reads as one.
function countWords(s) {
  let n = 0, prevNum = false;
  for (const w of String(s).replace(/[  ]/g, ' ').split(/\s+/)) {
    if (!/[\p{L}\p{N}]/u.test(w)) continue;
    const num = /^[\d.,+%–-]+$/.test(w);
    if (num && prevNum) continue;
    n++; prevNum = num;
  }
  return n;
}

// The texts of a section, with the social cut's overrides when rendering that format (null removes a key).
function pick(key) {
  const base = F[key] || {}, over = SOCIAL && F.social ? F.social[key] : null;
  if (!over) return base;
  const out = { ...base };
  for (const [k, v] of Object.entries(over)) if (v === null) delete out[k]; else out[k] = v;
  return out;
}

function markSVG(cls) {
  const d = h('div', null,
    `<svg class="mark ${cls || ''}" viewBox="0 0 24 24" aria-hidden="true"><path class="mk" d="M7 4H4v16h3"/>` +
    `<path class="mk" d="M17 4h3v16h-3"/><rect class="mb" x="7.5" y="10" width="9" height="4"/></svg>`);
  return d.firstChild;
}
function svgEl(tag, attrs) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  return e;
}
function flowSVG() {
  const fw = SOCIAL ? 936 : 1680, fh = SOCIAL ? 1130 : 792;
  const svg = svgEl('svg', { class: 'flowline', width: fw, height: fh, viewBox: `0 0 ${fw} ${fh}` });
  svg.style.cssText = `left:0;top:0;width:${fw}px;height:${fh}px`;
  return svg;
}

/* ---------- recorded property setters: every frame's values form its signature ---------- */
function uid(el) { if (!el._uid) el._uid = ++UID; return el._uid; }
function setStyle(el, prop, val) {
  const k = '_s_' + prop;
  if (el[k] !== val) { el.style.setProperty(prop, val); el[k] = val; }
  SIG.push(uid(el) + prop + val);
}
function setText(el, val) {
  if (el._t !== val) { el.textContent = val; el._t = val; }
  SIG.push(uid(el) + 'T' + val);
}
function setClass(el, val) {
  if (el._c !== val) { el.setAttribute('class', val); el._c = val; }
  SIG.push(uid(el) + 'C' + val);
}
function hash(str) { // cyrb53
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < str.length; i++) {
    const c = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36) + ':' + str.length;
}

/* ---------- scenes, steps, items ---------- */
class Scene {
  constructor(id, chapter, opts = {}) {
    this.id = id; this.chapter = chapter; this.chrome = chapter != null;
    this.final = !!opts.final; this.hold = opts.hold ?? BREATH; this.lead = opts.lead ?? LEAD;
    this.steps = []; this.items = []; this.customs = []; this.notes = [];
    this.root = h('section', 'scene ' + id); this.fr = h('div', 'fr'); this.root.append(this.fr);
    stage.append(this.root); SCENES.push(this);
  }
  // gap: the step lasts at least this long; fixed: the step lasts exactly this long (its reading time is then owed
  // at the end of the scene, which holds until everything has been read)
  step(o = {}) {
    this.cur = { pre: o.pre || 0, gap: o.gap || 0, fixed: o.fixed, extra: o.words || 0, items: [], t: 0 };
    this.steps.push(this.cur); return this.cur;
  }
  // a headline: its body follows 0.35 s later instead of waiting until the headline has been read
  headline(el, o = {}) { this.step({ fixed: HEAD }); return this.show(el, o); }
  // anim: up | left | fade | static | grow (scaleX) | growc (scaleX, centred) | draw (SVG stroke) | type (typed text)
  show(el, o = {}) {
    const text = o.text ?? (el._src != null ? plain(el._src) : el.textContent);
    const words = o.words ?? countWords(text) * (o.label ? LABEL : 1);
    const it = { el, text, words, anim: o.anim || 'up', dt: o.dt || 0, dur: o.dur || 0.7, step: this.cur, transcript: o.transcript ?? words > 0 };
    if (it.anim === 'type') { it.full = o.full; it.tx = o.tx; it.caret = o.caret; it.dur = o.dur || Math.max(0.6, o.full.length / 34); }
    this.cur.items.push(it); this.items.push(it);
    return el;
  }
  // show el in the current step, as soon as what the step already shows has been read
  after(el, o = {}) { return this.show(el, { ...o, dt: readEnd(this.cur.items) + (o.dt || 0) }); }
  custom(fn) { this.customs.push(fn); }
  note(text, atFn) { this.notes.push({ text, atFn }); }
}

// Reading is sequential: an item is read once it is legible and once what came before it has been read.
function readEnd(items) {
  let f = 0;
  for (const it of [...items].sort((a, b) => a.dt - b.dt)) if (it.words) f = Math.max(f, it.dt + LEGIBLE) + it.words * READ;
  return f;
}

function schedule() {
  let start = 0;
  SCENES.forEach(S => {
    let t = S.lead;
    for (const st of S.steps) {
      st.t = t + st.pre;
      let lastDt = 0, words = st.extra;
      for (const it of st.items) {
        it.at = st.t + it.dt;
        if (it.words) lastDt = Math.max(lastDt, it.dt);
        words += it.words;
      }
      st.words = words; st.lastDt = lastDt;
      const f = readEnd(st.items) + st.extra * READ;
      st.span = st.fixed != null ? st.fixed : Math.max(st.gap, f);
      t = st.t + st.span;
    }
    // the scene ends once everything has been read: from each step on, all that remains, read in order...
    let end = t;
    S.steps.forEach((st, k) => {
      const rest = S.steps.slice(k).reduce((a, s) => a + s.words, 0);
      if (rest) end = Math.max(end, st.t + LEGIBLE + READ * rest);
    });
    // ...and every text at least 2.5 s
    for (const it of S.items) if (it.words) end = Math.max(end, it.at + LEGIBLE + Math.max(MIN_LINE, READ * it.words));
    S.end = end + S.hold;
    S.dur = frames(S.end + (S.final ? 0 : FADE));
    S.start = frames(start);
    start = S.start + S.dur - (S.final ? 0 : XF); // the next scene starts while this one fades out
  });
  const last = SCENES[SCENES.length - 1];
  TOTAL = frames(last.start + last.dur);
}

function activeScenes(t) {
  const out = [];
  SCENES.forEach((S, i) => { if (t >= S.start && (t < S.start + S.dur || i === SCENES.length - 1)) out.push(i); });
  return out.length ? out : [0];
}

function applyItem(it, lt) {
  const p = clamp((lt - it.at) / it.dur), e = ease(p), el = it.el;
  switch (it.anim) {
    case 'up':
      setStyle(el, 'opacity', String(r3(e)));
      setStyle(el, 'transform', `translateY(${r1((1 - e) * 26)}px)`);
      break;
    case 'left':
      setStyle(el, 'opacity', String(r3(e)));
      setStyle(el, 'transform', `translateX(${r1((e - 1) * 26)}px)`);
      break;
    case 'fade':
      setStyle(el, 'opacity', String(r3(e)));
      break;
    case 'static':
      setStyle(el, 'opacity', '1');
      break;
    case 'grow':
    case 'growc':
      setStyle(el, 'opacity', p > 0 ? '1' : '0');
      setStyle(el, 'transform', `scaleX(${r3(e)})`);
      break;
    case 'draw':
      setStyle(el, 'opacity', p > 0 ? '1' : '0');
      setStyle(el, 'stroke-dashoffset', String(r1(el._len * (1 - e))));
      break;
    case 'type': {
      const n = Math.round(clamp((lt - it.at) / it.dur) * it.full.length);
      setStyle(el, 'opacity', lt >= it.at - 0.4 ? String(r3(clamp((lt - it.at + 0.4) / 0.3))) : '0');
      setText(it.tx, it.full.slice(0, n));
      setStyle(it.caret, 'visibility', lt >= it.at - 0.4 && lt < it.at + it.dur + 0.6 ? 'visible' : 'hidden');
      break;
    }
  }
}

function render(t) {
  SIG = [];
  const act = activeScenes(t);
  SCENES.forEach((S, i) => {
    const on = act.includes(i);
    setStyle(S.root, 'display', on ? 'block' : 'none');
    if (!on) return;
    const lt = t - S.start;
    const o = S.final ? 1 : clamp((S.dur - lt) / FADE);
    setStyle(S.root, 'opacity', String(r3(o)));
    for (const it of S.items) applyItem(it, lt);
    for (const fn of S.customs) fn(lt, S);
  });
  renderChrome(t, act);
  return hash(SIG.join('\u0001'));
}

/* ---------- chrome ---------- */
const ORDER = ['problem', 'answer', 'use', 'fork', 'numbers'];
function buildChrome() {
  const bar = h('header', 'bar'), brand = h('div', 'brand');
  brand.append(markSVG(), document.createTextNode(F.chrome.brand));
  const chap = h('div', 'chap');
  bar.append(brand, chap);
  const foot = h('footer', 'foot'), sq = h('span', 'sq');
  const squares = ORDER.map(() => { const i = h('i'); sq.append(i); return i; });
  foot.append(h('span', null, esc(F.chrome.site)), sq);
  stage.append(bar, foot);
  CHROME = { bar, chap, foot, squares };
}
function chromeOpacity(i, t) {
  const S = SCENES[i];
  if (!S.chrome) return 0;
  const lt = t - S.start, prev = SCENES[i - 1], next = SCENES[i + 1];
  let o = 1;
  if (!(prev && prev.chrome)) o = clamp((lt - 0.05) / 0.5);
  if (!(next && next.chrome)) o = Math.min(o, clamp((S.dur - lt) / FADE));
  return o;
}
function renderChrome(t, act) {
  const o = Math.max(0, ...act.map(i => chromeOpacity(i, t)));
  setStyle(CHROME.bar, 'opacity', String(r3(o)));
  setStyle(CHROME.foot, 'opacity', String(r3(o)));
  // the chapter label: the outgoing one fades out with its scene, the next one fades in once the cross-fade is over
  const iIn = act[act.length - 1], S = SCENES[iIn], P = act.length > 1 ? SCENES[act[0]] : null;
  let owner = S, co = 1;
  if (P && P.chrome && (!S.chrome || P.chapter !== S.chapter)) {
    owner = P; co = S.chrome ? clamp((P.dur - (t - P.start)) / FADE) : 1;
  } else if (!P) {
    const prev = SCENES[iIn - 1];
    if (prev && prev.chrome && S.chrome && prev.chapter !== S.chapter) co = clamp((t - S.start - XF) / 0.4);
  }
  if (!owner.chrome) return;
  setText(CHROME.chap, F.chapters[owner.chapter]);
  setStyle(CHROME.chap, 'opacity', String(r3(co)));
  CHROME.squares.forEach((q, k) => setClass(q, ORDER[k] === owner.chapter ? 'on' : ''));
}

/* ---------- figures from quality.json ---------- */
function num(v) {
  if (typeof v === 'number' && isFinite(v)) return v;
  if (typeof v !== 'string') return null;
  const s = v.replace(/[\s%]/g, '').replace(',', '.');
  return /^-?\d+(\.\d+)?$/.test(s) ? Number(s) : null;
}
const qv = key => num(Q[key]);
function fmtDec(x, d = 1) { const s = x.toFixed(d); return LANG === 'fr' ? s.replace('.', ',') : s; }
function fmtInt(x) { // the site's rule (site/src/format.rs): narrow no-break space in French, comma in English
  const s = String(Math.round(x)), sep = LANG === 'fr' ? ' ' : ',';
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
}
function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  if (!m || !F.months) return null;
  const d = Number(m[3]), mon = F.months[Number(m[2]) - 1];
  if (!mon) return null;
  return `${LANG === 'fr' && d === 1 ? '1er' : d} ${mon} ${m[1]}`;
}
// "{q.key}" is a value of quality.json, "{tests}" the smaller of the two test counts, rounded down to the hundred;
// null when a value is missing (the caller then uses the facts file's fallback)
function fillQ(s) {
  if (s == null) return null;
  let ok = true;
  const out = String(s).replace(/\{(q\.([a-z_]+)|tests)\}/g, (m, all, key) => {
    if (all === 'tests') {
      const a = qv('tests_windows'), b = qv('tests_linux');
      if (a == null || b == null) { ok = false; return ''; }
      return fmtInt(Math.floor(Math.min(a, b) / 100) * 100);
    }
    const v = qv(key);
    if (v == null) { ok = false; return ''; }
    // a per-family rate (f_*_nl, _mr, _pr) always with one decimal, as on the site ("92,0"); other values: an integer,
    // or one decimal, or two when quality.json has two (an over-masking rate such as 0.07)
    if (/^f_[a-z]+_(nl|mr|pr)$/.test(key)) return fmtDec(v);
    return Number.isInteger(v) ? fmtInt(v) : fmtDec(v, Math.min(2, Math.max(1, (String(v).split('.')[1] || '').length)));
  });
  return ok ? out : null;
}

/* ---------- the signature move: the brand's brackets close over a name, leave the orange bar, open on its tag ---------- */
function morphEntity(orig, ph, cls) {
  const el = h('span', 'mo'), o = h('span', 'mo-o'), p = h('span', 'ph mo-p ' + cls);
  o.textContent = orig; p.textContent = ph;
  const L = h('i', 'mo-k mo-l'), R = h('i', 'mo-k mo-r'), B = h('i', 'mo-b');
  el.append(o, p, L, R, B);
  const e = { el, orig, ph, t0: 0 };
  e.measure = () => {
    const cs = getComputedStyle(el);
    e.fs = parseFloat(cs.fontSize); e.lh = parseFloat(cs.lineHeight) || e.fs * 1.5;
    e.wo = o.offsetWidth; e.wp = p.offsetWidth;
    // the mark's proportions (24-unit box: brackets 16 high, 3 wide, 10 apart; bar 9 x 4; stroke 2.2)
    e.u = e.fs * 0.86 / 16; e.sw = Math.max(2, 2.2 * e.u); e.bw = 3 * e.u + e.sw;
    const bh = 16 * e.u + e.sw, top = (e.lh - bh) / 2;
    for (const k of [L, R]) Object.assign(k.style, { top: r1(top) + 'px', height: r1(bh) + 'px', width: r1(e.bw) + 'px', borderWidth: r1(e.sw) + 'px' });
    L.style.borderRightWidth = '0px'; R.style.borderLeftWidth = '0px';
    Object.assign(B.style, { top: r1(e.lh / 2 - 2 * e.u) + 'px', height: r1(4 * e.u) + 'px' });
    p.style.top = r1((e.lh - 1.2 * e.fs) / 2) + 'px';
  };
  e.render = d => {
    const u = e.u, gap = 0.12 * e.fs, c0 = e.wo / 2, xLc = c0 - 5 * u, xRc = c0 + 5 * u;
    let width = e.wo, xL = -gap, xR = e.wo + gap, kOp = 0, oOp = 1, clipL = 0, clipR = 0, barW = 0, barOp = 0, pOp = 0, c = c0;
    if (d >= 0) {
      kOp = clamp(d / 0.3);
      const q = easeIO(clamp((d - 0.3) / 0.55));
      xL = -gap + (xLc + gap) * q; xR = e.wo + gap + (xRc - e.wo - gap) * q;
      clipL = Math.max(0, xL); clipR = Math.max(0, e.wo - xR);
      oOp = 1 - clamp((q - 0.45) / 0.4);
      barW = 9 * u * ease(clamp((d - 0.72) / 0.25)); barOp = barW > 0 ? 1 : 0;
      if (d >= 1.05) {
        const r = easeIO(clamp((d - 1.05) / 0.5));
        // the brackets open around the placeholder, then hand over to it; the bar is gone before the placeholder's
        // letters arrive, so it never reads as a strike-through
        width = e.wo + (e.wp - e.wo) * r; c = c0 + (e.wp / 2 - c0) * r;
        xL = xLc + (0 - xLc) * r; xR = xRc + (e.wp - xRc) * r;
        barW = 9 * u * (1 + 0.6 * r); barOp = 1 - clamp((d - 1.05) / 0.18);
        kOp = 1 - clamp((d - 1.32) / 0.22); oOp = 0;
      }
      pOp = clamp((d - 1.3) / 0.3);
    }
    setStyle(el, 'width', r1(width) + 'px');
    setStyle(o, 'opacity', String(r3(oOp)));
    setStyle(o, 'clip-path', `inset(0 ${r1(clipR)}px 0 ${r1(clipL)}px)`);
    setStyle(p, 'opacity', String(r3(pOp)));
    setStyle(L, 'opacity', String(r3(kOp))); setStyle(R, 'opacity', String(r3(kOp)));
    setStyle(L, 'transform', `translateX(${r1(xL - e.bw)}px)`);
    setStyle(R, 'transform', `translateX(${r1(xR)}px)`);
    setStyle(B, 'opacity', String(r3(barOp)));
    setStyle(B, 'width', r1(barW) + 'px');
    setStyle(B, 'transform', `translateX(${r1(c - barW / 2)}px)`);
  };
  MEASURE.push(e);
  return e;
}
function specimenText(lines, ph) {
  return lines.map(segs => segs.map(s => (ph && s[1] != null ? s[1] : s[0])).join('')).join(' ');
}

/* ---------- 1. title: opens on a line of a document, already a full frame ---------- */
function buildTitle() {
  const T = pick('title'), S = new Scene('title', null, { hold: 0.8, lead: 0 });
  const w = h('div', 'ttl'), name = h('div', 'name'), mk = markSVG(), nm = hr('span', null, T.name);
  name.append(mk, nm);
  const spec = h('div', 'spec0'), ents = [];
  for (const segs of T.specimen) {
    const ln = h('div', 'sl');
    for (const [orig, ph, cls] of segs) {
      if (ph == null) { ln.append(document.createTextNode(orig)); continue; }
      const e = morphEntity(orig, ph, cls || 'p1'); ents.push(e); ln.append(e.el);
    }
    spec.append(ln);
  }
  const kick = hr('p', 'kick', T.kicker), rule = h('div', 'rule');
  const l1 = T.line1 ? hr('p', 'l1', T.line1) : null, l2 = T.line2 ? hr('p', 'l2', T.line2) : null;
  const urls = hr('p', 'urls', T.urls), top = h('div', 'top0');
  top.append(name, spec);
  w.append(...[top, kick, rule, l1, l2, urls].filter(Boolean)); S.fr.append(w);
  // frame 0 shows the name and the document line centred; they rise to their place when the rest arrives
  let lift = 0;
  MEASURE.push({ measure: () => { lift = (urls.offsetTop + urls.offsetHeight - top.offsetTop - top.offsetHeight) / 2; } });

  S.step({ fixed: 0.45 });
  S.show(name, { anim: 'static', label: true, text: T.name });
  S.show(spec, { anim: 'static', words: 0, text: specimenText(T.specimen, false), transcript: true });
  const STAG = 0.75, MOVE = 1.6;
  const mo = S.step({ gap: (ents.length - 1) * STAG + MOVE });
  ents.forEach((e, k) => { e.t0 = k * STAG; });
  S.note(specimenText(T.specimen, true), () => mo.t + (ents.length - 1) * STAG + MOVE - 0.2);
  S.custom(lt => ents.forEach(e => e.render(lt - mo.t - e.t0)));
  const ks = S.step(); S.show(kick, { dt: 0.25 });
  S.custom(lt => setStyle(top, 'transform', `translateY(${r1(lift * (1 - easeIO(clamp((lt - ks.t + 0.45) / 0.8))))}px)`));
  if (l1 || l2) {
    S.step(); S.show(rule, { anim: 'grow', dur: 1.0, words: 0 });
    if (l1) S.show(l1, { dt: 0.15 });
    if (l2) S.show(l2, { dt: 0.8 });
    S.show(urls, { anim: 'fade', dt: 1.6, label: true });
  } else {
    S.show(rule, { anim: 'grow', dt: 0.3, dur: 1.0, words: 0 });
    S.show(urls, { anim: 'fade', dt: 1.2, label: true });
  }
  S.posterAt = () => S.end - 0.4;
  return S;
}

/* ---------- 2. the problem ---------- */
const BARS = [[92, 48, 80], [60, 88, 44], [84, 52, 90], [46, 80, 66]];
function packet() {
  const p = h('div', 'pk');
  [0, 1, 0].forEach(pd => p.append(h('i', pd ? 'pd' : '')));
  return p;
}
function along(pts, p) { // point at fraction p of a polyline's length
  const seg = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let L = p * total;
  for (let i = 0; i < seg.length; i++) {
    if (L <= seg[i] || i === seg.length - 1) {
      const f = seg[i] ? clamp(L / seg[i]) : 1;
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f];
    }
    L -= seg[i];
  }
  return pts[pts.length - 1];
}
function place(el, x, y, w, hh) { Object.assign(el.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: hh + 'px' }); }

function buildProblem() {
  const T = pick('problem'), S = new Scene('problem', 'problem');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  // geometry: cards, the AI box, its slots, the wires and the path of each document (centre points)
  const G = SOCIAL ? (() => {
    const card = k => ({ x: (k % 2) * 506, y: 214 + Math.floor(k / 2) * 230, w: 430, h: 200 });
    const ai = { x: 0, y: 724, w: 936, h: 156 }, slot = k => ({ x: 636 + k * 68, y: ai.y + 72 });
    const gx = 468, bus = 690;
    const wires = [`M${gx} ${card(0).y + 100}V${bus}H${slot(3).x + 24}`, `M430 ${card(0).y + 100}H${gx}`, `M506 ${card(1).y + 100}H${gx}`,
      `M430 ${card(2).y + 100}H${gx}`, `M506 ${card(3).y + 100}H${gx}`];
    const drops = [0, 1, 2, 3].map(k => `M${slot(k).x + 24} ${bus}V${ai.y - 2}`);
    const path = k => { const c = card(k), y = c.y + 100, x0 = k % 2 ? 506 : 430; return [[x0, y], [gx, y], [gx, bus], [slot(k).x + 24, bus], [slot(k).x + 24, slot(k).y + 30]]; };
    return { card, ai, slot, wires: [...wires, ...drops], path, arrows: [] };
  })() : (() => {
    const card = k => ({ x: k * 316, y: 190, w: 300, h: 350 });
    const ai = { x: 1350, y: 190, w: 330, h: 350 }, slot = k => ({ x: 1378 + k * 62, y: 452 });
    const bus = 598, cx = k => card(k).x + 150;
    const wires = [`M${cx(0)} 540V${bus}H1515V550`, ...[1, 2, 3].map(k => `M${cx(k)} 540V${bus}`)];
    const path = k => [[cx(k), 548], [cx(k), bus], [slot(k).x + 24, bus], [slot(k).x + 24, slot(k).y + 30]];
    return { card, ai, slot, wires, path, arrows: ['M1506 562 1515 550 1524 562'] };
  })();
  const cards = T.docs.map(([label, data], k) => {
    const c = h('div', 'card'), g = G.card(k);
    place(c, g.x, g.y, g.w, g.h);
    if (!SOCIAL) { const bars = h('div', 'bars'); for (const wd of BARS[k]) { const i = h('i'); i.style.width = wd + '%'; bars.append(i); } c.append(bars); }
    c.append(hr('p', 'dat', data), hr('p', 'lab', label)); S.fr.append(c);
    return c;
  });
  const svg = flowSVG(); S.fr.append(svg);
  const wires = G.wires.map(d => { const p = svgEl('path', { d }); svg.append(p); return p; });
  const heads = G.arrows.map(d => { const p = svgEl('path', { d }); svg.append(p); return p; });
  const ai = h('div', 'aibox'), ga = G.ai; place(ai, ga.x, ga.y, ga.w, ga.h);
  ai.append(hr('p', 'lab', T.ai)); S.fr.append(ai);
  const slots = [0, 1, 2, 3].map(k => { const s = h('div', 'slot'), g = G.slot(k); s.style.left = g.x + 'px'; s.style.top = g.y + 'px'; S.fr.append(s); return s; });
  const pks = [0, 1, 2, 3].map(() => { const p = packet(); S.fr.append(p); return p; });
  const cap = hr('p', 'cap', T.caption); S.fr.append(cap);

  S.headline(hd);
  S.step(); cards.forEach((c, k) => S.show(c, { dt: k * 0.18, label: true, text: plain(T.docs[k][0]) + ' — ' + plain(T.docs[k][1].replace(/@\n/g, '@')) }));
  const flow = S.step({ gap: SOCIAL ? 2.1 : 2.6 });
  wires.forEach((p, k) => S.show(p, { anim: 'draw', dt: k ? 0.15 : 0, dur: k ? 0.35 : 0.7, words: 0 }));
  heads.forEach(p => S.show(p, { anim: 'fade', dt: 0.55, dur: 0.3, words: 0 }));
  S.show(ai, { anim: 'fade', dt: 0.1, label: true, text: T.ai });
  slots.forEach((s, k) => S.show(s, { anim: 'fade', dt: 0.3 + k * 0.05, words: 0 }));
  S.step(); S.show(cap);
  const TRAVEL = 1.5, STAG = 0.32;
  S.custom(lt => {
    pks.forEach((p, k) => {
      const t0 = flow.t + 0.6 + k * STAG, q = clamp((lt - t0) / TRAVEL);
      const [x, y] = along(G.path(k), easeIO(q));
      setStyle(p, 'opacity', String(r3(clamp((lt - t0) / 0.25))));
      setStyle(p, 'transform', `translate(${r1(x - 24)}px,${r1(y - 30)}px)`);
      setStyle(cards[k], 'border-color', lt >= t0 ? 'var(--field)' : 'var(--ink)');
    });
  });
}

function buildShortfalls() {
  const T = F.shortfalls, S = new Scene('shortfalls', 'problem');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const tbl = h('div', 'tbl'); S.fr.append(tbl);
  S.headline(hd);
  T.rows.forEach(([k, v], i) => {
    const r = h('div', 'r');
    const kk = hr('p', 'k', k), vv = hr('p', 'v', v);
    r.append(h('p', 'n', String(i + 1).padStart(2, '0')), kk, vv); tbl.append(r);
    const o = { text: plain(k) + ' — ' + plain(v), words: countWords(plain(k)) * LABEL + countWords(plain(v)) };
    if (i === T.rows.length - 1 && i > 0) S.after(r, o); else { S.step(); S.show(r, o); }
  });
}

/* ---------- 3. our answer ---------- */
function buildDemo() {
  const T = F.demo, S = new Scene('answer-doc', 'answer');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const doc = h('div', 'doc'), lab = hr('p', 'lab', T.label);
  const cur = h('div', 'cur'), lnbg = h('div', 'lnbg');
  doc.append(lab, lnbg, cur);
  const ents = [];
  T.lines.forEach((segs, li) => {
    const ln = h('div', 'ln');
    segs.forEach(([orig, ph, cls]) => {
      if (ph == null) { ln.append(document.createTextNode(orig)); return; }
      const sp = h('span', 'ent'); sp.textContent = orig;
      ents.push({ el: sp, orig, ph, cls: cls || 'p1', line: li });
      ln.append(sp);
    });
    doc.append(ln);
  });
  S.fr.append(doc);
  // the document's key: 32 random bytes that exist only while it is processed, then are destroyed
  const keyl = h('div', 'keyl'), kOn = hr('p', 'on', T.key_on), kOff = hr('p', 'off', T.key_off);
  keyl.append(kOn, kOff); S.fr.append(keyl);
  const keysq = h('div', 'keysq'), bytes = [];
  for (let j = 0; j < 32; j++) { const i = h('i'); keysq.append(i); bytes.push(i); }
  S.fr.append(keysq);
  const cap = hr('p', 'cap', T.caption); S.fr.append(cap);
  const origText = T.lines.map(s => s.map(x => x[0]).join('')).join(' / ');
  const outText = T.lines.map(s => s.map(x => (x[1] ?? x[0])).join('')).join(' / ');

  S.headline(hd);
  // the original is a specimen to look at, not prose to read word by word: it is read during the scan
  const docStep = S.step(); S.show(doc, { anim: 'fade', text: origText, words: 3 });
  S.show(keysq, { anim: 'fade', dt: 0.2, words: 0, transcript: false });
  // the scan: line by line, each name or number is erased and its placeholder typed in its place
  const LINE_T = [], perEnt = 0.4;
  let tt = 0.2;
  T.lines.forEach((segs, li) => {
    const n = ents.filter(e => e.line === li).length;
    LINE_T.push(tt); tt += Math.max(0.7, 0.2 + n * perEnt + 0.25);
  });
  const scanDur = tt + 0.2;
  const scan = S.step({ gap: scanDur });
  S.show(lab, { anim: 'fade', dur: 0.5, words: 0, text: T.label, transcript: true });
  S.show(kOn, { anim: 'fade', dt: 0, dur: 0.4 });
  ents.forEach(e => {
    const idx = ents.filter(x => x.line === e.line).indexOf(e);
    e.t0 = LINE_T[e.line] + 0.15 + idx * perEnt;
  });
  S.note(outText, () => scan.t + scanDur - 0.4);
  const post = S.step(); S.show(kOff, { anim: 'fade', dur: 0.4 }); S.show(cap, { dt: 0.6 });
  const lineH = 42 * 1.8, order = bytes.map((_, j) => (j * 13 + 7) % 32);
  S.custom(lt => {
    const ls = lt - scan.t;
    // current-line marker on the left edge and a faint line background, as in the site's queue
    let li = -1;
    for (let i = 0; i < LINE_T.length; i++) if (ls >= LINE_T[i]) li = i;
    const active = ls >= 0 && ls < scanDur;
    let y = 40;
    if (li >= 0) {
      const from = li > 0 ? 40 + (li - 1) * lineH : 40, to = 40 + li * lineH;
      y = from + (to - from) * easeIO(clamp((ls - LINE_T[li]) / 0.3));
    }
    const vis = active && li >= 0 ? clamp(Math.min((ls - LINE_T[0]) / 0.2, (scanDur - ls) / 0.3)) : 0;
    setStyle(cur, 'top', r1(y) + 'px'); setStyle(cur, 'height', r1(lineH) + 'px'); setStyle(cur, 'opacity', String(r3(vis)));
    setStyle(lnbg, 'top', r1(y) + 'px'); setStyle(lnbg, 'height', r1(lineH) + 'px'); setStyle(lnbg, 'opacity', String(r3(vis)));
    for (const e of ents) {
      const d = ls - e.t0;
      if (d < 0) { setClass(e.el, 'ent'); setText(e.el, e.orig); continue; }
      if (d < 0.12) { setClass(e.el, 'ent hit'); setText(e.el, e.orig); continue; }
      if (d < 0.32) {
        const n = Math.round((1 - (d - 0.12) / 0.2) * e.orig.length);
        setClass(e.el, 'ent hit'); setText(e.el, e.orig.slice(0, n)); continue;
      }
      const n = Math.round(clamp((d - 0.32) / (e.ph.length / 40)) * e.ph.length);
      setClass(e.el, 'ph ' + e.cls); setText(e.el, e.ph.slice(0, Math.max(1, n)));
    }
    // the key: its bytes appear with the document, and vanish once the last tag is in place
    const dk = lt - docStep.t, dOff = lt - post.t + 0.15;
    bytes.forEach((q, j) => {
      const on = clamp((dk - 0.25 - j * 0.02) / 0.15), off = clamp((dOff - order[j] * 0.025) / 0.2);
      setStyle(q, 'background-color', `rgba(14,17,22,${r3(on * (1 - off))})`);
      setStyle(q, 'box-shadow', `inset 0 0 0 1.5px rgba(221,224,229,${r3(1 - 0.6 * off)})`);
    });
    setStyle(kOn, 'opacity', String(r3(lt < post.t ? clamp((lt - scan.t) / 0.4) : 1 - clamp((lt - post.t) / 0.3))));
  });
}

function buildStory() {
  // The headline is the original sentence (the site's "Guillaume embête Nadège" story), the rows what becomes of it.
  const T = pick('story'), S = new Scene('story', 'answer');
  const hd = hr('h2', 'h1 story-h', T.headline); S.fr.append(hd);
  const spec = h('div', 'spec'); S.fr.append(spec);
  S.step(); S.show(hd);
  for (const row of T.rows) {
    const r = h('div', 'r'), k = hr('p', 'k', row.label), body = h('div');
    const tx = hr('p', 't', row.text); body.append(tx);
    r.append(k, body); spec.append(r);
    S.step(); S.show(r, { text: plain(row.label) + ' — ' + plain(row.text), words: countWords(row.label) * LABEL + countWords(plain(row.text)) });
    if (row.why) { const why = hr('p', 'why', row.why); body.append(why); S.show(why, { dt: 0.6 }); }
  }
}

function buildPillars() {
  const T = F.pillars, S = new Scene('pillars', 'answer');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const grid = h('div', 'tiles'); S.fr.append(grid);
  S.headline(hd);
  T.tiles.forEach(([k, v], i) => {
    const tile = h('div', 'tile');
    tile.append(h('p', 'n', String(i + 1).padStart(2, '0')), hr('p', 'k', k), hr('p', 'v', v));
    grid.append(tile);
    const o = { text: plain(k) + ' — ' + plain(v), words: countWords(k) * LABEL + countWords(plain(v)) };
    if (i === T.tiles.length - 1 && i > 0) S.after(tile, o); else { S.step(); S.show(tile, o); }
  });
}

/* ---------- 4. three ways in ---------- */
// A document travels along pts; it is hidden while it crosses the engine (from x0/y0 to x1/y1 along axis), and
// comes out anonymised (orange bar).
function travel(p, pts, q, axis, a0, a1) {
  const [x, y] = along(pts, easeIO(q)), v = axis === 'x' ? x : y, half = axis === 'x' ? 24 : 30;
  const before = clamp((a0 - (v + half)) / 14), afterE = clamp(((v - half) - a1) / 14);
  const op = (v < (a0 + a1) / 2 ? before : afterE) * clamp(q / 0.04) * clamp((1 - q) / 0.08);
  setStyle(p, 'opacity', q > 0 && q < 1 ? String(r3(op)) : '0');
  setStyle(p, 'transform', `translate(${r1(x - 24)}px,${r1(y - 30)}px)`);
  setClass(p, v > (a0 + a1) / 2 ? 'pk anon' : 'pk');
}

function buildUse() {
  if (SOCIAL) return buildUseSocial();
  const T = F.use, S = new Scene('use', 'use');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const TOPS = [110, 314, 518], EH = 188, EW = 540, X0 = 600, X1 = 980, MX = (EW + X0) / 2, YC = 408;
  const svg = flowSVG(); S.fr.append(svg);
  const entries = T.entries.map(([k, v], i) => {
    const b = h('div', 'blk'); place(b, 0, TOPS[i], EW, EH);
    b.append(hr('p', 'k', k), hr('p', 'v', v)); S.fr.append(b);
    return { b, k, v };
  });
  const conns = TOPS.map(tp => { const p = svgEl('path', { d: `M${EW} ${tp + EH / 2}H${MX}V${YC}H${X0}` }); svg.append(p); return p; });
  const eng = h('div', 'blk eng'); place(eng, X0, 228, X1 - X0, 360);
  const ek = h('p', 'k'); ek.append(markSVG(), document.createTextNode(T.engine[0]));
  eng.append(ek, hr('p', 'v', T.engine[1])); S.fr.append(eng);
  const out = svgEl('path', { d: `M${X1} ${YC}H1386` }), outHead = svgEl('path', { d: `M1374 ${YC - 9} 1386 ${YC} 1374 ${YC + 9}` });
  svg.append(out, outHead);
  const olab = hr('p', 'olab', T.output);
  Object.assign(olab.style, { left: X1 + 'px', width: '410px', top: (YC - 74) + 'px' }); S.fr.append(olab);
  const ai = h('div', 'blk ai2'); place(ai, 1390, YC - 120, 290, 240);
  ai.append(hr('p', 'k', T.ai)); S.fr.append(ai);
  const note = hr('p', 'unote', T.note); Object.assign(note.style, { left: '1010px', right: '0px', top: (YC + 150) + 'px' }); S.fr.append(note);
  const local = hr('div', 'local', T.local); S.fr.append(local);
  const pks = entries.map(() => { const p = packet(); S.fr.append(p); return p; });

  S.headline(hd);
  S.step();
  entries.forEach((e, i) => S.show(e.b, { anim: 'left', dt: i * 0.3, text: plain(e.k) + ' — ' + plain(e.v), words: countWords(e.k) * LABEL + countWords(plain(e.v)) }));
  S.step();
  conns.forEach(c => S.show(c, { anim: 'draw', dur: 0.7, words: 0 }));
  S.show(eng, { anim: 'fade', dt: 0.3, text: T.engine.join(' — '), words: countWords(T.engine[0]) * LABEL + countWords(T.engine[1]) });
  // documents start flowing as soon as the way out is drawn, and keep flowing while the rest is read
  const flow = S.step({ gap: 2.2 });
  S.show(out, { anim: 'draw', dur: 0.6, words: 0 }); S.show(outHead, { anim: 'fade', dt: 0.45, dur: 0.3, words: 0 });
  S.show(olab, { anim: 'fade', dt: 0.2, label: true });
  S.show(ai, { anim: 'fade', dt: 0.35, label: true, text: T.ai });
  S.step(); S.show(note);
  S.step(); S.show(local);
  S.custom(lt => {
    pks.forEach((p, k) => {
      const t0 = flow.t + 0.7 + k * 0.85, q = clamp((lt - t0) / 2.6), y0 = TOPS[k] + EH / 2;
      travel(p, [[EW - 24, y0], [MX, y0], [MX, YC], [1362, YC]], q, 'x', X0, X1);
    });
  });
}

function buildUseSocial() {
  const T = pick('use'), S = new Scene('use', 'use');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const EY = 122, EH = 100, EW = 296, BUS = 262, Y0 = 300, Y1 = 552, CX = 468, AIY = 642;
  const svg = flowSVG(); S.fr.append(svg);
  const entries = T.entries.map(([k], i) => {
    const b = h('div', 'blk ent3'); place(b, i * 320, EY, EW, EH);
    b.append(hr('p', 'k', k)); S.fr.append(b);
    return { b, k, cx: i * 320 + EW / 2 };
  });
  const conns = entries.map(e => { const p = svgEl('path', { d: `M${e.cx} ${EY + EH}V${BUS}H${CX}V${Y0}` }); svg.append(p); return p; });
  const eng = h('div', 'blk eng'); place(eng, 118, Y0, 700, Y1 - Y0);
  const ek = h('p', 'k'); ek.append(markSVG(), document.createTextNode(T.engine[0]));
  eng.append(ek, hr('p', 'v', T.engine[1])); S.fr.append(eng);
  const out = svgEl('path', { d: `M${CX} ${Y1}V${AIY - 2}` }), outHead = svgEl('path', { d: `M${CX - 10} ${AIY - 14} ${CX} ${AIY - 2} ${CX + 10} ${AIY - 14}` });
  svg.append(out, outHead);
  const olab = hr('p', 'olab', T.output); Object.assign(olab.style, { left: (CX + 28) + 'px', top: (Y1 + 20) + 'px', textAlign: 'left', whiteSpace: 'nowrap' }); S.fr.append(olab);
  const ai = h('div', 'blk ai2'); place(ai, 218, AIY, 500, 100); ai.append(hr('p', 'k', T.ai)); S.fr.append(ai);
  const note = hr('p', 'unote', T.note); Object.assign(note.style, { left: '0px', right: '0px', top: '790px' }); S.fr.append(note);
  const local = hr('div', 'local', T.local); S.fr.append(local);
  const pks = entries.map(() => { const p = packet(); S.fr.append(p); return p; });

  S.headline(hd);
  S.step(); entries.forEach((e, i) => S.show(e.b, { anim: 'up', dt: i * 0.2, label: true, text: plain(e.k) }));
  S.step(); conns.forEach(c => S.show(c, { anim: 'draw', dur: 0.7, words: 0 }));
  S.show(eng, { anim: 'fade', dt: 0.3, text: T.engine.join(' — '), words: countWords(T.engine[0]) * LABEL + countWords(T.engine[1]) });
  const flow = S.step({ gap: 2.0 });
  S.show(out, { anim: 'draw', dur: 0.5, words: 0 }); S.show(outHead, { anim: 'fade', dt: 0.4, dur: 0.3, words: 0 });
  S.show(olab, { anim: 'fade', dt: 0.2, label: true }); S.show(ai, { anim: 'fade', dt: 0.35, label: true, text: T.ai });
  S.step(); S.show(note);
  S.step(); S.show(local);
  S.custom(lt => {
    pks.forEach((p, k) => {
      const t0 = flow.t + 0.5 + k * 0.7, q = clamp((lt - t0) / 2.2), e = entries[k];
      travel(p, [[e.cx, EY + EH + 30], [e.cx, BUS], [CX, BUS], [CX, AIY - 34]], q, 'y', Y0, Y1);
    });
  });
}

/* ---------- 5. your own version ---------- */
function buildFork() {
  const T = pick('fork'), S = new Scene('fork', 'fork');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const cmd = h('div', 'cmd'), tx = h('span'), caret = h('span', 'caret');
  cmd.append(h('span', 'pr', '$ '), tx, caret); S.fr.append(cmd);
  const note = hr('p', 'fnote', T.note); S.fr.append(note);
  const grid = h('div', SOCIAL ? 'rows' : 'steps'); S.fr.append(grid);
  S.headline(hd);
  const typeDur = Math.max(0.6, T.command.length / 34);
  S.step({ gap: typeDur + 0.25 });
  S.show(cmd, { anim: 'type', full: T.command, tx, caret, text: '$ ' + T.command.replace(/\n/g, ''), words: 3 });
  T.steps.forEach(([k, v, ex], i) => {
    const tile = h('div', SOCIAL ? 'row' : 'tile');
    if (!SOCIAL) tile.append(h('p', 'n', String(i + 1).padStart(2, '0')));
    tile.append(hr('p', 'k', k), hr('p', 'v', v));
    if (ex && !SOCIAL) tile.append(hr('p', 'ex', ex));
    grid.append(tile);
    const text = [k, v, SOCIAL ? null : ex].filter(Boolean).map(plain).join(' — ');
    const o = { text, words: countWords(k) * LABEL + countWords(plain(v)) + (ex && !SOCIAL ? 2 : 0) };
    if (i === 0) { S.step(); S.show(note, { anim: 'fade' }); S.show(tile, { ...o, dt: 0.4 }); }
    else if (i === T.steps.length - 1) S.after(tile, o);
    else { S.step(); S.show(tile, o); }
  });
}

/* ---------- 6. the numbers ---------- */
function figure(f) {
  return { fig: fillQ(f.fig) ?? f.fallback_fig ?? f.fig, label: fillQ(f.label) ?? f.fallback_label ?? f.label };
}
function buildNumbers() {
  const T = pick('numbers'), S = new Scene('numbers', 'numbers');
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const grid = h('div', 'figs'); S.fr.append(grid);
  S.headline(hd);
  T.figures.forEach((f0, i) => {
    const f = figure(f0), d = h('div');
    d.append(hr('p', 'f', f.fig), hr('p', 'l', f.label)); grid.append(d);
    const o = { text: plain(f.fig) + ' — ' + plain(f.label), words: 1 + countWords(plain(f.label)) };
    if (i === T.figures.length - 1 && i > 0) S.after(d, o); else { S.step(); S.show(d, o); }
  });
}

// The confidence index as quality.json has it. The protocol publishes the index only with its interval and the
// mention recall (from quality.json), next to the campaign's precision and over-masking guards (written in the facts
// files, "guards"): the value shows only when the four keys are there. The definition may carry the campaign's date
// ("{date}"; "definition_nodate" without one).
function indexState(T) {
  const ci = qv('confidence_index'), lo = qv('confidence_ci_low'), hi = qv('confidence_ci_high');
  const mr = qv('mention_recall_pct');
  const docs = qv('protocol_docs'), date = fmtDate(Q.protocol_date);
  const measured = [ci, lo, hi, mr].every(v => v != null);
  const defn = String(T.definition ?? '').includes('{date}')
    ? (measured && date ? T.definition.replace('{date}', date) : T.definition_nodate ?? T.definition.replace('{date}', ''))
    : T.definition;
  if (!measured) return { measured, pending: T.pending, proto: T.protocol_pending ?? null, definition: defn };
  let proto = T.protocol_pending ?? null;
  if (docs != null && T.protocol_done) {
    proto = date ? T.protocol_done.replace('{date}', date).replace('{docs}', fmtInt(docs))
      : T.protocol_done_nodate.replace('{docs}', fmtInt(docs));
  }
  return {
    measured, proto, definition: defn,
    value: T.value.replace('{v}', fmtDec(ci)),
    ci: T.ci.replace('{lo}', fmtDec(lo)).replace('{hi}', fmtDec(hi)),
    // the guards line may carry "{q.key}" values (per-family precision, over-masking); without them, "guards_nodata"
    guards: fillQ(T.guards.replace('{mr}', fmtDec(mr))) ?? (T.guards_nodata ?? '').replace('{mr}', fmtDec(mr)),
  };
}
function indexBox(T, I) {
  const box = h('div', I.measured ? 'ci' : 'ci pending');
  const k = hr('p', 'k', T.title);
  const val = I.measured ? hr('p', 'val', I.value) : hr('p', 'val pd', I.pending);
  box.append(k, val);
  const ic = I.measured ? hr('p', 'ic', I.ci) : null, g = I.measured && I.guards ? hr('p', 'g', I.guards) : null;
  if (ic) box.append(ic);
  if (g) box.append(g);
  return { box, k, val, ic, g };
}

function buildIndex() {
  const T = F.index, S = new Scene('index', 'numbers'), I = indexState(T);
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const { box, k, val, ic, g } = indexBox(T, I); S.fr.append(box);
  const d = hr('p', 'd', I.definition);
  box.append(d);
  const p = I.proto ? hr('p', 'p', I.proto) : null;
  if (p) box.append(p);
  const lim = h('div', 'lim'), lk = hr('p', 'k', T.limits_title), ul = h('ul');
  const lis = T.limits.map(x => { const li = hr('li', null, x); ul.append(li); return li; });
  const link = hr('p', 'lk', T.link);
  lim.append(lk, ul, link); S.fr.append(lim);

  S.headline(hd);
  S.step(); S.show(box, { anim: 'fade', words: 0, transcript: false }); S.show(k, { label: true }); S.show(val, { dt: 0.25 });
  if (ic) S.show(ic, { dt: 0.4 });
  if (g) S.show(g, { dt: 0.6 });
  S.step(); S.show(d); if (p) S.show(p, { dt: 0.5 });
  S.step(); S.show(lk, { label: true }); S.show(lis[0], { dt: 0.3 });
  for (let i = 1; i < lis.length; i++) { S.step(); S.show(lis[i]); }
  S.after(link, { anim: 'fade' });
}

// The social cut: two figures, the confidence index (with its definition and date) and the limits, in one scene.
function buildNumbersSocial() {
  const T = pick('numbers'), TI = pick('index'), S = new Scene('numbers', 'numbers'), I = indexState(TI);
  const hd = hr('h2', 'h1', T.headline); S.fr.append(hd);
  const col = h('div', 'stack'), grid = h('div', 'figs'); col.append(grid); S.fr.append(col);
  const rows = T.figures.map(f0 => {
    const f = figure(f0), d = h('div');
    d.append(hr('p', 'f', f.fig), hr('p', 'l', f.label)); grid.append(d);
    return { d, o: { text: plain(f.fig) + ' — ' + plain(f.label), words: 1 + countWords(plain(f.label)) } };
  });
  const { box, k, val, ic, g } = indexBox(TI, I); col.append(box);
  const d = I.definition ? hr('p', 'd', I.definition) : null;
  if (d) box.append(d);
  const p = I.proto ? hr('p', 'p', I.proto) : null;
  if (p) box.append(p);
  const ul = h('ul', 'lims'), lis = T.limits.map(x => { const li = hr('li', null, x); ul.append(li); return li; });
  col.append(ul);
  S.headline(hd);
  rows.forEach(({ d: row, o }) => { S.step(); S.show(row, o); });
  S.step(); S.show(box, { anim: 'fade', words: 0, transcript: false }); S.show(k, { label: true }); S.show(val, { dt: 0.2 });
  if (ic) S.show(ic, { dt: 0.4 });
  if (g) S.show(g, { dt: 0.6 });
  if (d) S.show(d, { dt: 0.8 });
  if (p) S.show(p, { dt: 1.0 });
  lis.forEach(li => { S.step(); S.show(li); });
}

/* ---------- 7. closing ---------- */
function buildClosing() {
  const T = pick('closing'), S = new Scene('closing', null, { final: true, hold: SOCIAL ? 1.0 : 1.5 });
  const w = h('div', 'close'), brand = h('div', 'brand'), mk = markSVG(), bn = hr('span', null, T.brand);
  brand.append(mk, bn);
  const l1 = hr('p', 'l1', T.line1), big = hr('p', 'big', T.big), rule = h('div', 'rule');
  const urls = hr('p', 'urls', T.urls), repo = hr('p', 'repo', T.repo);
  const cred = h('div', 'cred'), cs = T.credits.map(c => { const p = hr('p', null, SOCIAL ? c.replace(/\n/g, ' ') : c); cred.append(p); return p; });
  const lic = hr('p', 'lic', T.licence);
  w.append(brand, l1, big, rule, urls, repo, cred, lic); S.fr.append(w);
  const [a, b] = mk.querySelectorAll('path'), bar = mk.querySelector('rect');
  S.step();
  S.show(a, { anim: 'draw', dur: 0.8, words: 0 }); S.show(b, { anim: 'draw', dur: 0.8, words: 0 });
  S.show(bar, { anim: 'growc', dt: 0.6, dur: 0.5, words: 0 });
  S.show(bn, { anim: 'fade', dt: 0.2, label: true }); S.show(l1, { dt: 0.4 });
  S.step(); S.show(big, { dur: 0.9 });
  S.step(); S.show(rule, { anim: 'grow', dur: 0.9, words: 0 }); S.show(urls, { dt: 0.3 }); S.show(repo, { dt: 0.5, label: true });
  S.step(); cs.forEach((c, i) => S.show(c, { anim: 'fade', dt: i * 0.3, label: true })); S.show(lic, { anim: 'fade', dt: 0.9, label: true });
}

/* ---------- reports for render.py ---------- */
function mmss(t) { const s = Math.floor(t + 1e-6); return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); }
function transcript() {
  const rows = [];
  SCENES.forEach((S, si) => {
    for (const it of S.items) if (it.transcript) rows.push({ t: S.start + it.at, si, text: plain(it.text) });
    for (const n of S.notes) rows.push({ t: S.start + n.atFn(), si, text: plain(n.text) });
  });
  rows.sort((a, b) => a.t - b.t);
  return rows.map(r => ({ time: mmss(r.t), t: Math.round(r.t * 100) / 100, scene: SCENES[r.si].id, text: r.text }));
}
function readability() {
  const scenes = [], problems = [];
  for (const S of SCENES) {
    const end = S.dur - (S.final ? 0 : FADE);
    let words = 0, minSlack = Infinity;
    S.steps.forEach((st, k) => {
      words += st.words;
      const need = READ * S.steps.slice(k).reduce((a, s) => a + s.words, 0);
      if (!need) return;
      const avail = end - (st.t + LEGIBLE);
      minSlack = Math.min(minSlack, avail - need);
      if (avail < need - 1e-6) problems.push(`${S.id} step ${k}: ${avail.toFixed(2)} s on screen for ${need.toFixed(2)} s of reading`);
    });
    for (const it of S.items) {
      if (!it.words) continue;
      const vis = end - (it.at + LEGIBLE), need = Math.max(MIN_LINE, READ * it.words);
      if (vis < need - 1e-6) problems.push(`${S.id}: "${plain(it.text).slice(0, 40)}" on screen ${vis.toFixed(2)} s < ${need.toFixed(2)} s`);
    }
    scenes.push({ id: S.id, chapter: S.chapter, start: S.start, dur: S.dur, words: Math.round(words * 10) / 10, slack: Math.round(minSlack * 100) / 100 });
  }
  return { total: TOTAL, scenes, problems, rule: { read_s_per_word: READ, min_line_s: MIN_LINE, label_weight: LABEL, crossfade_s: XF } };
}

/* ---------- preview (no capture) ---------- */
function preview(t0) {
  const bar = h('div', 'pv'), btn = h('button', null, 'play'), rng = h('input'), lab = h('span');
  rng.type = 'range'; rng.min = 0; rng.max = TOTAL; rng.step = 1 / FPS; rng.value = t0;
  bar.append(btn, rng, lab); document.body.append(bar);
  let t = t0, playing = false, last = 0;
  const show = () => { render(t); rng.value = t; lab.textContent = t.toFixed(2) + ' / ' + TOTAL.toFixed(2) + ' s'; };
  const loop = now => { if (!playing) return; t += (now - last) / 1000; last = now; if (t >= TOTAL) { t = TOTAL; playing = false; } show(); requestAnimationFrame(loop); };
  const toggle = () => { playing = !playing; btn.textContent = playing ? 'pause' : 'play'; if (playing) { if (t >= TOTAL) t = 0; last = performance.now(); requestAnimationFrame(loop); } };
  btn.onclick = toggle;
  rng.oninput = () => { t = Number(rng.value); show(); };
  addEventListener('keydown', e => {
    if (e.key === ' ') { e.preventDefault(); toggle(); }
    if (e.key === 'ArrowRight') { t = Math.min(TOTAL, t + 1); show(); }
    if (e.key === 'ArrowLeft') { t = Math.max(0, t - 1); show(); }
  });
  show();
}

/* ---------- boot ---------- */
async function boot() {
  const get = async u => { const r = await fetch(u, { cache: 'no-store' }); if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); };
  [F, Q] = await Promise.all([get(`facts.${LANG}.json`), get('../site/data/quality.json')]);
  document.documentElement.lang = LANG;
  document.documentElement.classList.toggle('social', SOCIAL);
  document.title = F.html_title;
  if (SOCIAL) {
    buildTitle(); buildProblem(); buildStory(); buildUse(); buildFork(); buildNumbersSocial(); buildClosing();
  } else {
    buildTitle(); buildProblem(); buildShortfalls(); buildDemo(); buildStory(); buildPillars();
    buildUse(); buildFork(); buildNumbers(); buildIndex(); buildClosing();
  }
  buildChrome();
  const FONTS = ['400 40px "GR Sans"', '600 40px "GR Sans"', '400 40px "GR Mono"'];
  await Promise.all(FONTS.map(f => document.fonts.load(f)));
  await document.fonts.ready;
  for (const S of SCENES) for (const it of S.items) if (it.anim === 'draw') {
    it.el._len = it.el.getTotalLength();
    it.el.style.strokeDasharray = it.el._len + ' ' + it.el._len;
  }
  // measure what the signature move needs, with every scene laid out once
  for (const S of SCENES) S.root.style.display = 'block';
  for (const m of MEASURE) m.measure();
  for (const S of SCENES) S.root.style.display = 'none';
  schedule();
  window.TIMELINE = { duration: TOTAL, fps: FPS, lang: LANG, format: SOCIAL ? 'social' : 'wide', width: W, height: H,
    scenes: SCENES.map(S => ({ id: S.id, chapter: S.chapter, start: S.start, dur: S.dur })) };
  window.posterTime = () => SCENES[0].start + SCENES[0].posterAt();
  window.transcript = transcript;
  window.readability = readability;
  window.render = render;
  window.FONTS_OK = FONTS.every(f => document.fonts.check(f));
  const t0 = Number(QS.get('t')) || 0;
  render(t0);
  window.READY = true;
  if (!CAPTURE) preview(t0);
}
boot().catch(e => { window.BOOT_ERROR = String(e && e.stack || e); console.error(e); });
