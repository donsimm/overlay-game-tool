"""Twitch-Chat: EventSub-WebSocket, Auswertung aller Nachrichtenarten, Zusatzdaten (Badges, Cheermotes, 7TV/BTTV/FFZ).

Die Verbindung läuft nur, solange mindestens ein Chat-Overlay offen ist (spart Ressourcen).
Nachrichten werden hier in ein einfaches Format übersetzt, das die Overlays direkt darstellen können.
"""
import asyncio
import collections
import json
import os
import re
import time
from urllib.parse import urlparse

import httpx
import websockets

from . import oauth, store

EVENTSUB_URL = os.environ.get("OVERLAY_EVENTSUB_URL", "wss://eventsub.wss.twitch.tv/ws")
HELIX = os.environ.get("OVERLAY_HELIX_URL", "https://api.twitch.tv/helix")
EMOTE_URL = "https://static-cdn.jtvnw.net/emoticons/v2/{id}/{fmt}/dark/2.0"
SUBSCRIPTIONS = ("channel.chat.message", "channel.chat.notification", "channel.chat.message_delete",
                 "channel.chat.clear", "channel.chat.clear_user_messages")
META_TTL = 6 * 3600
GRACE_SECONDS = 30            # nach dem Schliessen des letzten Overlays noch kurz verbunden bleiben
MAX_PARTS, MAX_BADGES, MAX_THIRDPARTY = 80, 6, 6000
ANNOUNCEMENT_COLORS = {"blue": "#3b82f6", "green": "#22c55e", "orange": "#f97316", "purple": "#a855f7"}


class NotConnected(Exception):
    pass


# ---------- Auswertung (reine Funktionen, ohne Netzwerk) ----------

def _https(url) -> str | None:
    """Nur https-Adressen von fremden Quellen zulassen (GIFs/Emotes kommen von aussen)."""
    if isinstance(url, str) and urlparse(url).scheme == "https" and urlparse(url).netloc:
        return url
    if isinstance(url, str) and url.startswith("//"):
        return "https:" + url
    return None


def split_thirdparty(text: str, table: dict) -> list:
    """Teilt Text in Text- und Emote-Teile (7TV/BTTV/FFZ-Emotes sind Wörter im Text)."""
    if not table:
        return [{"t": "text", "text": text}]
    parts, buf = [], []
    for token in re.split(r"(\s+)", text):
        e = table.get(token)
        if e:
            if buf:
                parts.append({"t": "text", "text": "".join(buf)}); buf = []
            parts.append({"t": "emote", "name": token, **e})
        else:
            buf.append(token)
    if buf:
        parts.append({"t": "text", "text": "".join(buf)})
    return parts


def _cheer_part(frag: dict, ctx: dict) -> dict:
    ch = frag.get("cheermote") or {}
    prefix, bits = str(ch.get("prefix", "")), int(ch.get("bits") or 0)
    tiers = ctx["cheermotes"].get(prefix.lower())
    tier = None
    if tiers:
        tier = max((t for t in tiers if t["min_bits"] <= bits), key=lambda t: t["min_bits"], default=tiers[0])
    img = (tier or {}).get("images", {}).get("dark", {})
    anim = _https((img.get("animated") or {}).get("2"))
    static = _https((img.get("static") or {}).get("2"))
    if not (anim or static):
        return {"t": "text", "text": frag.get("text", "")}
    return {"t": "cheer", "prefix": prefix, "bits": bits, "color": (tier or {}).get("color", "#ffffff"),
            "url": static or anim, "url_anim": anim}


def _parts(message: dict, ctx: dict) -> list:
    parts = []
    for frag in (message.get("fragments") or [])[:MAX_PARTS]:
        kind, text = frag.get("type"), frag.get("text", "")
        if kind == "emote" and isinstance(frag.get("emote"), dict) and frag["emote"].get("id"):
            e = frag["emote"]
            part = {"t": "emote", "name": text, "provider": "twitch",
                    "url": EMOTE_URL.format(id=e["id"], fmt="static")}
            if "animated" in (e.get("format") or []):
                part["url_anim"] = EMOTE_URL.format(id=e["id"], fmt="animated")
            parts.append(part)
        elif kind == "cheermote":
            parts.append(_cheer_part(frag, ctx))
        elif kind == "mention":
            parts.append({"t": "mention", "text": text})
        elif kind == "gif" and isinstance(frag.get("gif"), dict) and _https(frag["gif"].get("url")):
            parts.append({"t": "gif", "url": _https(frag["gif"]["url"]), "text": text})
        elif kind == "text" or text:   # unbekannte neue Teile: als Text zeigen
            parts.extend(split_thirdparty(text, ctx["thirdparty"]) if kind == "text" else [{"t": "text", "text": text}])
    return parts


