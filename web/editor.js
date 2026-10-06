"use strict";
const $ = s => document.querySelector(s);
const id = location.pathname.split("/").pop();
const frame = $("#frame"), stage = $("#stage"), host = $("#stage-host");
let mod, type, layout, saved, selected = null, ready = false;

const json = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
};
const clone = o => JSON.parse(JSON.stringify(o));
const dirty = () => JSON.stringify(layout) !== JSON.stringify(saved);
const toFrame = msg => ready && frame.contentWindow.postMessage(msg, location.origin);

function updateState() {
  const el = $("#state");
  el.textContent = dirty() ? "ungespeicherte Änderungen" : "gespeichert";
  el.className = "dim" + (dirty() ? " unsaved" : "");
}
function push() { toFrame({type: "layout", layout}); syncPanel(); updateState(); }

/* ---------- Bühne ---------- */
function fit() {
  const k = Math.min(host.clientWidth / mod.width, host.clientHeight / mod.height);
  stage.style.width = mod.width * k + "px"; stage.style.height = mod.height * k + "px";
  frame.style.width = mod.width + "px"; frame.style.height = mod.height + "px";
  frame.style.transform = `scale(${k})`;
}
new ResizeObserver(() => mod && fit()).observe(host);
function setBg(bg) {  // "checker" = Schachbrett aus dem Stylesheet
  stage.style.backgroundImage = bg === "checker" ? "" : "none";
  stage.style.backgroundColor = bg === "checker" ? "" : bg;
}
document.querySelectorAll("[data-bg]").forEach(b => b.onclick = () => setBg(b.dataset.bg));
$("#bgcolor").oninput = e => setBg(e.target.value);

/* ---------- Panel ---------- */
function buildList() {
  $("#els").replaceChildren(...type.elements.map(e => {
    const b = Object.assign(document.createElement("button"), {textContent: e.label});
    b.dataset.key = e.key; b.onclick = () => choose(e.key, true);
    return b;
  }));
}
function choose(key, tell) {
  selected = key;
  document.querySelectorAll("#els button").forEach(b => b.classList.toggle("active", b.dataset.key === key));
  $("#controls").hidden = !key; $("#hint").hidden = !!key;
  if (tell) toFrame({type: "select", key});
  syncPanel();
}
function syncPanel() {
  const l = selected && layout[selected]; if (!l) return;
  const set = (a, v) => { $("#" + a).value = v; $("#" + a + "n").value = v; };
  set("x", +l.x.toFixed(1)); set("y", +l.y.toFixed(1));
  set("scale", Math.round(l.scale * 100)); set("rotate", +l.rotate.toFixed(1));
  $("#anim").checked = l.anim;
}
const bind = (name, apply) => ["", "n"].forEach(sfx => $("#" + name + sfx).addEventListener("input", e => {
  const v = parseFloat(e.target.value); if (Number.isNaN(v) || !selected) return;
  apply(layout[selected], v); push();
}));
bind("x", (l, v) => l.x = v); bind("y", (l, v) => l.y = v);
bind("scale", (l, v) => l.scale = Math.min(6, Math.max(0.1, v / 100)));
bind("rotate", (l, v) => l.rotate = v);
$("#anim").onchange = e => { layout[selected].anim = e.target.checked; push(); };
$("#reset-el").onclick = () => { layout[selected] = clone(type.elements.find(e => e.key === selected).defaults); push(); };
$("#reset-all").onclick = () => { if (confirm("Alle Elemente auf Standard zurücksetzen?")) { layout = defaults(); push(); } };
$("#anim-on").onclick = () => { Object.values(layout).forEach(l => l.anim = true); push(); };
$("#anim-off").onclick = () => { Object.values(layout).forEach(l => l.anim = false); push(); };
const defaults = () => Object.fromEntries(type.elements.map(e => [e.key, clone(e.defaults)]));

/* ---------- Speichern ---------- */
async function save() {
  try {
    await json(`/api/modules/${id}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({layout})});
    saved = clone(layout); updateState();
  } catch (e) { $("#state").textContent = "Fehler: " + e.message; $("#state").className = "dim unsaved"; }
}
$("#save").onclick = save;
function onKey(key, ctrl, shift, inField) {
  if (ctrl && key === "s") { save(); return true; }
  const step = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[key];
  if (!step || !selected || inField) return false;
  const d = shift ? 1 : 0.1;
  layout[selected].x += step[0] * d; layout[selected].y += step[1] * d; push();
  return true;
}
addEventListener("keydown", e => {
  if (onKey(e.key, e.ctrlKey || e.metaKey, e.shiftKey, e.target.matches("input,select,textarea"))) e.preventDefault();
});
addEventListener("beforeunload", e => { if (dirty()) e.preventDefault(); });

/* ---------- Nachrichten aus der Vorschau ---------- */
addEventListener("message", e => {
  if (e.source !== frame.contentWindow || e.origin !== location.origin) return;
  const m = e.data;
  if (m.type === "ready") { ready = true; toFrame({type: "layout", layout}); if (selected) toFrame({type: "select", key: selected}); }
  if (m.type === "layout") { layout = m.layout; syncPanel(); updateState(); }
  if (m.type === "select") choose(m.key, false);
  if (m.type === "key") onKey(m.key, m.ctrl, m.shift, false);  // Tastendruck, während der Fokus in der Vorschau liegt
});

(async () => {
  mod = await json(`/api/overlay/${id}`);
  type = (await json("/api/module-types")).find(t => t.type === mod.type);
  if (!type?.elements?.length) { $("#hint").textContent = "Dieses Overlay hat noch keine verschiebbaren Elemente."; return; }
  document.title = `Editor – ${mod.name}`; $("#title").textContent = mod.name;
  layout = clone(mod.layout); saved = clone(layout);
  buildList(); fit(); updateState();
  frame.src = `/overlay/${id}?edit=1`;
})();
