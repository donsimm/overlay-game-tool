// Bearbeitungsschicht (nur mit ?edit=1 geladen): Elemente ziehen, an der Ecke skalieren.
// Kommuniziert per postMessage mit editor.html (gleicher Ursprung).
import {applyLayout} from "/overlays/_layout.js";

export function start(root, initialLayout) {
  let layout = structuredClone(initialLayout);
  let selected = null;
  const parentWin = window.parent;
  const send = msg => parentWin.postMessage(msg, location.origin);

  const box = Object.assign(document.createElement("div"), {id: "sel"});
  const handle = Object.assign(document.createElement("div"), {id: "handle"});
  box.append(handle);
  document.body.append(box);
  const style = document.createElement("style");
  style.textContent = `
    #sel{position:fixed;display:none;border:2px dashed #7c5cff;pointer-events:none;z-index:9}
    #handle{position:absolute;right:-9px;bottom:-9px;width:16px;height:16px;background:#7c5cff;border:2px solid #fff;border-radius:50%;pointer-events:auto;cursor:nwse-resize}
    .el{cursor:move;touch-action:none;user-select:none}
    .el *{pointer-events:none}`;
  document.head.append(style);

  const wrapOf = key => root.querySelector(`[data-el="${key}"]`);
  function updateBox() {
    const w = selected && wrapOf(selected);
    if (!w) { box.style.display = "none"; return; }
    const r = w.getBoundingClientRect();
    Object.assign(box.style, {display: "block", left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px"});
  }
  function select(key, notify = true) {
    selected = key; updateBox();
    if (notify) send({type: "select", key});
  }
  const changed = () => { applyLayout(root, layout, true); updateBox(); send({type: "layout", layout}); };
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  root.addEventListener("pointerdown", e => {
    const w = e.target.closest("[data-el]");
    if (!w) return select(null);
    const key = w.dataset.el;
    select(key);
    const start = {x: e.clientX, y: e.clientY, lx: layout[key].x, ly: layout[key].y};
    const rect = root.getBoundingClientRect();
    w.setPointerCapture(e.pointerId);
    const move = ev => {
      layout[key].x = clamp(start.lx + (ev.clientX - start.x) / rect.width * 100, -150, 150);
      layout[key].y = clamp(start.ly + (ev.clientY - start.y) / rect.height * 100, -150, 150);
      changed();
    };
    const up = () => { w.removeEventListener("pointermove", move); w.removeEventListener("pointerup", up); };
    w.addEventListener("pointermove", move); w.addEventListener("pointerup", up);
  });

  handle.addEventListener("pointerdown", e => {
    e.stopPropagation();
    const key = selected, w = key && wrapOf(key);
    if (!w) return;
    const r = w.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const d0 = Math.hypot(e.clientX - cx, e.clientY - cy) || 1, s0 = layout[key].scale;
    handle.setPointerCapture(e.pointerId);
    const move = ev => {
      layout[key].scale = clamp(s0 * Math.hypot(ev.clientX - cx, ev.clientY - cy) / d0, 0.1, 6);
      changed();
    };
    const up = () => { handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", up); };
    handle.addEventListener("pointermove", move); handle.addEventListener("pointerup", up);
  });

  addEventListener("message", e => {
    if (e.source !== parentWin || e.origin !== location.origin) return;
    if (e.data?.type === "layout") { layout = e.data.layout; applyLayout(root, layout, true); updateBox(); }
    if (e.data?.type === "select") select(e.data.key, false);
  });
  addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s" || e.key.startsWith("Arrow")) e.preventDefault();
    send({type: "key", key: e.key, ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey});
  });
  // Grösse von Bild/Schrift ändert sich nach dem Laden
  root.addEventListener("load", updateBox, true);
  document.fonts.ready.then(updateBox);
  applyLayout(root, layout, true);
  send({type: "ready"});
}
