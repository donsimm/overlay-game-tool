"""Modul-Typen und Verwaltung der angelegten Overlay-Module."""
import secrets

# Ruhige, dezente Textanimationen (Stärke per «intensity» regelbar)
TEXT_ANIMATIONS = [
    {"key": "float", "label": "Schweben"},
    {"key": "breathe", "label": "Atmen"},
    {"key": "sway", "label": "Wiegen"},
]

MODULE_TYPES = {
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
        ],
    },
    "chat": {"label": "Chat", "description": "Chatnachrichten von Twitch und YouTube", "size": (500, 800)},
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


def layout_defaults(type_: str) -> dict:
    return {e["key"]: dict(e["defaults"]) for e in MODULE_TYPES[type_].get("elements", [])}


def merged_layout(mod: dict) -> dict:
    out = layout_defaults(mod["type"])
    for key, values in mod.get("layout", {}).items():
        if key in out:
            out[key].update(values)
    return out


def validate_layout(type_: str, layout: dict) -> dict:
    """Prüft und bereinigt ein vom Editor gesendetes Layout."""
    elements = {e["key"]: e for e in MODULE_TYPES[type_].get("elements", [])}
    clean = {}
    for key, values in layout.items():
        if key not in elements:
            raise ValueError(f"Unbekanntes Element: {key}")
        item = dict(elements[key]["defaults"])
        allowed = {a["key"] for a in elements[key].get("animations", [])}
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
    }
