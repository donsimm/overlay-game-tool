import {el, makeElement, applyLayout} from "/overlays/_layout.js";

const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/welcome.css";
document.head.append(css);

export function render(root, mod) {
  const s = mod.settings;
  const wrap = el("div", "welcome");
  wrap.style.setProperty("--accent", s.accent);

  // Jedes Element: Wrapper (.el, Layout) > .a (Animation) > Inhalt
  const inA = node => { const a = el("div", "a"); a.append(node); return a; };

  const heart = el("img"); heart.src = "/assets/heart.webp"; heart.alt = "";
  makeElement(wrap, "heart", el("div", "glow"), inA(heart));

  makeElement(wrap, "title", inA(el("h1", "", s.title)));

  const sub = el("p", "", s.subtitle);
  const dots = el("span", "dots");
  dots.append(...["", "", ""].map(() => el("i", "", ".")));
  sub.append(dots);
  makeElement(wrap, "subtitle", inA(sub));

  root.replaceChildren(wrap);
  applyLayout(root, mod.layout);
}
