"""Modul-Typen und Verwaltung der angelegten Overlay-Module."""
import re
import secrets

# Ruhige, dezente Textanimationen (Stärke per «intensity» regelbar)
MOTION_ANIMATIONS = [
    {"key": "float", "label": "Schweben"},
    {"key": "breathe", "label": "Atmen"},
    {"key": "sway", "label": "Wiegen"},
]
# Zwei Schreibmaschinen-Effekte (nur Text); «Stärke» regelt hier das Tempo
TEXT_ANIMATIONS = MOTION_ANIMATIONS + [
    {"key": "typewriter", "label": "Schreibmaschine"},
    {"key": "typewriter_erase", "label": "Schreibmaschine mit Löschen"},
]
ITEM_ANIMATIONS = {"text": TEXT_ANIMATIONS, "image": MOTION_ANIMATIONS}
TEXT_STYLES = [{"key": "comic", "label": "Comic (Rand + Schatten)"},
               {"key": "thick", "label": "Comic dick (dicker Rand)"},
               {"key": "plain", "label": "Schlicht (leichter Rand)"},
               {"key": "none", "label": "Ohne"}]
# Layout-Standard für frei hinzugefügte Ebenen (Texte/Bilder)
ITEM_LAYOUT_DEFAULTS = {"x": 0, "y": 0, "scale": 1, "rotate": 0, "anim": False, "visible": True,
                        "z": 0, "intensity": 1, "animation": "float"}
MAX_ITEMS = 50
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
ITEM_ID_RE = re.compile(r"i_[a-z0-9]{6,12}")

