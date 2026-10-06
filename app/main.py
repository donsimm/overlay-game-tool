import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import modules, oauth, store

WEB = Path(__file__).resolve().parent.parent / "web"
PORT = int(os.environ.get("OVERLAY_PORT", "8080"))
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}

app = FastAPI(title="Overlay Game Tool")


@app.middleware("http")
async def local_only(request: Request, call_next):
    """Schutz gegen fremde Webseiten, die lokale Schreib-Endpunkte aufrufen wollen."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).hostname not in {h.strip("[]") for h in LOCAL_HOSTS}:
            return JSONResponse({"detail": "Origin nicht erlaubt"}, status_code=403)
    return await call_next(request)


# ---------- Verbindungen ----------

class Credentials(BaseModel):
    client_id: str
    client_secret: str | None = None


def _provider(key: str) -> str:
    if key not in oauth.PROVIDERS:
        raise HTTPException(404, "Unbekannter Dienst")
    return key


@app.get("/api/connections")
async def connections():
    # Nur lokaler Stand, keine Netzwerkaufrufe (ressourcenschonend)
    return [{**oauth.public_status(key, PORT), "error": None} for key in oauth.PROVIDERS]


@app.post("/api/connections/{key}/check")
async def check_connection(key: str):
    """Prüft die Verbindung bei Bedarf (Token erneuern, Profil abrufen)."""
    _provider(key)
    error = None
    try:
        await oauth.fetch_profile(key)
    except (httpx.HTTPError, RuntimeError) as e:
        error = f"Prüfung fehlgeschlagen: {e}"
    return {**oauth.public_status(key, PORT), "error": error}


@app.put("/api/connections/{key}/credentials")
async def set_credentials(key: str, body: Credentials):
    _provider(key)
    if not body.client_id.strip():
        raise HTTPException(400, "Client-ID fehlt")
    oauth.set_credentials(key, body.client_id, body.client_secret)
    return oauth.public_status(key, PORT)


@app.post("/api/connections/{key}/disconnect")
async def disconnect(key: str):
    await oauth.disconnect(_provider(key))
    return oauth.public_status(key, PORT)


@app.get("/auth/{key}/login")
async def login(key: str):
    try:
        return RedirectResponse(oauth.build_login_url(_provider(key), PORT))
    except ValueError as e:
        return RedirectResponse(f"/?error={e}#connections")


@app.get("/auth/{key}/callback")
async def callback(key: str, state: str = "", code: str = "", error: str = ""):
    _provider(key)
    if error or not code:
        return RedirectResponse(f"/?error={error or 'Abgebrochen'}#connections")
    if not oauth.consume_state(state, key):
        return RedirectResponse("/?error=Ungültiger state-Parameter#connections")
    try:
        await oauth.exchange_code(key, code, PORT)
        await oauth.fetch_profile(key)
    except (httpx.HTTPError, RuntimeError) as e:
        await oauth.disconnect(key)
        return RedirectResponse(f"/?error=Anmeldung fehlgeschlagen: {e}#connections")
    return RedirectResponse(f"/?connected={key}#connections")


# ---------- Module ----------

class ModuleCreate(BaseModel):
    type: str
    name: str = ""


class ModulePatch(BaseModel):
    name: str | None = None
    width: int | None = None
    height: int | None = None
    enabled: bool | None = None


@app.get("/api/module-types")
async def module_types():
    return [{"type": k, "label": v["label"], "description": v["description"]}
            for k, v in modules.MODULE_TYPES.items()]


@app.get("/api/modules")
async def list_modules():
    return store.load()["modules"]


@app.post("/api/modules", status_code=201)
async def create_module(body: ModuleCreate):
    try:
        mod = modules.new_module(body.type, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    data = store.load()
    data["modules"].append(mod)
    store.save(data)
    return mod


@app.patch("/api/modules/{mid}")
async def patch_module(mid: str, body: ModulePatch):
    data = store.load()
    mod = next((m for m in data["modules"] if m["id"] == mid), None)
    if not mod:
        raise HTTPException(404, "Modul nicht gefunden")
    changes = body.model_dump(exclude_none=True)
    for k in ("width", "height"):
        if k in changes and not 16 <= changes[k] <= 8192:
            raise HTTPException(400, f"{k} muss zwischen 16 und 8192 liegen")
    if "name" in changes:
        changes["name"] = changes["name"].strip() or mod["name"]
    mod.update(changes)
    store.save(data)
    return mod


@app.delete("/api/modules/{mid}", status_code=204)
async def delete_module(mid: str):
    data = store.load()
    data["modules"] = [m for m in data["modules"] if m["id"] != mid]
    store.save(data)


# ---------- Overlay (Browserquelle in OBS) ----------

@app.get("/overlay/{mid}", response_class=HTMLResponse)
async def overlay(mid: str):
    if not any(m["id"] == mid for m in store.load()["modules"]):
        raise HTTPException(404, "Modul nicht gefunden")
    return FileResponse(WEB / "overlay.html")


@app.get("/api/overlay/{mid}")
async def overlay_config(mid: str):
    mod = next((m for m in store.load()["modules"] if m["id"] == mid), None)
    if not mod:
        raise HTTPException(404, "Modul nicht gefunden")
    return mod


class Hub:
    """Verteilt Ereignisse (später: Chat, Follows, Kanalpunkte) an offene Overlays."""

    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def broadcast(self, message: dict):
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                self.clients.discard(ws)


hub = Hub()


@app.websocket("/ws/overlay/{mid}")
async def overlay_ws(ws: WebSocket, mid: str):
    origin = ws.headers.get("origin")
    if origin and urlparse(origin).hostname not in {h.strip("[]") for h in LOCAL_HOSTS}:
        await ws.close(code=1008)
        return
    await ws.accept()
    hub.clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(ws)


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
