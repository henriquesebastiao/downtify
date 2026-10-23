---
icon: lucide/file-code
---

# Docker Compose

A Docker Compose a Downtify futtatásának ajánlott módja tartós otthoni szerverbeállításokhoz. Megkönnyíti a frissítéseket, a biztonsági mentéseket és a konfigurációváltoztatásokat.

## Minimális beállítás

Hozz létre egy `docker-compose.yml` fájlt:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Indítsd el:

```bash
docker compose up -d
```

Nyisd meg a **[http://localhost:8000](http://localhost:8000)** címet.

## slskd-vel (Soulseek)

Ha a [slskd-t hangforrásként](../features/slskd-navidrome.md) használnád, csatold a Downtifyba a slskd letöltési mappáját is — **ugyanazt a gazdagépmappát**, amelybe a slskd-konténered ír:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Ezután a **Beállítások → Hangforrások → slskd** alatt kapcsold be a slskd-t, add meg az URL-jét (pl. `http://slskd:5030`, ha a két konténer közös Docker-hálózaton van) és az API-kulcsot, a letöltési mappát pedig állítsd `/slskd`-re.

## Meglévő zenemappák

Hogy a Könyvtár felvegyen egy, a gazdagépen már meglévő gyűjteményt, [csatold](../features/external-library.md) ugyanígy, és a **konténerbeli** útvonalat add meg a **Beállítások → Könyvtár** alatt:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## A szerver megtalálása az alkalmazásokból

A [mobilalkalmazások](../features/mobile-apps.md#finding-the-server-on-your-network) mDNS-en keresztül sorolják fel a hálózatodon lévő Downtify-szervereket. A Docker alapértelmezett bridge hálózatában ez a hirdetés sosem hagyja el a Dockert, így a telefonok nem látják. Hogy megjelenjen, futtasd a konténert a gazdagép hálózatán — a `ports:` leképezés ekkor már nem érvényes, és a Downtify közvetlenül a `DOWNTIFY_PORT` porton figyel:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Egyébként egyszerűen add meg a szerver címét az alkalmazásban (`http://<a gazdagép IP-je>:8000`); semmi más nem függ a felfedezéstől.

## Egyéni port

Ha a 8000-es port már foglalt, képezz le másik gazdagépportot, és állítsd be a `DOWNTIFY_PORT` környezeti változót, hogy a konténer belül ugyanazon a porton figyeljen:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

A portot a **Beállítások → Szerver → Port** alatt is kiválaszthatod a `DOWNTIFY_PORT` beállítása helyett (amely, ha be van állítva, elsőbbséget élvez a Beállításokkal szemben). Az alapértelmezett bridge hálózatban állítsd át a `ports:` leképezést ugyanarra a portra, és hozd létre újra a konténert — lásd: [A port módosítása](../features/server.md#changing-the-port).

## Egyéni DNS-sel (ajánlott)

Egyes internetszolgáltatók és vállalati hálózatok blokkolják a YouTube-ot. Kifejezett DNS-feloldók hozzáadása javítja a megbízhatóságot:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Frissítés

```bash
docker compose pull
docker compose up -d
```

A zenéd és a beállításaid a kötetekben megmaradnak.

## Kötetek

| Útvonal a compose-fájlban | Cél |
|------------------------------|---------|
| `./downloads:/downloads` | Letöltött hangfájlok (helyi könyvtár) |
| `downtify_data:/data` | Az alkalmazás adatbázisa és beállításai (névvel ellátott kötet) |

A névvel ellátott kötetet lecserélheted helyi útvonalra (`./data:/data`), ha inkább magad kezeled.
