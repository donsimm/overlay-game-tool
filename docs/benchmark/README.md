# Sprachvergleich für den Server (gemessen am 31.10.2026)

Gleicher Mini-Server in vier Sprachen: HTTP + WebSocket, 3 offene Overlays, 5 Nachrichten pro Sekunde (je ca. 300 Byte).
Gemessen mit `drive.py` (RSS aus `/proc`, CPU aus `/proc/<pid>/stat`, 20 s Messfenster), Linux x86_64, 4 Kerne.
Das ist nur das Gerüst (ohne Twitch-Anbindung, OAuth, TLS-Client). Die echte Anwendung braucht in jeder Sprache etwas mehr.

| Sprache / Bibliothek | RAM Leerlauf | RAM mit 3 Overlays | CPU (ein Kern) | Threads | Programmdatei |
|---|---|---|---|---|---|
| Rust 1.97, axum, 1 Thread | 2,6 MB | 2,7 MB | 0,1 % | 1 | 0,8 MB (eine Datei) |
| Go 1.24, coder/websocket | 7,3 MB | 8,0 MB | 0,25 % | 6 | 5,8 MB (eine Datei) |
| Python 3.13, asyncio + websockets | 24 MB | 24 MB | 0,2 % | 1 | Interpreter nötig |
| Node.js 22, ws | 58 MB | 56 MB | 0,35 % | 7 | Node nötig |
| **Aktuelle Anwendung** (Python, FastAPI, httpx) | **52 MB** | **52 MB** | **0,9 %** (inkl. HTTP-Last) | 5 | Interpreter + Pakete nötig |

Nachbauen: Server starten (`python3 server.py PORT`, `node server.js PORT`, gebaute Go-/Rust-Datei mit PORT), `drive.py` an die Pfade anpassen.
