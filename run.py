"""Startet den lokalen Server: python run.py"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("OVERLAY_PORT", "8080"))
    # Ein Prozess, kein Reload, minimale Logs, WebSocket-Ping aus (keine Hintergrund-Timer)
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, workers=1,
                log_level="warning", access_log=False, ws_ping_interval=None)
