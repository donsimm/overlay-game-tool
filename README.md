# Overlay Game Tool

Lokaler Generator für OBS-Overlays (Browserquelle) mit Twitch- und YouTube-Anbindung.
Stand: Grundgerüst – Oberfläche, Modulverwaltung, Twitch-/YouTube-Login. Die einzelnen Overlays folgen.

## Start (Linux)

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    python run.py

Oberfläche: http://localhost:8080 (nur lokal erreichbar, Port änderbar mit `OVERLAY_PORT`).

## Twitch / YouTube verbinden

Pro Dienst wird eine eigene App benötigt (Client-ID und Client-Secret). Diese trägst du unter
«Verbindungen» ein; dort steht auch die Weiterleitungs-URL, die in der App eingetragen werden muss.

- Twitch: https://dev.twitch.tv/console/apps
- YouTube: https://console.cloud.google.com/apis/credentials (OAuth-Client «Webanwendung», YouTube Data API v3 aktivieren)

## Module in OBS

Unter «Module» ein Modul erstellen, die URL kopieren und in OBS als Browserquelle einfügen
(Breite/Höhe wie angezeigt).

## Editor (Layout live anpassen)

Bei Modulen mit verschiebbaren Elementen steht «Editor öffnen». Die Vorschau ist die echte Overlay-Seite.
Elemente ziehen, Punkt an der Ecke = Grösse, Panel = X/Y, Grösse, Drehung, Animation (an/aus, Art, Stärke).
Ebenen: Reihenfolge per Ziehen oder ▲▼, Sichtbarkeit per Häkchen.

**Eigene Texte und Bilder (in jedem Modul):** im Editor «+ Text» bzw. «+ Bild». Bilder (png, jpg, gif, webp, svg, webm, max. 25 MB)
liegen in der Bibliothek (`data/assets/`) und lassen sich mehrfach verwenden. Das Modul «Freies Overlay» ist eine leere Fläche
nur mit solchen Ebenen. Textanimationen: Schweben, Atmen, Wiegen, Schreibmaschine, Schreibmaschine mit Löschen.
Speichern (Ctrl+S) aktualisiert offene Overlays in OBS sofort, ohne Neuladen.

## Chat-Overlay (Twitch)

1. Twitch unter «Verbindungen» verbinden (Berechtigung `user:read:chat`, siehe unten).
2. Unter «Module» ein Modul «Chat» erstellen, die URL in OBS als Browserquelle einfügen (Breite/Höhe wie angezeigt).
3. Die Verbindung zu Twitch (EventSub-WebSocket) wird nur aufgebaut, solange ein Chat-Overlay in OBS offen ist (30 s Nachlauf).
   Der Zustand steht unter «Verbindungen» → Twitch → «Chat-Empfang» und in der Vorschau (`?debug=1`).
4. Test ohne Twitch: Auf der Modulkarte unter «Test (ohne Twitch)» (oder im Editor) Beispielnachrichten senden.

Was dargestellt wird: Text, Twitch-Emotes (animiert oder statisch), GIF-Nachrichten, Cheers (Bits), Erwähnungen, Antworten,
Badges, Namensfarben, hervorgehobene Nachrichten (Kanalpunkte) und Erstnachrichten, Subs/Resubs/Geschenke/Raids/Ankündigungen,
gelöschte Nachrichten und «Chat leeren». Optional 7TV/BTTV/FFZ-Emotes. Befehle (`!…`) und Bots lassen sich ausblenden.
Links werden standardmässig nur als `[domain]` gezeigt, nie als Bild nachgeladen. Bilder werden nur von `https` geladen.

Tests ohne Netzwerk: `python tests/test_chat_normalize.py`

## Ressourcen und Sicherheit

- Schrift: Be Vietnam Pro (lokal in `web/fonts`, Lizenz SIL OFL 1.1) ist die Standardschrift aller Overlays.
- Ein Prozess, keine Hintergrundtasks im Leerlauf, Konfiguration im Speicher gecacht, keine Netzwerkabfragen beim Öffnen der Oberfläche.
- Zugangsdaten und Tokens liegen in `data/config.json` (Dateirechte 600, nicht in Git).
- Server bindet nur an 127.0.0.1; schreibende Anfragen von fremden Webseiten werden abgelehnt.
