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

export function applyLayout(root, layout) {
  for (const wrap of root.querySelectorAll("[data-el]")) {
    const l = layout[wrap.dataset.el];
    if (!l) continue;
    wrap.style.left = `${50 + l.x}%`;
    wrap.style.top = `${50 + l.y}%`;
    wrap.style.setProperty("--s", l.scale);
    wrap.style.setProperty("--r", `${l.rotate}deg`);
    wrap.classList.toggle("noanim", !l.anim);
  }
}