MODULE_TYPES = {
    "custom": {
        "label": "Freies Overlay",
        "description": "Leere Fläche: eigene Bilder und Texte frei anordnen",
        "size": (1920, 1080),
        "elements": [],
        "fields": [],
    },
    "welcome": {
        "label": "Willkommen",
        "description": "«Herzlich Willkommen – der Stream geht gleich los», leicht animiert",
        "size": (1920, 1080),
        # Positionen in % der Fläche, ab Mitte (x, y); scale 1 = Standardgrösse; rotate in Grad
        "elements": [
            {"key": "heart", "label": "Herz",
             "animations": [{"key": "beat", "label": "Herzschlag"}],
             "defaults": {"x": 0, "y": -12, "scale": 1, "rotate": -12, "anim": True, "visible": True,
                          "z": 0, "intensity": 1, "animation": "beat"}},
            {"key": "title", "label": "Titel", "animations": TEXT_ANIMATIONS,
             "defaults": {"x": 0, "y": 8, "scale": 1, "rotate": -1.5, "anim": True, "visible": True,
                          "z": 1, "intensity": 1, "animation": "float"}},
            {"key": "subtitle", "label": "Untertitel", "animations": TEXT_ANIMATIONS,
             "defaults": {"x": 0, "y": 18, "scale": 1, "rotate": -1, "anim": True, "visible": True,
                          "z": 2, "intensity": 1, "animation": "float"}},
        ],
        "fields": [
            {"key": "title", "label": "Titel", "kind": "text", "default": "Herzlich Willkommen"},
            {"key": "subtitle", "label": "Untertitel", "kind": "text", "default": "Der Stream geht gleich los"},
            {"key": "accent", "label": "Leuchtfarbe", "kind": "color", "default": "#ff4d6d"},
            {"key": "style", "label": "Textstil", "kind": "select", "default": "comic",
             "options": [{"value": o["key"], "label": o["label"]} for o in TEXT_STYLES]},
        ],
    },
    "chat": {
        "label": "Chat",
        "description": "Chatnachrichten von Twitch (Emotes, GIFs, Cheers, Antworten, Subs, Raids)",
        "size": (600, 900),
        "elements": [
            {"key": "chat", "label": "Chat", "animations": [],
             "defaults": {"x": 0, "y": 0, "scale": 1, "rotate": 0, "anim": True, "visible": True,
                          "z": 0, "intensity": 1, "animation": "none"}},
        ],
        "fields": [
            {"key": "font_size", "label": "Schriftgrösse", "kind": "number", "min": 1.2, "max": 8, "step": 0.1, "default": 2.8},
            {"key": "box_w", "label": "Breite % der Fläche", "kind": "number", "min": 10, "max": 100, "step": 1, "default": 96},
            {"key": "box_h", "label": "Höhe % der Fläche", "kind": "number", "min": 10, "max": 100, "step": 1, "default": 96},
            {"key": "max_messages", "label": "Max. Nachrichten", "kind": "number", "min": 1, "max": 60, "step": 1, "default": 12},
            {"key": "lifetime", "label": "Ausblenden nach (Sek., 0 = nie)", "kind": "number", "min": 0, "max": 3600, "step": 1, "default": 60},
            {"key": "style", "label": "Textstil", "kind": "select", "default": "comic",
             "options": [{"value": o["key"], "label": o["label"]} for o in TEXT_STYLES]},
            {"key": "links", "label": "Links", "kind": "select", "default": "domain",
             "options": [{"value": "hidden", "label": "ausblenden"}, {"value": "domain", "label": "nur Domain zeigen"},
                         {"value": "text", "label": "als Text zeigen"}]},
            {"key": "hide_commands", "label": "Befehle (!…) ausblenden", "kind": "bool", "default": True},
            {"key": "hide_users", "label": "Nutzer ausblenden (Komma)", "kind": "text",
             "default": "nightbot, streamelements, streamlabs, moobot, fossabot, wizebot"},
            {"key": "badges", "label": "Badges zeigen", "kind": "bool", "default": True},
            {"key": "name_colors", "label": "Namensfarben", "kind": "bool", "default": True},
            {"key": "animated_emotes", "label": "Animierte Emotes", "kind": "bool", "default": True},
            {"key": "gifs", "label": "GIFs zeigen", "kind": "bool", "default": True},
            {"key": "gif_height", "label": "GIF-Höhe (Zeilen)", "kind": "number", "min": 1, "max": 12, "step": 0.5, "default": 4},
            {"key": "third_party", "label": "7TV/BTTV/FFZ-Emotes", "kind": "bool", "default": False},
            {"key": "replies", "label": "Antworten zeigen", "kind": "bool", "default": True},
            {"key": "notices", "label": "Subs/Raids/Ankündigungen zeigen", "kind": "bool", "default": True},
        ],
        "tests": [{"key": k, "label": l} for k, l in [
            ("text", "Nachricht"), ("emotes", "Emotes"), ("cheer", "Cheer"), ("reply", "Antwort"), ("gif", "GIF"),
            ("link", "Link"), ("mention", "Erwähnung"), ("highlight", "Hervorgehoben"), ("intro", "Erste Nachricht"),
            ("long", "Lange Nachricht"), ("mixed", "Mehrere"), ("sub", "Sub"), ("resub", "Resub"), ("gift", "Sub-Geschenk"),
            ("raid", "Raid"), ("announcement", "Ankündigung"), ("delete", "Letzte löschen"), ("clear", "Alles löschen")]],
    },
    "last_follow": {"label": "Letzter Follow", "description": "Zeigt die zuletzt folgende Person", "size": (500, 120)},
    "last_sub": {"label": "Letzter Sub", "description": "Zeigt die zuletzt abonnierende Person", "size": (500, 120)},
    "logo_loop": {"label": "Logo-Loop", "description": "Animierte, sich wiederholende Logos", "size": (400, 400)},
    "plant_game": {"label": "Pflanze giessen", "description": "Chat-/Kanalpunkte-Spiel", "size": (400, 600)},
    "cat_game": {"label": "Katze streicheln", "description": "Chat-/Kanalpunkte-Spiel", "size": (600, 600)},
}


def defaults(type_: str) -> dict:
    return {f["key"]: f["default"] for f in MODULE_TYPES[type_].get("fields", [])}


LAYOUT_LIMITS = {"x": (-150, 150), "y": (-150, 150), "scale": (0.1, 6), "rotate": (-180, 180),
                 "intensity": (0, 2), "z": (0, 99)}
BOOL_FIELDS = ("anim", "visible")


def element_specs(type_: str, items: list) -> dict:
    """Alle verschiebbaren Elemente eines Moduls: eigene Elemente + frei hinzugefügte Ebenen."""
    specs = {e["key"]: {"defaults": e["defaults"], "animations": e.get("animations", [])}
             for e in MODULE_TYPES[type_].get("elements", [])}
    for it in items:
        specs[it["id"]] = {"defaults": ITEM_LAYOUT_DEFAULTS, "animations": ITEM_ANIMATIONS[it["kind"]]}
    return specs


def merged_layout(mod: dict) -> dict:
    specs = element_specs(mod["type"], mod.get("items", []))
    out = {k: dict(v["defaults"]) for k, v in specs.items()}
    for key, values in mod.get("layout", {}).items():
        if key in out:
            out[key].update(values)
    return out


