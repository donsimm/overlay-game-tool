// Chat-Overlay: stellt Nachrichten von Twitch dar (Text, Emotes, GIFs, Cheers, Antworten, Badges, Subs/Raids).
// Alle Inhalte werden als Text/Bild-Elemente gebaut (nie als HTML). Bilder kommen nur von https oder /assets/.
import {el, makeElement} from "/overlays/_layout.js";

const css = document.createElement("link");
css.rel = "stylesheet"; css.href = "/overlays/chat.css";
document.head.append(css);

const params = new URLSearchParams(location.search);
const EDIT = params.has("edit"), DEBUG = params.has("debug");
const NOTICE_COLORS = {sub: "#9146ff", resub: "#9146ff", sub_gift: "#ff5ca8", community_sub_gift: "#ff5ca8", raid: "#a855f7", announcement: "#3b82f6"};
const history = [];   // letzte Ereignisse, damit ein Neuladen (Einstellungen speichern) den Chat nicht leert
let box = null, s = {}, hidden = new Set();

const okImage = u => typeof u === "string" && /^(https:\/\/|\/assets\/)/.test(u);

// Dunkle Namensfarben aufhellen, damit sie lesbar bleiben
function readable(hex) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return "#ffffff";
  const [r, g, b] = [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16));
  if (0.2126 * r + 0.7152 * g + 0.0722 * b > 140) return hex;
  const mix = c => Math.round(c + (255 - c) * 0.5);
  return `rgb(${mix(r)},${mix(g)},${mix(b)})`;
}

function addText(parent, text) {
  const re = /(?:https?:\/\/|www\.)[^\s]+/gi;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) parent.append(text.slice(last, m.index));
    if (s.links === "text") parent.append(m[0]);
    else if (s.links === "domain") {
      let host = "Link";
      try { host = new URL(/^www\./i.test(m[0]) ? "https://" + m[0] : m[0]).hostname.replace(/^www\./, ""); } catch { /* Link */ }
      parent.append(el("span", "link", `[${host}]`));
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parent.append(text.slice(last));
}

function img(cls, src, alt) {
  const i = el("img", cls);
  Object.assign(i, {src, alt: alt || "", referrerPolicy: "no-referrer"});
  return i;
}

function addParts(parent, parts, fallbackText) {
  if (!parts?.length) { if (fallbackText) addText(parent, fallbackText); return; }
  for (const p of parts) {
    if (p.t === "emote") {
      const third = p.provider && p.provider !== "twitch";
      const animUrl = s.animated_emotes && p.url_anim ? p.url_anim : null;
      // Animierte Fremd-Emotes ohne Standbild: bei ausgeschalteter Animation als Text zeigen
      const needsAnim = third && p.animated && !p.url_anim && !s.animated_emotes;
      if ((third && !s.third_party) || needsAnim || !okImage(animUrl || p.url)) parent.append(p.name);
      else parent.append(img("emote", animUrl || p.url, p.name));
    } else if (p.t === "gif") {
      if (!s.gifs || !okImage(p.url)) parent.append(p.text || "[GIF]");
      else parent.append(img("gif", p.url, "GIF"));
    } else if (p.t === "cheer") {
      const url = s.animated_emotes && p.url_anim ? p.url_anim : p.url;
      if (okImage(url)) parent.append(img("cheer", url, p.prefix));
      const bits = el("span", "bits", String(p.bits));
      bits.style.color = readable(p.color);
      parent.append(bits, " ");
    } else if (p.t === "mention") parent.append(el("span", "mention", p.text));
    else addText(parent, p.text || "");
  }
}

