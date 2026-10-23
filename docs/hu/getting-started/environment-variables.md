---
icon: lucide/settings
---

# Környezeti változók

Minden környezeti változó opcionális. A Downtify egyik nélkül is azonnal működik.

## Alapvető

| Változó | Alapértelmezés | Leírás |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(nincs beállítva)_ | A port, amelyen a szerver figyel (a konténeren belül). Ha nincs beállítva: a **Beállítások → Szerver → Port** alatt választott port, különben `8000`. Beállítva elsőbbséget élvez, és a Beállítások mezője zárolt. Másik gazdagépport elérhetővé tételéhez módosítsd a portleképezés bal oldalát. Lásd: [A port módosítása](../features/server.md#changing-the-port). |
| `DOWNLOAD_DIR` | `/downloads` | A könyvtár, ahová a hangfájlok mentődnek. Írd felül, ha a könyvtáradat egyéni útvonalra csatolod. |
| `HOST` | `0.0.0.0` | A webszerver kötési címe. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Az alkalmazás naplószintje (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Helyi időzóna (IANA-név, pl. `America/Sao_Paulo`), amely alapján a lenti `DOWNTIFY_MONITOR_SYNC_TIME` értelmeződik. |

## Lejátszási lista figyelő

| Változó | Alapértelmezés | Leírás |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(nincs beállítva)_ | A napszak (24 órás `HH:MM`, a fenti `TZ` szerint helyi), amikor a napi vagy hosszabb (naponta, hetente, 2 hetente, havonta) intervallumú [Lejátszási lista figyelő](../features/playlist-monitor.md#choosing-a-daily-sync-time) szinkronizálásoknak le kell futniuk. Hagyd beállítatlanul, hogy pontosan egy intervallummal az előző ellenőrzés után szinkronizáljon, bármilyen időpontra essen is. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Mobilalkalmazások és bejelentkezés

Lásd: [Mobilalkalmazások](../features/mobile-apps.md) és [Felhasználók és bejelentkezés](../features/users.md). A bejelentkezés kötelező, kivéve ha a `DOWNTIFY_DISABLE_AUTH` értéke `true`; a korábbi verziók `DOWNTIFY_REQUIRE_SIGN_IN` változóját már nem használja (amíg be van állítva, figyelmeztetést naplóz).

| Változó | Alapértelmezés | Leírás |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | A `true` kikapcsolja a fiókokat: senki nem jelentkezik be, és aki eléri a szervert, adminisztrátorként használja. A bejelentkezési oldal, a kijelentkezés gombok, a **Beállítások → Felhasználók** és a **Beállítások → Általános** fiókrésze eltűnik. A párosított alkalmazások tovább működnek. Állítsd vissza `false`-ra (vagy töröld), és a bejelentkezés újra kötelező, a fiókok pedig úgy maradtak, ahogy voltak. Lásd: [Felhasználók és bejelentkezés](../features/users.md#turning-accounts-off). |
| `DOWNTIFY_TRUSTED_PROXIES` | _(nincs beállítva)_ | A fordított proxyd vesszővel elválasztott címei vagy hálózatai (pl. `172.18.0.0/16,10.0.0.5`). Csak az ezektől érkező kéréseknél hisz az `X-Forwarded-For`, `X-Forwarded-Proto` és `X-Forwarded-Host` fejléceknek — a kliens címénél, amely alapján a bejelentkezési és párosítási kísérleteket korlátozza, a bejelentkezési süti secure jelzőjénél és az azonos webhelyre vonatkozó ellenőrzésnél. Ha nincs beállítva: ezeket a fejléceket figyelmen kívül hagyja. |
| `DOWNTIFY_DISCOVERY` | `true` | A `false` leállítja a szerver hirdetését a helyi hálózaton (mDNS, `_downtify._tcp`), amelyet az alkalmazások arra használnak, hogy a *Ezen a hálózaton található* alatt felsorolják. A Docker bridge hálózatában a hirdetés amúgy sem jut el a LAN-ra — lásd: [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | A legnagyobb méret MB-ban, amely alatt az átkódolt másolatok gyorsítótárát (`/data/transcode_cache`) tartja; a legrégebben lejátszott másolatok mennek előbb. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Hány dalt kódol át egyszerre az alkalmazások kisebb streaming-minőségeihez. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | A legnagyobb méret MB-ban, amely alatt a streamelt hang gyorsítótárát (`/data/stream_cache`) tartja; a legrégebben lejátszott másolatok mennek előbb. A szerveren át történő streamelés játssza le a le nem töltött számokat ott, ahol maga a böngésző nem éri el a YouTube-ot. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Hány streamletöltés futhat egyszerre. |

## Állapotellenőrzés

A képfájl beépített [Docker `HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck) ellenőrzést tartalmaz — egyéni `--health-cmd` nem szükséges. Ez 30 másodpercenként lekérdezi a `GET /api/health` végpontot a konténer saját portján (5 másodperces időtúllépés, 20 másodperces indulási türelmi idő, 3 újrapróbálkozás, mielőtt a konténert nem egészségesnek jelöli). A `docker ps` és a `docker inspect` mutatja az eredményt, és az olyan eszközök, mint a Compose `condition: service_healthy` feltétele vagy a Watchtower, reagálhatnak rá.

| Változó | Alapértelmezés | Leírás |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Állítsd `0`-ra a beépített ellenőrzés kikapcsolásához — ekkor mindig „egészséges”-t jelent, a szerverrel való kapcsolatfelvétel nélkül. Akkor használd, ha egy külső/orkesztrátorszintű ellenőrzésnek (pl. egy Kubernetes liveness probe) kell egyedül dönteni a konténer állapotáról. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Bot-ellenes védelem / YouTube

A YouTube időnként kihívás elé állítja az automatizált letöltőket. Ezek a változók menekülőutakat adnak, ha az alapértelmezések már nem működnek.

| Változó | Alapértelmezés | Leírás |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(nincs beállítva)_ | Állítsd `1`-re, hogy a yt-dlp csak IPv4-et használjon. Hasznos, ha a gazdagépednek hibás vagy sebességkorlátozott IPv6-címe van. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | A kipróbálandó yt-dlp lejátszókliensek vesszővel elválasztott, sorrendezett listája. A Downtify alapértelmezett listája már előnyben részesíti a JavaScript-futtatókörnyezet nélkül működő klienseket. Csak akkor módosítsd, ha tudod, hogy egy adott klienst blokkolnak. |
| `DOWNTIFY_YT_PO_TOKEN` | _(nincs beállítva)_ | A yt-dlp-hez vesszővel elválasztott Proof-of-Origin tokenek, mindegyik `<client>.<context>+<token>` alakban (pl. `mweb.gvs+ABC123`). Csak akkor kellenek, ha a YouTube PO Tokeneket kezd követelni a használt kliensekhez. |
| `DOWNTIFY_COOKIES_FILE` | _(nincs beállítva)_ | Egy Netscape formátumú `cookies.txt` útvonala **a konténeren belül**. Lehetővé teszi, hogy a yt-dlp valódi böngészőmunkamenetként hitelesítsen — explicit/korhatáros számokhoz és mindig szükséges, amikor a YouTube bejelentkezési falat kényszerít. Elsőbbséget élvez a webes felületen feltöltött fájllal szemben, és a felület ezen részét csak olvashatóvá teszi. Lásd: [YouTube sütik](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(nincs beállítva)_ | A böngésző neve, amelyből a sütiket kinyeri (pl. `chrome`, `firefox`). Megköveteli, hogy a böngésző sütitára a konténeren belülről elérhető legyen, ezért Dockerben ritkán használható. |

::: tip Valószínűleg nincs rájuk szükséged
Feltölthetsz egy `cookies.txt` fájlt közvetlenül a **Beállítások → YouTube sütik** oldalon a webes felületen. A `/data` könyvtárban tárolódik (így túléli a konténerfrissítéseket), nem kell hozzá bind mount vagy konténerútvonal, és Windowson, macOS-en és Linuxon ugyanúgy működik. A fenti változók továbbra is támogatottak azoknak a telepítéseknek, amelyek inkább maguk kezelik a fájlt.
:::

## Példa: Docker Compose bot-ellenes beállításokkal

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## cookies.txt beszerzése

Használj böngészőbővítményt, például a [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) vagy a [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox) bővítményt. Exportálj a `youtube.com` oldalról egy valódi Google-fiókba bejelentkezve, majd töltsd fel a fájlt a **Beállítások → YouTube sütik** alatt, vagy csatold a konténerbe a fent látható módon.

A teljes útmutatót lásd: [YouTube sütik](../features/youtube-cookies.md), és [Hibaelhárítás](../troubleshooting.md), ha a letöltések továbbra is meghiúsulnak.

::: warning
Tartsd privátan a `cookies.txt` fájlodat — olyan munkamenet-tokeneket tartalmaz, amelyek hozzáférést adnak a Google-fiókodhoz.
:::