def validate_layout(type_: str, layout: dict, items: list) -> dict:
    """Prüft und bereinigt ein vom Editor gesendetes Layout."""
    specs = element_specs(type_, items)
    clean = {}
    for key, values in layout.items():
        if key not in specs:
            raise ValueError(f"Unbekanntes Element: {key}")
        item = dict(specs[key]["defaults"])
        allowed = {a["key"] for a in specs[key]["animations"]}
        for field, value in values.items():
            if field in BOOL_FIELDS:
                if not isinstance(value, bool):
                    raise ValueError(f"{key}.{field} muss wahr/falsch sein")
                item[field] = value
            elif field == "animation":
                if value not in allowed:
                    raise ValueError(f"{key}: unbekannte Animation")
                item[field] = value
            elif field in LAYOUT_LIMITS:
                lo, hi = LAYOUT_LIMITS[field]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
                    raise ValueError(f"{key}.{field} muss zwischen {lo} und {hi} liegen")
                item[field] = int(round(value)) if field == "z" else round(float(value), 3)
            else:
                raise ValueError(f"Unbekannte Eigenschaft: {field}")
        clean[key] = item
    return clean


def _num(value, label: str, lo: float, hi: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ValueError(f"{label} muss zwischen {lo} und {hi} liegen")
    return round(float(value), 2)


def validate_items(items: list, assets: list) -> list:
    """Prüft die frei hinzugefügten Text-/Bild-Ebenen."""
    if len(items) > MAX_ITEMS:
        raise ValueError(f"Maximal {MAX_ITEMS} Ebenen")
    asset_names = {a["id"]: a["name"] for a in assets}
    seen, out = set(), []
    for it in items:
        iid, kind = it.get("id"), it.get("kind")
        if not isinstance(iid, str) or not ITEM_ID_RE.fullmatch(iid) or iid in seen:
            raise ValueError("Ungültige oder doppelte Ebenen-ID")
        seen.add(iid)
        if kind == "text":
            text = it.get("text")
            if not isinstance(text, str) or not 1 <= len(text) <= 200:
                raise ValueError("Text: 1 bis 200 Zeichen")
            color, style = it.get("color", "#ffffff"), it.get("style", "comic")
            if not isinstance(color, str) or not COLOR_RE.fullmatch(color):
                raise ValueError("Text: ungültige Farbe")
            if style not in {s["key"] for s in TEXT_STYLES}:
                raise ValueError("Text: unbekannter Stil")
            out.append({"id": iid, "kind": "text", "name": text.strip()[:24] or "Text", "text": text,
                        "size": _num(it.get("size", 7), "Text-Grösse", 1, 60), "color": color, "style": style})
        elif kind == "image":
            asset = it.get("asset")
            if asset not in asset_names:
                raise ValueError("Bild nicht in der Bibliothek")
            out.append({"id": iid, "kind": "image", "name": asset_names[asset][:40], "asset": asset,
                        "size": _num(it.get("size", 25), "Bild-Grösse", 1, 100)})
        else:
            raise ValueError("Unbekannte Ebenen-Art")
    return out


def validate_setting(field: dict, value):
    """Prüft einen Einstellungswert nach Feldart (text, color, number, bool, select)."""
    kind, label = field["kind"], field["label"]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{label}: wahr/falsch erwartet")
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not field["min"] <= value <= field["max"]:
            raise ValueError(f"{label}: Zahl zwischen {field['min']} und {field['max']}")
        return float(value)
    elif kind == "select":
        if value not in {o["value"] for o in field["options"]}:
            raise ValueError(f"{label}: ungültige Auswahl")
    else:
        if not isinstance(value, str) or len(value) > 200:
            raise ValueError(f"{label}: Text bis 200 Zeichen")
        if kind == "color" and not COLOR_RE.fullmatch(value):
            raise ValueError(f"{label}: ungültige Farbe")
    return value


def new_module(type_: str, name: str) -> dict:
    if type_ not in MODULE_TYPES:
        raise ValueError(f"Unbekannter Modul-Typ: {type_}")
    w, h = MODULE_TYPES[type_]["size"]
    return {
        "id": secrets.token_urlsafe(6),
        "type": type_,
        "name": name.strip() or MODULE_TYPES[type_]["label"],
        "width": w,
        "height": h,
        "enabled": True,
        "settings": defaults(type_),
        "layout": {},
        "items": [],
    }
