"use strict";
const $ = s => document.querySelector(s);
const id = location.pathname.split("/").pop();
const frame = $("#frame"), stage = $("#stage"), host = $("#stage-host");
let mod, type, meta, layout, items, saved, selected = null, ready = false, assets = [], libMode = null;

const json = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.status === 204 ? null : r.json();
};
const clone = o => JSON.parse(JSON.stringify(o));
const snap = () => JSON.stringify({layout, items});
const dirty = () => snap() !== saved;
const toFrame = msg => ready && frame.contentWindow.postMessage(msg, location.origin);
const newId = () => "i_" + [...crypto.getRandomValues(new Uint8Array(6))].map(b => (b % 36).toString(36)).join("");

const builtin = () => type.elements.find(e => e.key === selected);
const itemOf = key => items.find(i => i.id === key);
const labelOf = key => itemOf(key)?.name || type.elements.find(e => e.key === key)?.label || key;
const animsOf = key => { const it = itemOf(key); return it ? meta.item_animations[it.kind] : (builtin()?.animations || []); };

function updateState() {
  const el = $("#state");
  el.textContent = dirty() ? "ungespeicherte Änderungen" : "gespeichert";
  el.className = "dim" + (dirty() ? " unsaved" : "");
}
function push() { toFrame({type: "state", items, layout}); buildList(); syncPanel(); updateState(); }

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

/* ---------- Ebenen ---------- */
const order = () => Object.keys(layout).sort((a, b) => layout[a].z - layout[b].z);  // hinten -> vorne
function setOrder(keys) { keys.forEach((k, i) => layout[k].z = i); }   // z lückenlos neu vergeben

function buildList() {
  const keys = order().reverse();   // oberste Ebene zuerst anzeigen
  $("#layers").replaceChildren(...keys.map((key, row) => {
    const li = document.createElement("li");
    li.draggable = true; li.dataset.key = key;
    li.classList.toggle("active", key === selected);
    const vis = Object.assign(document.createElement("input"), {type: "checkbox", checked: layout[key].visible, title: "Sichtbar"});
    vis.onclick = e => e.stopPropagation();
    vis.onchange = () => { layout[key].visible = vis.checked; push(); };
    const btn = (txt, title, delta) => {
      const b = Object.assign(document.createElement("button"), {textContent: txt, title});
      b.disabled = row + delta < 0 || row + delta >= keys.length;
      b.onclick = e => { e.stopPropagation(); const k = [...keys]; [k[row], k[row + delta]] = [k[row + delta], k[row]]; setOrder(k.reverse()); push(); };
      return b;
    };
    const kind = itemOf(key)?.kind;
    li.append(Object.assign(document.createElement("span"), {className: "grip", textContent: "⠿"}), vis,
      Object.assign(document.createElement("span"), {className: "name", textContent: (kind === "image" ? "▣ " : kind === "text" ? "T " : "") + labelOf(key)}),
      btn("▲", "Nach vorne", -1), btn("▼", "Nach hinten", 1));
    li.onclick = () => choose(key, true);
    li.ondragstart = e => e.dataTransfer.setData("text/plain", key);
    li.ondragover = e => { e.preventDefault(); li.classList.add("over"); };
    li.ondragleave = () => li.classList.remove("over");
    li.ondrop = e => {
      e.preventDefault();
      const from = e.dataTransfer.getData("text/plain");
      if (!layout[from] || from === key) return buildList();
      const k = keys.filter(x => x !== from);
      k.splice(k.indexOf(key), 0, from);   // vor die Ziel-Zeile einfügen
      setOrder(k.reverse()); push();
    };
    return li;
  }));
}
function choose(key, tell) {
  selected = key;
  $("#controls").hidden = !key; $("#hint").hidden = !!key;
  if (tell) toFrame({type: "select", key});
  buildList(); syncPanel();
}

