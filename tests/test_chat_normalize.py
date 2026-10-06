"""Prüft die Auswertung der Twitch-Chatereignisse (ohne Netzwerk). Start: python tests/test_chat_normalize.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import chat  # noqa: E402

CTX = {
    "badges": {("moderator", "1"): {"url": "https://x.example/mod.png", "title": "Moderator"}},
    "cheermotes": {"cheer": [
        {"min_bits": 1, "color": "#979797", "images": {"dark": {"animated": {"2": "https://x.example/c1.gif"}, "static": {"2": "https://x.example/c1.png"}}}},
        {"min_bits": 100, "color": "#9c3ee8", "images": {"dark": {"animated": {"2": "https://x.example/c100.gif"}, "static": {"2": "https://x.example/c100.png"}}}}]},
    "thirdparty": {"OMEGALUL": {"provider": "7tv", "url": "https://cdn.7tv.app/emote/abc/2x.webp", "animated": True}},
}

ev = {"message_id": "m1", "chatter_user_id": "7", "chatter_user_login": "mira", "chatter_user_name": "Mira", "color": "#00ff7f",
      "badges": [{"set_id": "moderator", "id": "1", "info": ""}, {"set_id": "unbekannt", "id": "9", "info": ""}],
      "message_type": "channel_points_highlighted", "cheer": {"bits": 150},
      "reply": {"parent_user_name": "Tom", "parent_message_body": "x" * 300},
      "message": {"text": "hi", "fragments": [
          {"type": "text", "text": "hi OMEGALUL "},
          {"type": "emote", "text": "Kappa", "emote": {"id": "25", "format": ["static", "animated"]}},
          {"type": "emote", "text": "NurStatisch", "emote": {"id": "1", "format": ["static"]}},
          {"type": "cheermote", "text": "Cheer150", "cheermote": {"prefix": "Cheer", "bits": 150, "tier": 100}},
          {"type": "mention", "text": "@Tom", "mention": {"user_id": "1"}},
          {"type": "gif", "text": "[GIF]", "gif": {"id": "g1", "url": "https://media.example/g.gif"}},
          {"type": "gif", "text": "[BÖSE]", "gif": {"id": "g2", "url": "javascript:alert(1)"}},
          {"type": "zukunft", "text": "neuer Teil"}]}}

m = chat.normalize_message(ev, CTX)
assert m["type"] == "chat" and m["kind"] == "channel_points_highlighted" and m["bits"] == 150
assert m["badges"] == [{"url": "https://x.example/mod.png", "title": "Moderator"}], "unbekannte Badges werden übersprungen"
assert len(m["reply"]["text"]) == 100 and m["reply"]["user"] == "Tom"
kinds = [p["t"] for p in m["parts"]]
assert kinds == ["text", "emote", "text", "emote", "emote", "cheer", "mention", "gif", "text", "text"], kinds
assert m["parts"][1]["provider"] == "7tv" and m["parts"][1]["animated"] is True        # Fremd-Emote erkannt
assert m["parts"][3]["url_anim"].endswith("/animated/dark/2.0") and "/static/" in m["parts"][3]["url"]
assert "url_anim" not in m["parts"][4]                                                   # nur statisch verfügbar
assert m["parts"][5]["url_anim"].endswith("c100.gif") and m["parts"][5]["bits"] == 150   # richtige Cheer-Stufe
assert m["parts"][7]["url"] == "https://media.example/g.gif"
assert m["parts"][8] == {"t": "text", "text": "[BÖSE]"}, "GIF mit javascript:-Adresse wird nur als Text gezeigt"
assert m["parts"][9]["text"] == "neuer Teil", "unbekannte Teile bleiben als Text erhalten"

n = chat.normalize_notice({"message_id": "n1", "notice_type": "announcement", "chatter_user_name": "Mod", "system_message": "",
                           "announcement": {"color": "green"}, "message": {"text": "Hallo", "fragments": [{"type": "text", "text": "Hallo"}]}}, CTX)
assert n["type"] == "notice" and n["color"] == "#22c55e" and n["parts"][0]["text"] == "Hallo"
n = chat.normalize_notice({"message_id": "n2", "notice_type": "sub_gift", "chatter_is_anonymous": True, "system_message": "Ein Anonymer hat 1 Sub verschenkt"}, CTX)
assert n["name"] == "Anonym" and n["text"].startswith("Ein Anonymer")

assert chat.split_thirdparty("a OMEGALUL b", CTX["thirdparty"])[1]["name"] == "OMEGALUL"
assert chat.split_thirdparty("OMEGALULX", CTX["thirdparty"]) == [{"t": "text", "text": "OMEGALULX"}], "nur ganze Wörter"

# Anbieter-Antworten (Aufbau nach Wissensstand, nicht live geprüft)
assert chat.parse_7tv({"emotes": [{"id": "1", "name": "A", "data": {"animated": False, "host": {"url": "//cdn.7tv.app/emote/1"}}}]})["A"]["url"] == "https://cdn.7tv.app/emote/1/2x.webp"
assert "B" in chat.parse_bttv({"channelEmotes": [{"id": "5590b223b344e2c42a9e28e3", "code": "B", "imageType": "gif"}], "sharedEmotes": []})
assert chat.parse_ffz({"sets": {"1": {"emoticons": [{"name": "C", "urls": {"1": "//cdn.frankerfacez.com/e/1"}}]}}})["C"]["url"].startswith("https://")
assert chat.parse_7tv({"emotes": [{"name": "X", "data": {"host": {"url": "http://evil.example/e"}}}]}) == {}, "kein http"

for kind in ("text", "emotes", "cheer", "reply", "gif", "link", "mention", "highlight", "intro", "long", "mixed",
             "sub", "resub", "gift", "raid", "announcement", "delete", "clear"):
    assert chat.sample(kind), kind
print("OK: alle Prüfungen bestanden")
