import {syncTyping} from "/overlays/_typing.js";

// Gemeinsame Layout-Logik aller Overlays: jedes verschiebbare Element ist ein
// Wrapper <div class="el" data-el="schlüssel"> mit Position/Grösse/Drehung/Animation aus dem Layout.
export const el = (tag, cls, text) => Object.assign(document.createElement(tag), {className: cls || "", textContent: text ?? ""});

export function makeElement(parent, key, ...children) {
  const wrap = el("div", "el");
  wrap.dataset.el = key;
  wrap.append(...children);
  parent.append(wrap);
  return wrap;
}

// Text, der für die Schreibmaschinen-Effekte gebraucht wird (node = Element mit der Schriftart)
export function setTyping(wrap, text, node) { wrap._typing = {text, node}; }

export function applyLayout(root, layout, editing = false) {
  for (const wrap of root.querySelectorAll("[data-el]")) {
    const l = layout[wrap.dataset.el];
    if (!l) continue;
    wrap.style.left = `${50 + l.x}%`;
    wrap.style.top = `${50 + l.y}%`;
    wrap.style.zIndex = l.z;
    wrap.style.setProperty("--s", l.scale);
    wrap.style.setProperty("--r", `${l.rotate}deg`);
    wrap.style.setProperty("--i", l.intensity);   // Stärke der Animation
    wrap.dataset.anim = l.animation;             // Art der Animation (CSS wählt anhand davon)
    wrap.classList.toggle("noanim", !l.anim);
    // Ausgeblendete Ebenen: im Editor blass sichtbar (damit verschiebbar), sonst weg
    wrap.style.display = l.visible || editing ? "" : "none";
    wrap.style.opacity = !l.visible && editing ? 0.25 : "";
    syncTyping(wrap, l);
  }
}
