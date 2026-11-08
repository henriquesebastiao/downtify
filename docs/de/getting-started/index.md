---
icon: lucide/play
---

# Erste Schritte

Downtify ist eine selbst gehostete Web-App, die Musik von Spotify herunterlädt — ohne API-Schlüssel, ohne Konto, ohne Premium-Abo. Alles läuft in einem einzigen Docker-Container.

## Was du brauchst

- **Docker** (oder Docker Compose) — die einzige Voraussetzung auf dem Host
- Einen Rechner mit Internetzugang
- Ein Volume bzw. Verzeichnis, in dem deine Musik gespeichert werden soll

## Wähle deine Installationsart

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  Der schnellste Einstieg. Ein Befehl, in unter einer Minute startklar.

  [Installation →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  Empfohlen für dauerhafte Setups. Einfacher zu aktualisieren und zu verwalten.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **Installation mit einem Klick**

  Du nutzt Umbrel, CasaOS oder HomeDock OS? Installiere direkt aus deren App-Stores.

  [Installation mit einem Klick →](one-click.md)

</div>

## Nächste Schritte

Sobald Downtify läuft, öffne [http://localhost:8000](http://localhost:8000) im Browser. Füge die URL eines Spotify-Titels, -Albums oder einer -Playlist in die Suchleiste ein und klicke auf **Herunterladen**.

Im Rest der Dokumentation erfährst du mehr über die [Download-Einstellungen](../features/download-settings.md), die [Playlist-Überwachung](../features/playlist-monitor.md), den [integrierten Player](../features/player.md) und vieles mehr.
