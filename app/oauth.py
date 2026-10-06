"""OAuth2 (Authorization Code Flow) für Twitch und YouTube/Google."""
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from . import store


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    authorize_url: str
    token_url: str
    revoke_url: str
    scopes: tuple
    extra_auth_params: dict
    console_url: str


PROVIDERS = {
    "twitch": Provider(
        key="twitch",
        label="Twitch",
        authorize_url="https://id.twitch.tv/oauth2/authorize",
        token_url="https://id.twitch.tv/oauth2/token",
        revoke_url="https://id.twitch.tv/oauth2/revoke",
        scopes=(
            "user:read:chat",
            "moderator:read:followers",
            "channel:read:subscriptions",
            "channel:read:redemptions",
            "bits:read",
        ),
        extra_auth_params={"force_verify": "true"},
        console_url="https://dev.twitch.tv/console/apps",
    ),
    "youtube": Provider(
        key="youtube",
        label="YouTube",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        revoke_url="https://oauth2.googleapis.com/revoke",
        scopes=("https://www.googleapis.com/auth/youtube.readonly",),
        extra_auth_params={"access_type": "offline", "prompt": "consent"},
        console_url="https://console.cloud.google.com/apis/credentials",
    ),
}

# state -> (provider, Ablaufzeit); nur im Speicher, einmal verwendbar
_pending: dict[str, tuple[str, float]] = {}


def redirect_uri(provider: str, port: int) -> str:
    return f"http://localhost:{port}/auth/{provider}/callback"


def _conn(provider: str) -> dict:
    return store.load()["connections"].setdefault(provider, {})


def _update(provider: str, **fields) -> None:
    data = store.load()
    data["connections"].setdefault(provider, {}).update(fields)
    store.save(data)


def set_credentials(provider: str, client_id: str, client_secret: str | None) -> None:
    fields = {"client_id": client_id.strip()}
    if client_secret:  # leer = bestehendes Secret behalten
        fields["client_secret"] = client_secret.strip()
    _update(provider, **fields)


def build_login_url(provider: str, port: int) -> str:
    p, c = PROVIDERS[provider], _conn(provider)
    if not c.get("client_id") or not c.get("client_secret"):
        raise ValueError("Client-ID und Client-Secret fehlen")
    now = time.time()
    for s in [s for s, (_, exp) in _pending.items() if exp < now]:
        del _pending[s]
    state = secrets.token_urlsafe(24)
    _pending[state] = (provider, now + 600)
    params = {
        "client_id": c["client_id"],
        "redirect_uri": redirect_uri(provider, port),
        "response_type": "code",
        "scope": " ".join(p.scopes),
        "state": state,
        **p.extra_auth_params,
    }
    return f"{p.authorize_url}?{urlencode(params)}"


def consume_state(state: str, provider: str) -> bool:
    entry = _pending.pop(state, None)
    return bool(entry and entry[0] == provider and entry[1] >= time.time())


def _store_tokens(provider: str, tok: dict) -> None:
    fields = {
        "access_token": tok["access_token"],
        "expires_at": time.time() + int(tok.get("expires_in", 3600)),
        "scopes": tok.get("scope") if isinstance(tok.get("scope"), list) else str(tok.get("scope", "")).split(),
    }
    if tok.get("refresh_token"):  # Google liefert beim Refresh keinen neuen
        fields["refresh_token"] = tok["refresh_token"]
    _update(provider, **fields)


async def exchange_code(provider: str, code: str, port: int) -> None:
    p, c = PROVIDERS[provider], _conn(provider)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(p.token_url, data={
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri(provider, port),
        })
    r.raise_for_status()
    _store_tokens(provider, r.json())


async def ensure_token(provider: str) -> str | None:
    """Gibt ein gültiges Access-Token zurück (erneuert es bei Bedarf)."""
    p, c = PROVIDERS[provider], _conn(provider)
    if not c.get("access_token"):
        return None
    if c.get("expires_at", 0) > time.time() + 60:
        return c["access_token"]
    if not c.get("refresh_token"):
        return None
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(p.token_url, data={
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": c["refresh_token"],
        })
    r.raise_for_status()
    _store_tokens(provider, r.json())
    return _conn(provider)["access_token"]


async def fetch_profile(provider: str) -> dict:
    token = await ensure_token(provider)
    if not token:
        raise RuntimeError("Nicht verbunden")
    c = _conn(provider)
    async with httpx.AsyncClient(timeout=15) as http:
        if provider == "twitch":
            r = await http.get("https://api.twitch.tv/helix/users",
                               headers={"Authorization": f"Bearer {token}", "Client-Id": c["client_id"]})
            r.raise_for_status()
            u = r.json()["data"][0]
            profile = {"id": u["id"], "name": u["display_name"], "avatar": u.get("profile_image_url")}
        else:
            r = await http.get("https://www.googleapis.com/youtube/v3/channels",
                               params={"part": "snippet", "mine": "true"},
                               headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            items = r.json().get("items") or []
            if not items:
                raise RuntimeError("Dieses Google-Konto hat keinen YouTube-Kanal")
            sn = items[0]["snippet"]
            profile = {"id": items[0]["id"], "name": sn["title"],
                       "avatar": sn.get("thumbnails", {}).get("default", {}).get("url")}
    _update(provider, account=profile)
    return profile


async def disconnect(provider: str) -> None:
    p, c = PROVIDERS[provider], _conn(provider)
    token = c.get("access_token")
    if token:  # Widerruf ist best effort
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                if provider == "twitch":
                    await http.post(p.revoke_url, data={"client_id": c["client_id"], "token": token})
                else:
                    await http.post(p.revoke_url, params={"token": token})
        except httpx.HTTPError:
            pass
    data = store.load()
    conn = data["connections"].get(provider, {})
    for k in ("access_token", "refresh_token", "expires_at", "scopes", "account"):
        conn.pop(k, None)
    store.save(data)


def public_status(provider: str, port: int) -> dict:
    p, c = PROVIDERS[provider], _conn(provider)
    return {
        "key": provider,
        "label": p.label,
        "has_credentials": bool(c.get("client_id") and c.get("client_secret")),
        "client_id": c.get("client_id", ""),
        "connected": bool(c.get("access_token")),
        "account": c.get("account"),
        "scopes": list(p.scopes),
        "redirect_uri": redirect_uri(provider, port),
        "console_url": p.console_url,
    }