def _badges(raw, ctx: dict) -> list:
    out = []
    for b in raw or []:
        found = ctx["badges"].get((b.get("set_id"), b.get("id")))
        if found:
            out.append(found)
    return out[:MAX_BADGES]


def normalize_message(ev: dict, ctx: dict) -> dict:
    reply = ev.get("reply") or None
    return {
        "type": "chat",
        "id": ev.get("message_id", ""),
        "uid": ev.get("chatter_user_id", ""),
        "login": ev.get("chatter_user_login", ""),
        "name": ev.get("chatter_user_name") or ev.get("chatter_user_login", ""),
        "color": ev.get("color") or "",
        "badges": _badges(ev.get("badges"), ctx),
        "kind": ev.get("message_type", "text"),   # text, channel_points_highlighted, user_intro, power_ups_* …
        "bits": int((ev.get("cheer") or {}).get("bits") or 0),
        "reply": {"user": reply.get("parent_user_name", ""), "text": (reply.get("parent_message_body") or "")[:100]}
                 if reply else None,
        "text": (ev.get("message") or {}).get("text", ""),
        "parts": _parts(ev.get("message") or {}, ctx),
    }


def normalize_notice(ev: dict, ctx: dict) -> dict:
    """Sub, Resub, Geschenke, Raid, Ankündigung usw. Twitch liefert den fertigen Text in system_message."""
    kind = ev.get("notice_type", "")
    name = "Anonym" if ev.get("chatter_is_anonymous") else (ev.get("chatter_user_name") or "")
    color = ""
    if kind == "announcement":
        color = ANNOUNCEMENT_COLORS.get((ev.get("announcement") or {}).get("color", ""), "")
    elif kind == "raid":
        color = "#a855f7"
    return {
        "type": "notice",
        "id": ev.get("message_id", ""),
        "kind": kind,
        "name": name,
        "color": color,
        "text": ev.get("system_message") or "",
        "badges": _badges(ev.get("badges"), ctx),
        "parts": _parts(ev.get("message") or {}, ctx),
    }


def parse_badges(data: dict) -> dict:
    out = {}
    for s in data.get("data", []):
        for v in s.get("versions", []):
            url = _https(v.get("image_url_2x") or v.get("image_url_1x"))
            if url:
                out[(s.get("set_id"), v.get("id"))] = {"url": url, "title": v.get("title", "")}
    return out


def parse_cheermotes(data: dict) -> dict:
    out = {}
    for c in data.get("data", []):
        tiers = [t for t in c.get("tiers", []) if isinstance(t.get("min_bits"), int)]
        if tiers:
            out[str(c.get("prefix", "")).lower()] = tiers
    return out


def parse_7tv(data: dict) -> dict:
    emotes = data.get("emotes") or (data.get("emote_set") or {}).get("emotes") or []
    out = {}
    for e in emotes:
        host = (e.get("data") or {}).get("host") or {}
        base = _https(host.get("url"))
        if e.get("name") and base:
            out[e["name"]] = {"provider": "7tv", "url": f"{base}/2x.webp", "animated": bool((e["data"]).get("animated"))}
    return out


def parse_bttv(data) -> dict:
    items = data if isinstance(data, list) else (data.get("channelEmotes") or []) + (data.get("sharedEmotes") or [])
    return {e["code"]: {"provider": "bttv", "url": f"https://cdn.betterttv.net/emote/{e['id']}/2x.webp",
                        "animated": bool(e.get("animated")) or e.get("imageType") == "gif"}
            for e in items if e.get("code") and re.fullmatch(r"[0-9a-fA-F]{8,}", str(e.get("id", "")))}


