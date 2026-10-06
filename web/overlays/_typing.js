// Schreibmaschinen-Effekte. Technik: ein Ausschnitt (clip-path) wird buchstabenweise aufgedeckt,
// ein Cursor folgt der Kante. Kein Timer: die Web Animations API läuft im Browser (ruhig und sparsam).
// Die Buchstabenpositionen werden einmal gemessen (nach dem Laden der Schrift).
const KINDS = {typewriter: {erase: false}, typewriter_erase: {erase: true}};
const PAD = 60;   // px, damit Schatten/Rand nicht abgeschnitten werden

export function syncTyping(wrap, l) {
  const cfg = KINDS[l.animation], t = wrap._typing;
  const active = !!(cfg && t?.text && l.anim && l.intensity > 0);
  const key = active ? `${l.animation}|${l.intensity}|${t.text}` : "";
  if (wrap._typingKey === key) return;
  wrap._typingKey = key;
  stop(wrap);
  if (active) document.fonts.ready.then(() => { if (wrap._typingKey === key) start(wrap, cfg, l.intensity, t); });
}

function stop(wrap) {
  wrap._typingAnims?.forEach(a => a.cancel());
  wrap._typingAnims = null;
  wrap.querySelector(".cursor")?.remove();
}

function measure(node, text) {
  const cs = getComputedStyle(node);
  const m = document.createElement("div");
  Object.assign(m.style, {position: "fixed", left: "-99999px", top: "0", visibility: "hidden", whiteSpace: "pre",
    fontFamily: cs.fontFamily, fontSize: cs.fontSize, fontWeight: cs.fontWeight, fontStyle: cs.fontStyle, letterSpacing: cs.letterSpacing});
  m.textContent = text;
  document.body.append(m);
  const left = m.getBoundingClientRect().left, range = document.createRange(), edges = [0];
  let off = 0;
  for (const ch of text) {
    off += ch.length;
    range.setStart(m.firstChild, 0); range.setEnd(m.firstChild, off);
    edges.push(range.getBoundingClientRect().right - left);
  }
  m.remove();
  return {edges, fontSize: cs.fontSize};
}

function start(wrap, cfg, intensity, t) {
  const a = wrap.querySelector(".a");
  if (!a) return;
  const {edges, fontSize} = measure(t.node, t.text);
  const n = edges.length - 1, total = edges[n] || 1, A = a.offsetWidth || total, f = A / total;
  const x = i => edges[i] * f;
  const clip = i => i === 0 ? "inset(50% 50% 50% 50%)"
    : i === n ? `inset(-${PAD}px -${PAD}px -${PAD}px -${PAD}px)` : `inset(-${PAD}px ${A - x(i)}px -${PAD}px -${PAD}px)`;

  // Zeitplan (ms): kurze Pause, tippen, Pause mit Cursor, dann löschen/zurücksetzen, Pause
  const speed = Math.max(0.05, intensity);
  const tp = 500, v = 90 / speed, hold = 3200, ve = 45 / speed, rest = 900;
  const steps = [{t: 0, i: 0}];
  for (let i = 1; i <= n; i++) steps.push({t: tp + (i - 1) * v, i});
  let tEnd = tp + (n - 1) * v + hold;
  if (cfg.erase) { for (let i = n - 1; i >= 0; i--) { steps.push({t: tEnd, i}); tEnd += ve; } }
  else { steps.push({t: tEnd, i: 0}); }
  const T = tEnd + rest;
  steps.push({t: T, i: 0});
  const off = s => Math.min(1, s.t / T);

  const timing = {duration: T, iterations: Infinity, easing: "linear"};  // Stufen stehen pro Keyframe
  const clipAnim = a.animate(steps.map(s => ({offset: off(s), clipPath: clip(s.i), easing: "step-end"})), timing);

  const cur = document.createElement("span");
  cur.className = "cursor"; cur.style.fontSize = fontSize;
  cur.append(document.createElement("i"));
  a.append(cur);
  const curAnim = cur.animate(steps.map(s => ({offset: off(s), transform: `translateX(${x(s.i)}px)`, easing: "step-end"})), timing);
  wrap._typingAnims = [clipAnim, curAnim];
}
