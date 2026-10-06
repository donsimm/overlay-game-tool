// Frei hinzugefügte Ebenen (Text/Bild): gelten für ALLE Module, nicht nur für ein bestimmtes Overlay.
import {el, makeElement, setTyping} from "/overlays/_layout.js";

export function renderItems(root, items) {
  root.querySelectorAll(":scope > .el.item").forEach(n => n.remove());
  for (const it of items || []) {
    let content;
    if (it.kind === "text") {
      content = el("div", `txt txt-${it.style}`, it.text);   // textContent: kein HTML aus Texten
      content.style.setProperty("--sz", it.size);
      content.style.setProperty("--c", it.color);
    } else {
      const src = `/media/${it.file}`;
      const video = it.file.endsWith(".webm");
      content = el(video ? "video" : "img", "pic");
      content.style.setProperty("--sz", it.size);
      if (video) Object.assign(content, {src, muted: true, loop: true, autoplay: true, playsInline: true});
      else Object.assign(content, {src, alt: ""});
    }
    const a = el("div", "a"); a.append(content);
    const wrap = makeElement(root, it.id, a);
    wrap.classList.add("item");
    if (it.kind === "text") setTyping(wrap, it.text, content);
  }
}
