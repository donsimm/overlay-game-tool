import {el, makeElement, setTyping, applyLayout} from "/overlays/_layout.js";

const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/welcome.css";
document.head.append(css);

export function render(root, mod) {
  const s = mod.settings;
  const look = s.style === "comic" ? "wl-comic" : `txt-${s.style}`;   // Comic = eigener Look dieses Overlays
  const wrap = el("div", "welcome");
  wrap.style.setProperty("--accent", s.accent);

  // Jedes Element: Wrapper (.el, Layout) > .a (Animation) > Inhalt
  const inA = node => { const a = el("div", "a"); a.append(node); return a; };

  const heart = el("img"); heart.src = "/assets/heart.webp"; heart.alt = "";
  makeElement(wrap, "heart", el("div", "glow"), inA(heart));

  const h1 = el("h1", look, s.title);
  setTyping(makeElement(wrap, "title", inA(h1)), s.title, h1);

  const sub = el("p", look, s.subtitle);
  const dots = el("span", "dots");
  dots.append(...["", "", ""].map(() => el("i", "", ".")));
  sub.append(dots);
  setTyping(makeElement(wrap, "subtitle", inA(sub)), s.subtitle + "...", sub);

  root.replaceChildren(wrap);
  applyLayout(root, mod.layout);
}
