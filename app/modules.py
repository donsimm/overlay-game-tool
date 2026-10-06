"""Modul-Typen und Verwaltung der angelegten Overlay-Module."""
import secrets

MODULE_TYPES = {
    "welcome": {
        "label": "Willkommen",
        "description": "«Herzlich Willkommen – der Stream geht gleich los», leicht animiert",
        "size": (1920, 1080),
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
    }
