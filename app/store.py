"""Persistenter Speicher (JSON-Datei). Enthält Zugangsdaten -> nur für den Besitzer lesbar."""
import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("OVERLAY_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
CONFIG_FILE = DATA_DIR / "config.json"

_DEFAULT = {"connections": {}, "modules": []}
_cache: dict | None = None  # Datei wird nur einmal gelesen (weniger I/O)


def load() -> dict:
    """Gibt die gecachte Konfiguration zurück. Änderungen danach mit save(data) sichern."""
    global _cache
    if _cache is None:
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        for key, value in _DEFAULT.items():
            data.setdefault(key, type(value)())
        _cache = data
    return _cache


def save(data: dict) -> None:
    global _cache
    _cache = data
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_FILE)