function build(ev) {
  const m = el("div", `msg txt-${s.style}`);
  m.dataset.id = ev.id || ""; m.dataset.uid = ev.uid || "";
  if (ev.type === "notice") {
    m.classList.add("notice");
    m.style.setProperty("--nc", ev.color || NOTICE_COLORS[ev.kind] || "#9146ff");
    if (ev.text) m.append(el("span", "sys", ev.text));
    if (ev.parts?.length) { m.append(" "); addParts(m, ev.parts); }
    return m;
  }
  if (ev.kind === "channel_points_highlighted") m.classList.add("hl");
  if (ev.kind === "user_intro") m.classList.add("intro");
  if (s.replies && ev.reply) m.append(el("span", "reply", `↪ @${ev.reply.user}: ${ev.reply.text}`));
  if (s.badges) for (const b of ev.badges || []) if (okImage(b.url)) m.append(img("badge", b.url, b.title));
  const name = el("span", "name", ev.name || ev.login || "");
  name.style.color = s.name_colors ? readable(ev.color) : "#fff";
  m.append(name, ": ");
  addParts(m, ev.parts, ev.text);
  return m;
}

function remove(m) {
  if (!m.isConnected || m.classList.contains("out")) return;
  m.classList.add("out");
  setTimeout(() => m.remove(), 450);
}

function show(ev, instant) {
  if (!box) return;
  if (ev.type === "chat") {
    const text = (ev.text || "").trim();
    if (s.hide_commands && text.startsWith("!")) return;
    if (hidden.has((ev.login || "").toLowerCase())) return;
  } else if (!s.notices) return;
  const m = build(ev);
  box.append(m);
  if (instant) m.classList.add("in"); else requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add("in")));
  while (box.children.length > s.max_messages) box.firstElementChild.remove();
  if (s.lifetime > 0) setTimeout(() => remove(m), s.lifetime * 1000);
}

const DEMO = [
  {type: "chat", id: "d1", uid: "1", name: "Mira", color: "#9acd32", badges: [], parts: [{t: "text", text: "Hallo zusammen!"}]},
  {type: "chat", id: "d2", uid: "2", name: "Jonas", color: "#1e90ff", badges: [], parts: [{t: "text", text: "Das war stark "},
    {t: "emote", name: "Kappa", provider: "twitch", url: "https://static-cdn.jtvnw.net/emoticons/v2/25/static/dark/2.0"}]},
  {type: "notice", id: "d3", kind: "sub", text: "Luca_91 hat Tier 1 abonniert.", parts: []},
  {type: "chat", id: "d4", uid: "3", name: "Aylin", color: "#ff69b4", badges: [], reply: {user: "Mira", text: "Hallo zusammen!"},
    parts: [{t: "text", text: "@Mira willkommen im Chat, das ist eine etwas längere Nachricht zum Testen."}]},
];

export function render(root, mod) {
  s = mod.settings;
  hidden = new Set(String(s.hide_users || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean));
  box = el("div", `chatbox`);
  box.style.setProperty("--fs", s.font_size); box.style.setProperty("--bw", s.box_w);
  box.style.setProperty("--bh", s.box_h); box.style.setProperty("--gh", s.gif_height);
  const a = el("div", "a"); a.append(box);
  const wrap = el("div", "chat-root");
  wrap.style.cssText = "position:absolute;inset:0";
  makeElement(wrap, "chat", a);
  root.replaceChildren(wrap);
  if (DEBUG) { const st = el("div"); st.id = "chat-status"; st.textContent = "Chat: …"; root.append(st); }
  const events = EDIT && !history.length ? DEMO : history;
  events.forEach(ev => show(ev, true));
}

export function onEvent(msg) {
  if (msg.type === "chat" || msg.type === "notice") {
    history.push(msg); if (history.length > 60) history.shift();
    show(msg, false);
  } else if (msg.type === "delete") {
    const i = history.findIndex(h => h.id === msg.id); if (i >= 0) history.splice(i, 1);
    box?.querySelectorAll(".msg").forEach(m => m.dataset.id === msg.id && remove(m));
  } else if (msg.type === "clear") {
    history.length = 0; box?.querySelectorAll(".msg").forEach(remove);
  } else if (msg.type === "clear-user") {
    for (let i = history.length - 1; i >= 0; i--) if (history[i].uid === msg.uid) history.splice(i, 1);
    box?.querySelectorAll(".msg").forEach(m => m.dataset.uid === msg.uid && remove(m));
  } else if (msg.type === "chat-status") {
    const st = document.getElementById("chat-status");
    if (st) st.textContent = `Chat: ${msg.state}${msg.detail ? " – " + msg.detail : ""}`;
  }
}