/* ---------- Panel ---------- */
// Wert nur setzen, wenn das Feld nicht gerade getippt wird (sonst springt der Cursor)
const setVal = (el, v) => { if (document.activeElement !== el) el.value = v; };
function syncPanel() {
  const l = selected && layout[selected]; if (!l) { $("#item-ctl").hidden = true; return; }
  const set = (a, v) => { setVal($("#" + a), v); setVal($("#" + a + "n"), v); };
  set("x", +l.x.toFixed(1)); set("y", +l.y.toFixed(1));
  set("scale", Math.round(l.scale * 100)); set("rotate", +l.rotate.toFixed(1));
  $("#anim").checked = l.anim;
  set("intensity", Math.round(l.intensity * 100));
  const kinds = animsOf(selected);
  $("#anim-kind-row").hidden = kinds.length < 2;
  $("#anim-kind").replaceChildren(...kinds.map(k => Object.assign(document.createElement("option"), {value: k.key, textContent: k.label, selected: k.key === l.animation})));
  $("#intensity-label").textContent = l.animation.startsWith("typewriter") ? "Tempo %" : "Stärke %";
  $("#reset-el").hidden = !!itemOf(selected);

  const it = itemOf(selected);
  $("#item-ctl").hidden = !it;
  if (it) {
    $("#text-ctl").hidden = it.kind !== "text";
    $("#it-swap").hidden = it.kind !== "image";
    setVal($("#it-size"), it.size); setVal($("#it-sizen"), it.size);
    if (it.kind === "text") { setVal($("#it-text"), it.text); setVal($("#it-color"), it.color); $("#it-style").value = it.style; }
  }
}
const bind = (name, apply) => ["", "n"].forEach(sfx => $("#" + name + sfx).addEventListener("input", e => {
  const v = parseFloat(e.target.value); if (Number.isNaN(v) || !selected) return;
  apply(layout[selected], v); push();
}));
bind("x", (l, v) => l.x = v); bind("y", (l, v) => l.y = v);
bind("scale", (l, v) => l.scale = Math.min(6, Math.max(0.1, v / 100)));
bind("rotate", (l, v) => l.rotate = v);
bind("intensity", (l, v) => l.intensity = Math.min(2, Math.max(0, v / 100)));
$("#anim-kind").onchange = e => { layout[selected].animation = e.target.value; push(); };
$("#anim").onchange = e => { layout[selected].anim = e.target.checked; push(); };
$("#reset-el").onclick = () => { layout[selected] = clone(builtin().defaults); push(); };
const defaults = () => Object.fromEntries(type.elements.map(e => [e.key, clone(e.defaults)]));
$("#reset-all").onclick = () => {
  if (!confirm("Alle eigenen Elemente auf Standard zurücksetzen? (Hinzugefügte Texte/Bilder bleiben, ihre Position wird zurückgesetzt.)")) return;
  const z = Object.fromEntries(order().map((k, i) => [k, i]));
  layout = {...defaults(), ...Object.fromEntries(items.map(i => [i.id, clone(meta.item_defaults)]))};
  Object.keys(layout).forEach(k => layout[k].z = z[k] ?? 0);
  push();
};
$("#anim-on").onclick = () => { Object.values(layout).forEach(l => l.anim = true); push(); };
$("#anim-off").onclick = () => { Object.values(layout).forEach(l => l.anim = false); push(); };

/* ---------- Eigene Ebenen (Text/Bild) ---------- */
function addItem(item) {
  if (items.length >= meta.max_items) return alert(`Maximal ${meta.max_items} Ebenen.`);
  items.push(item);
  layout[item.id] = {...clone(meta.item_defaults), z: Math.max(-1, ...Object.values(layout).map(l => l.z)) + 1};
  push(); choose(item.id, true);
}
$("#add-text").onclick = () => addItem({id: newId(), kind: "text", name: "Neuer Text", text: "Neuer Text", size: 7, color: "#ffffff", style: "comic"});
$("#add-image").onclick = () => openLib("add");
$("#it-text").oninput = e => { const it = itemOf(selected); if (!e.target.value) return; it.text = e.target.value; it.name = it.text.trim().slice(0, 24) || "Text"; push(); };
$("#it-color").oninput = e => { itemOf(selected).color = e.target.value; push(); };
$("#it-style").replaceChildren();
$("#it-style").onchange = e => { itemOf(selected).style = e.target.value; push(); };
["it-size", "it-sizen"].forEach(i => $("#" + i).addEventListener("input", e => {
  const v = parseFloat(e.target.value); if (Number.isNaN(v)) return;
  itemOf(selected).size = Math.min(+$("#it-size").max, Math.max(1, v)); push();
}));
$("#it-swap").onclick = () => openLib("swap");
$("#it-del").onclick = () => {
  const key = selected;
  items = items.filter(i => i.id !== key); delete layout[key];
  setOrder(order()); selected = null; push(); choose(null, true);
};

