import {el, makeElement, applyLayout} from "/overlays/_layout.js";

const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/welcome.css";
document.head.append(css);

export function render(root, mod) {
  const s = mod.settings;
  const wrap = el("div", "welcome");
  wrap.style.setProperty("--accent", s.accent);

  // Herz: Leuchten + Bild (Animation: Herzschlag)
  const heart = el("img"); heart.src = "/assets/heart.webp"; heart.alt = "";
  const heartEl = makeElement(wrap, "heart", el("div", "glow"), el("div", "a beat", ""));
  heartEl.querySelector(".beat").append(heart);

  // Titel und Untertitel (Animation: leichtes Schweben)
  const title = el("div", "a float", ""); title.append(el("h1", "", s.title));
  makeElement(wrap, "title", title);
  const sub = el("p", "", s.subtitle);
  const dots = el("span", "dots");
  dots.append(...["", "", ""].map(() => el("i", "", ".")));
  sub.append(dots);
  const subWrap = el("div", "a float late", ""); subWrap.append(sub);
  makeElement(wrap, "subtitle", subWrap);

  root.replaceChildren(wrap);
  applyLayout(root, mod.layout);
}
