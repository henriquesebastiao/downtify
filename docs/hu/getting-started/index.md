---
icon: lucide/play
---

# Első lépések

A Downtify egy saját szerveren futtatható webalkalmazás, amely zenét tölt le a Spotifyról — API-kulcs, fiók és Premium előfizetés nélkül. Minden egyetlen Docker-konténerben fut.

## Mire van szükséged

- **Docker** (vagy Docker Compose) — az egyetlen követelmény a gazdagépen
- Egy internetelérésű gép
- Egy kötet/könyvtár, ahová a zenéd kerül

## Válaszd ki a telepítés módját

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  A leggyorsabb kezdés. Egyetlen parancs, egy percen belül fut.

  [Telepítés →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  Tartós telepítéshez ajánlott. Könnyebb frissíteni és kezelni.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **Telepítés egy kattintással**

  Umbrelt, CasaOS-t vagy HomeDock OS-t használsz? Telepítsd közvetlenül az alkalmazásboltjukból.

  [Telepítés egy kattintással →](one-click.md)

</div>

## Következő lépések

Amint a Downtify fut, nyisd meg a [http://localhost:8000](http://localhost:8000) címet a böngészőben. Illessz be egy Spotify-szám, -album vagy -lejátszási lista URL-jét a keresősávba, és kattints a **Letöltés** gombra.

A dokumentáció többi részéből megismerheted a [letöltési beállításokat](../features/download-settings.md), a [lejátszási lista figyelőt](../features/playlist-monitor.md), a [beépített lejátszót](../features/player.md) és még sok mást.