def parse_ffz(data: dict) -> dict:
    out = {}
    for s in (data.get("sets") or {}).values():
        for e in s.get("emoticons", []):
            urls, anim = e.get("urls") or {}, e.get("animated") or {}
            url = _https(urls.get("2") or urls.get("1"))
            if e.get("name") and url:
                part = {"provider": "ffz", "url": url, "animated": False}
                if _https(anim.get("2") or anim.get("1")):
                    part["url_anim"] = _https(anim.get("2") or anim.get("1"))
                out[e["name"]] = part
    return out


# ---------- Verbindung ----------

class ChatService:
    def __init__(self, emit, on_status, want_thirdparty):
        self.emit, self.on_status, self.want_thirdparty = emit, on_status, want_thirdparty
        self.state, self.detail = "idle", ""
        self.listeners = 0
        self.ctx = {"badges": {}, "cheermotes": {}, "thirdparty": {}}
        self._meta_at = 0.0
        self._task: asyncio.Task | None = None
        self._stop_handle = None
        self._seen = collections.deque(maxlen=300)
        self._bg: set = set()

    # Overlays melden sich an/ab
    def acquire(self):
        self.listeners += 1
        if self._stop_handle:
            self._stop_handle.cancel(); self._stop_handle = None
        if not self._task or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    def release(self):
        self.listeners = max(0, self.listeners - 1)
        if self.listeners == 0 and not self._stop_handle:
            self._stop_handle = asyncio.get_running_loop().call_later(GRACE_SECONDS, self._stop)

    def _stop(self):
        self._stop_handle = None
        if self.listeners == 0 and self._task:
            self._task.cancel()
            self._task = None
            self._set("idle", "")

    def _set(self, state: str, detail: str = ""):
        if (state, detail) == (self.state, self.detail):
            return
        self.state, self.detail = state, detail
        t = asyncio.get_running_loop().create_task(self.on_status(state, detail))
        self._bg.add(t); t.add_done_callback(self._bg.discard)

    async def _run(self):
        delay = 2
        while True:
            try:
                await self._once()
                delay = 2
            except asyncio.CancelledError:
                raise
            except NotConnected as e:
                self._set("not-connected", str(e))
                await asyncio.sleep(10)
            except Exception as e:  # Netzwerk, abgelehnte Abos usw.: später erneut versuchen
                self._set("error", f"{type(e).__name__}: {e}")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def _once(self):
        conn = store.load()["connections"].get("twitch", {})
        account = conn.get("account") or {}
        if not conn.get("access_token") or not account.get("id"):
            raise NotConnected("Twitch ist nicht verbunden")
        if "user:read:chat" not in (conn.get("scopes") or []):
            raise NotConnected("Berechtigung «user:read:chat» fehlt: Twitch trennen und neu verbinden")
        self._set("connecting", "")
        async with httpx.AsyncClient(timeout=15) as http:
            await self._load_meta(http, account["id"])
            ws = await websockets.connect(EVENTSUB_URL, max_size=1 << 20, ping_interval=None)
            try:
                subscribed, wait = False, 15
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), wait))
                    kind = msg.get("metadata", {}).get("message_type")
                    if kind == "session_welcome":
                        sess = msg["payload"]["session"]
                        wait = (sess.get("keepalive_timeout_seconds") or 10) + 5
                        if not subscribed:
                            await self._subscribe(http, sess["id"], account["id"])
                            subscribed = True
                            self._set("connected", "")
                    elif kind == "notification":
                        mid = msg["metadata"].get("message_id")
                        if mid in self._seen:   # Twitch kann Nachrichten doppelt senden
                            continue
                        self._seen.append(mid)
                        await self._dispatch(msg["payload"])
                    elif kind == "session_reconnect":
                        new = await websockets.connect(msg["payload"]["session"]["reconnect_url"],
                                                       max_size=1 << 20, ping_interval=None)
                        first = json.loads(await asyncio.wait_for(new.recv(), 30))
                        await ws.close()
                        ws = new
                        wait = (first["payload"]["session"].get("keepalive_timeout_seconds") or 10) + 5
                    elif kind == "revocation":
                        raise RuntimeError("Twitch hat ein Abo widerrufen: " + msg["payload"]["subscription"].get("status", ""))
            finally:
                await ws.close()

    async def _helix(self, http, method: str, path: str, **kw):
        token = await oauth.ensure_token("twitch")
        if not token:
            raise NotConnected("Twitch ist nicht verbunden")
        client_id = store.load()["connections"]["twitch"]["client_id"]
        r = await http.request(method, HELIX + path, headers={"Authorization": f"Bearer {token}", "Client-Id": client_id}, **kw)
        return r

    async def _subscribe(self, http, session_id: str, user_id: str):
        errors = []
        for typ in SUBSCRIPTIONS:
            r = await self._helix(http, "POST", "/eventsub/subscriptions", json={
                "type": typ, "version": "1",
                "condition": {"broadcaster_user_id": user_id, "user_id": user_id},
                "transport": {"method": "websocket", "session_id": session_id}})
            if r.status_code not in (200, 202):
                try:
                    detail = r.json().get("message", r.text)
                except ValueError:
                    detail = r.text
                errors.append(f"{typ}: {r.status_code} {detail}")
        if len(errors) == len(SUBSCRIPTIONS) or any(e.startswith(SUBSCRIPTIONS[0]) for e in errors):
            raise RuntimeError("; ".join(errors))   # ohne Chat-Nachrichten ist das Overlay nutzlos

    async def _dispatch(self, payload: dict):
        typ, ev = payload["subscription"]["type"], payload["event"]
        if typ == "channel.chat.message":
            await self.emit(normalize_message(ev, self.ctx))
        elif typ == "channel.chat.notification":
            await self.emit(normalize_notice(ev, self.ctx))
        elif typ == "channel.chat.message_delete":
            await self.emit({"type": "delete", "id": ev.get("message_id", "")})
        elif typ == "channel.chat.clear":
            await self.emit({"type": "clear"})
        elif typ == "channel.chat.clear_user_messages":
            await self.emit({"type": "clear-user", "uid": ev.get("target_user_id", "")})

    async def _load_meta(self, http, user_id: str):
        """Badges, Cheermotes und (falls gewünscht) 7TV/BTTV/FFZ laden; Fehler sind nicht schlimm."""
        if time.time() - self._meta_at < META_TTL and (self.ctx["badges"] or self.ctx["cheermotes"]):
            return
        badges = {}
        for path in ("/chat/badges/global", f"/chat/badges?broadcaster_id={user_id}"):
            try:
                r = await self._helix(http, "GET", path)
                if r.status_code == 200:
                    badges.update(parse_badges(r.json()))
            except (httpx.HTTPError, ValueError):
                pass
        cheer = {}
        try:
            r = await self._helix(http, "GET", f"/bits/cheermotes?broadcaster_id={user_id}")
            if r.status_code == 200:
                cheer = parse_cheermotes(r.json())
        except (httpx.HTTPError, ValueError):
            pass
        third = await self._load_thirdparty(http, user_id) if self.want_thirdparty() else {}
        self.ctx = {"badges": badges, "cheermotes": cheer, "thirdparty": third}
        self._meta_at = time.time()

    async def _load_thirdparty(self, http, user_id: str) -> dict:
        sources = [
            ("https://7tv.io/v3/emote-sets/global", parse_7tv), (f"https://7tv.io/v3/users/twitch/{user_id}", parse_7tv),
            ("https://api.betterttv.net/3/cached/emotes/global", parse_bttv),
            (f"https://api.betterttv.net/3/cached/users/twitch/{user_id}", parse_bttv),
            ("https://api.frankerfacez.com/v1/set/global", parse_ffz), (f"https://api.frankerfacez.com/v1/room/id/{user_id}", parse_ffz),
        ]
        table = {}
        for url, parse in sources:   # später genannte (Kanal) überschreiben frühere (global)
            try:
                r = await http.get(url, follow_redirects=True)
                if r.status_code == 200 and len(r.content) < 8_000_000:
                    table.update(parse(r.json()))
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
                continue
        return dict(list(table.items())[:MAX_THIRDPARTY])


