---
icon: lucide/download
---

# Telepítés

A Downtify futtatásának leggyorsabb módja egyetlen `docker run` parancs. A gazdagépen nincs szükség Pythonra, Node.js-re vagy más rendszerfüggőségre — minden a képfájlban van.

## Előfeltételek

- Telepített és futó [Docker](https://docs.docker.com/get-docker/)

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Cseréld a `/path/to/music` útvonalat arra a könyvtárra, ahová a zenéd kerüljön.

Amint a konténer elindult, nyisd meg a **[http://localhost:8000](http://localhost:8000)** címet a böngészőben.

## Kötetek

| Kötet | Cél |
|--------|---------|
| `/downloads` | Letöltött hangfájlok |
| `/data` | Az alkalmazás adatbázisa és tartós beállításai |

Mindkét kötet megmarad a konténer újraindításai és frissítései során. A `/downloads` kötet lehet bármely könyvtár a gazdagépen vagy egy névvel ellátott Docker-kötet.

## Egyéni port

Ha a Downtifyt másik gazdagépporton akarod elérhetővé tenni, módosítsd a `-p` bal oldalát:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # gazdagép:konténer
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Ezután nyisd meg a **[http://localhost:9090](http://localhost:9090)** címet.

## Frissítés

Húzd le a legújabb képfájlt, és hozd létre újra a konténert:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

A zenéd és a beállításaid a kötetekben megmaradnak.

## Mi következik?

- **[Docker Compose](docker-compose.md)** — egyszerűbb mód a konténer hosszú távú kezelésére
- **[Környezeti változók](environment-variables.md)** — a bot-ellenes viselkedés és egyéb haladó beállítások finomhangolása
- **[Letöltési beállítások](../features/download-settings.md)** — válaszd ki a formátumot és a bitrátát
