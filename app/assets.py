"""Bilder-Bibliothek: Uploads prüfen und ablegen (data/assets/)."""
import re
import secrets

from . import store

ASSET_DIR = store.DATA_DIR / "assets"
MAX_BYTES = 25 * 1024 * 1024
TYPES = {  # Endung -> (Medientyp, Art)
    "png": ("image/png", "image"), "jpg": ("image/jpeg", "image"), "jpeg": ("image/jpeg", "image"),
    "gif": ("image/gif", "image"), "webp": ("image/webp", "image"), "svg": ("image/svg+xml", "image"),
    "webm": ("video/webm", "video"),
}
FILE_RE = re.compile(r"a_[A-Za-z0-9_-]{8,}\.(?:%s)" % "|".join(TYPES))


def looks_like(ext: str, head: bytes) -> bool:
    """Prüft die ersten Bytes, damit Endung und Inhalt zusammenpassen."""
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "gif":
        return head[:4] == b"GIF8"
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == "webm":
        return head.startswith(b"\x1a\x45\xdf\xa3")
    if ext == "svg":
        return b"<svg" in head.lower() or b"<?xml" in head.lower()
    return False


def add(name: str, ext: str, content: bytes) -> dict:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    asset_id = "a_" + secrets.token_urlsafe(9)
    file = f"{asset_id}.{ext}"
    (ASSET_DIR / file).write_bytes(content)
    record = {"id": asset_id, "file": file, "name": name, "kind": TYPES[ext][1], "size": len(content)}
    data = store.load()
    data["assets"].append(record)
    store.save(data)
    return record


def remove(asset_id: str) -> None:
    data = store.load()
    rec = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if rec:
        (ASSET_DIR / rec["file"]).unlink(missing_ok=True)
        data["assets"] = [a for a in data["assets"] if a["id"] != asset_id]
        store.save(data)