# ---------- Testnachrichten (ohne Twitch, zum Prüfen der Darstellung) ----------

def _emote(name: str, eid: str) -> dict:
    return {"t": "emote", "name": name, "provider": "twitch", "url": EMOTE_URL.format(id=eid, fmt="static")}


_n = 0


def sample(kind: str) -> list:
    """Gibt eine Liste von Overlay-Ereignissen für die Testart zurück."""
    global _n
    _n += 1
    mid = f"test-{_n}"
    base = {"type": "chat", "id": mid, "uid": f"u{_n % 5}", "login": "testuser", "name": "TestUser", "color": "#ff7a59",
            "badges": [], "kind": "text", "bits": 0, "reply": None, "text": ""}
    T = lambda s: {"t": "text", "text": s}   # noqa: E731
    users = [("Mira", "#9acd32"), ("Jonas", "#1e90ff"), ("Luca_91", "#ff69b4"), ("Aylin", "#ffa500"), ("Tom", "#b19cd9")]
    name, color = users[_n % len(users)]
    base.update(name=name, login=name.lower(), color=color)

    def msg(parts, **extra):
        return {**base, "text": "".join(p.get("text", p.get("name", "")) for p in parts), "parts": parts, **extra}

    if kind == "text":
        return [msg([T("Hallo zusammen, schöner Stream heute!")])]
    if kind == "emotes":
        return [msg([T("Das war stark "), _emote("Kappa", "25"), T(" "), _emote("LUL", "425618"), T(" "), _emote("Kreygasm", "41"),
                     T(" gg "), _emote("<3", "9")])]
    if kind == "cheer":
        return [msg([T("Danke für den Stream "), {"t": "cheer", "prefix": "Cheer", "bits": 100, "color": "#9c3ee8",
                                                   "url": EMOTE_URL.format(id="25", fmt="static")}, T(" 100 Bits!")], bits=100)]
    if kind == "reply":
        return [msg([T("@Mira ja, genau das meine ich")], reply={"user": "Mira", "text": "Wann geht das nächste Spiel los?"})]
    if kind == "gif":
        return [msg([T("Meine Reaktion: "), {"t": "gif", "url": "/assets/test.gif", "text": "[GIF]"}])]
    if kind == "link":
        return [msg([T("Schaut mal hier https://example.com/pfad/zu/etwas?x=1 und www.beispiel.ch")])]
    if kind == "mention":
        return [msg([{"t": "mention", "text": "@Streamer"}, T(" du bist der Beste")])]
    if kind == "highlight":
        return [msg([T("Hervorgehoben mit Kanalpunkten!")], kind="channel_points_highlighted")]
    if kind == "intro":
        return [msg([T("Hi, ich bin neu hier und freue mich!")], kind="user_intro")]
    if kind == "long":
        return [msg([T("Das ist eine sehr lange Nachricht, die garantiert umbrochen werden muss, "
                       "damit man sieht, wie das Overlay mit mehreren Zeilen und breiten Wörtern wie "
                       "Donaudampfschifffahrtsgesellschaftskapitän zurechtkommt.")])]
    if kind == "mixed":
        return [m for k in ("text", "emotes", "reply", "gif", "cheer") for m in sample(k)]
    notice = {"type": "notice", "id": mid, "kind": kind, "name": name, "color": "", "badges": [], "parts": []}
    if kind == "sub":
        return [{**notice, "text": f"{name} hat Tier 1 abonniert."}]
    if kind == "resub":
        return [{**notice, "text": f"{name} hat zum 6. Mal abonniert (Tier 1).", "parts": [T("Immer noch dabei!")]}]
    if kind == "gift":
        return [{**notice, "text": f"{name} hat 5 Subs verschenkt!"}]
    if kind == "raid":
        return [{**notice, "kind": "raid", "color": "#a855f7", "text": f"{name} raidet mit 42 Zuschauern!"}]
    if kind == "announcement":
        return [{**notice, "color": "#3b82f6", "text": "Ankündigung", "parts": [T("Heute Abend gibt es ein Special!")]}]
    if kind == "delete":
        return [{"type": "delete", "id": f"test-{_n - 1}"}]
    if kind == "clear":
        return [{"type": "clear"}]
    return []
