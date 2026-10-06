const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/welcome.css";
document.head.append(css);

const SVG = "http://www.w3.org/2000/svg";

export function render(root, mod) {
  const s = mod.settings;
  const el = (tag, cls, text) => Object.assign(document.createElement(tag), {className: cls || "", textContent: text ?? ""});

  const wrap = el("div", "welcome");
  wrap.style.setProperty("--accent", s.accent);

  const heart = document.createElementNS(SVG, "svg");
  heart.setAttribute("viewBox", "0 0 24 24"); heart.setAttribute("class", "heart");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute("d", "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z");
  heart.append(path);

  const sub = el("p", "", s.subtitle);
  const dots = el("span", "dots");
  dots.append(...["", "", ""].map(() => el("i", "", ".")));
  sub.append(dots);

  const stack = el("div", "stack");
  stack.append(el("h1", "", s.title), sub);
  wrap.append(el("div", "glow"), heart, stack);
  root.replaceChildren(wrap);
}