/* ---------- Bilder-Bibliothek ---------- */
const lib = $("#lib");
async function loadAssets() { assets = await json("/api/assets"); }
function renderLib() {
  $("#lib-grid").replaceChildren(...assets.map(a => {
    const thumb = a.kind === "video"
      ? Object.assign(document.createElement("video"), {src: `/media/${a.file}`, muted: true, preload: "metadata"})
      : Object.assign(document.createElement("img"), {src: `/media/${a.file}`, alt: "", loading: "lazy"});
    const tile = document.createElement("div"); tile.className = "tile";
    const del = Object.assign(document.createElement("button"), {className: "del danger", textContent: "✕", title: "Aus der Bibliothek löschen"});
    del.onclick = async e => {
      e.stopPropagation();
      if (!confirm(`«${a.name}» löschen?`)) return;
      try { await json(`/api/assets/${a.id}`, {method: "DELETE"}); await loadAssets(); renderLib(); $("#lib-msg").textContent = ""; }
      catch (err) { $("#lib-msg").textContent = err.message; }
    };
    const th = document.createElement("div"); th.className = "thumb"; th.append(thumb);
    tile.append(del, th, Object.assign(document.createElement("div"), {className: "nm", textContent: a.name, title: a.name}));
    tile.onclick = () => pick(a);
    return tile;
  }));
  if (!assets.length) $("#lib-grid").textContent = "Noch keine Bilder. Oben hochladen.";
}
async function openLib(mode) { libMode = mode; $("#lib-msg").textContent = ""; await loadAssets(); renderLib(); lib.showModal(); }
function pick(a) {
  lib.close();
  if (libMode === "swap") { const it = itemOf(selected); it.asset = a.id; it.file = a.file; it.name = a.name; push(); }
  else addItem({id: newId(), kind: "image", name: a.name, asset: a.id, file: a.file, size: 25});
}
$("#lib-close").onclick = () => lib.close();
$("#lib-file").onchange = async e => {
  const msg = $("#lib-msg"); msg.textContent = "";
  for (const f of e.target.files) {
    try {
      msg.textContent = `Lade ${f.name} …`;
      await json(`/api/assets?name=${encodeURIComponent(f.name)}`, {method: "POST", headers: {"Content-Type": "application/octet-stream"}, body: f});
    } catch (err) { msg.textContent = `${f.name}: ${err.message}`; e.target.value = ""; await loadAssets(); renderLib(); return; }
  }
  e.target.value = ""; msg.textContent = "Hochgeladen."; await loadAssets(); renderLib();
};

/* ---------- Speichern ---------- */
async function save() {
  try {
    await json(`/api/modules/${id}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({layout, items})});
    saved = snap(); updateState();
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
  if (m.type === "ready") { ready = true; toFrame({type: "state", items, layout}); if (selected) toFrame({type: "select", key: selected}); }
  if (m.type === "layout") { layout = m.layout; syncPanel(); updateState(); }   // Ziehen/Skalieren in der Vorschau
  if (m.type === "select") choose(m.key, false);
  if (m.type === "key") onKey(m.key, m.ctrl, m.shift, false);  // Tastendruck, während der Fokus in der Vorschau liegt
});

(async () => {
  mod = await json(`/api/overlay/${id}`);
  [type, meta] = [(await json("/api/module-types")).find(t => t.type === mod.type), await json("/api/meta")];
  document.title = `Editor – ${mod.name}`; $("#title").textContent = mod.name;
  $("#it-style").replaceChildren(...meta.text_styles.map(s => Object.assign(document.createElement("option"), {value: s.key, textContent: s.label})));
  layout = clone(mod.layout); items = clone(mod.items); saved = snap();
  buildList(); fit(); updateState(); choose(null, false);
  frame.src = `/overlay/${id}?edit=1`;
})();
