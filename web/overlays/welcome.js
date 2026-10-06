const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/welcome.css";
document.head.append(css);

export function render(root, mod) {
  const s = mod.settings;
  const el = (tag, cls, text) => Object.assign(document.createElement(tag), {className: cls || "", textContent: text ?? ""});

  const wrap = el("div", "welcome");
  wrap.style.setProperty("--accent", s.accent);

  const heart = el("img", "heart");
  heart.src = "/assets/heart.webp"; heart.alt = "";

  const sub = el("p", "", s.subtitle);
  const dots = el("span", "dots");
  dots.append(...["", "", ""].map(() => el("i", "", ".")));
  sub.append(dots);

  const stack = el("div", "stack");
  stack.append(el("h1", "", s.title), sub);
  wrap.append(el("div", "glow"), heart, stack);
  root.replaceChildren(wrap);
}
