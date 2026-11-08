---
icon: lucide/cog
---

# Hogyan működik

A Downtify letöltési folyamata három szakaszból áll:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Metaadatok — a Spotify beágyazási oldalának beolvasása

Amikor beillesztesz egy Spotify-URL-t, a Downtify lekéri az adott szám, album vagy lejátszási lista nyilvános `open.spotify.com/embed` oldalát. Nincs szükség Spotify-fiókra, API-kulcsra vagy Premium előfizetésre — a beágyazási oldal nyilvánosan elérhető.

A **számoknál** a beágyazás visszaadja: a címet, az előadó(ka)t, az album nevét, a megjelenés évét, a hosszt és a borítókép URL-jét.

Az **albumoknál és lejátszási listáknál** a számlistát adja vissza. A lejátszási lista beágyazások körülbelül 50–100 bejegyzésre korlátozottak, ezért a Downtify a teljes listát a Spotify névtelen `api.spotify.com` végpontjától is lekéri, lapozással, hogy a több száz dalos lejátszási listákat is kezelje.

::: info Számonkénti metaadat-gazdagítás
A beágyazás lejátszásilista-bejegyzéseiből hiányzik a megjelenés éve, és az egyes számok saját albumborítója helyett a lejátszási lista borítóját használják. A [Lejátszási lista figyelő](features/playlist-monitor.md) számára a Downtify minden új számot külön újra lekér, hogy letöltés előtt megkapja a helyes borítót és évet.
:::

## 2. Hang illesztése — YouTube Music, aztán YouTube

A Downtify a [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) segítségével keresi a YouTube Musicban a legjobb hangegyezést. A keresési kifejezés a szám címéből és az előadó nevéből épül fel.

Egy találatot csak akkor fogad el, ha a címe hasonlít a forráscímre, és legalább egy előadót közösen birtokolnak. A Spotify kötőjeles verziótoldalékát és a YouTube Music zárójelesét ugyanannak tekinti (a `Tubarões - Ao Vivo` egyezik a `Tubarões (Ao Vivo)` címmel), és az előadói jelölést, amelyet a YouTube Music egy bejegyzésbe sűrít (`A, B, and C`), összehasonlítás előtt szétbontja. Az előadónevek elején álló „The” figyelmen kívül marad (az `Eden Project` egyezik a `The Eden Project` névvel), és egy cím egyezhet a feltöltés címének egy ` - ` jellel elválasztott részével (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`), amíg a többi rész nem nevez meg másik verziót. A karaoke-, feldolgozás-, instrumentális, gyorsított/lassított, élő (az `Ao Vivo`/`En Vivo` is), akusztikus, remix és más nyelvű (pl. `(Spanish Version)`) verziókat elutasítja, kivéve, ha maga a forrásszám az a verzió. A megmaradó találatok közül az nyer, amelynek hossza a legközelebb van a Spotify-éhoz, egyező albumnévért bónusszal. Ha egyetlen találat sem felel meg, a keresést a szavak fordított sorrendjében megismétli (`<cím> <előadó>` a `<előadó> <cím>` helyett) — a YouTube Music a szósorrendtől függően másképp rangsorol, és egyes dalok csak az egyik irányban jönnek elő a lista elején. Ha ez sem hoz eredményt, és az album ismert, közvetlenül az album számlistáját vizsgálja át.

### Visszaesés a hagyományos YouTube-ra

Egyes dalok hiányoznak a YouTube Musicból, vagy ott csak másik felvételként léteznek. Ezért a hagyományos YouTube-ot is keresi, ha:

- a YouTube Musicnak **nincs elfogadható találata**, vagy
- a legjobb találat hossza **több mint 10 másodperccel** tér el a Spotify-étól — ez erős jele annak, hogy másik felvételről van szó (pl. azonos című szinkronizált verzió).

A hagyományos YouTube találatai ugyanazokon a cím-, előadó- és verzióellenőrzéseken mennek át, és soha nem fogadja el őket, ha több mint 30 másodperccel eltérnek a Spotify hosszától. Egy YouTube-találat csak akkor váltja le a gyenge YouTube Music-találatot, ha a hossza szigorúan közelebb van; különben a YouTube Music-találat marad, mert a katalógusfeltöltések hangja általában a legtisztább.

Ha egyik oldalon sincs elfogadható találat, a szám a rossz dal letöltése helyett a `Could not find a YouTube match for '<title>'` hibával meghiúsul.

A közvetlenül megadott YouTube-URL-eknél ez a lépés kimarad — a Downtify azt a konkrét videót tölti le.

::: info Deezer-hivatkozások
A beillesztett Deezer-szám/album/lejátszási lista/előadó hivatkozás (`deezer.com/track/…`) úgy működik, mint a Spotify-é: a Deezer nyilvános REST API-ja adja a címet, az előadó(ka)t, az albumot és a borítót, minden szám teljes hosszában streamelhető a YouTube-ról letöltés előtt, és ugyanez a lépés illeszti a YouTube Musicon/YouTube-on. A Downtifynak nincs saját Deezer-diszkográfia-feloldója azon túl, amit a Deezer API már visszaad, ezért egy Deezer-hivatkozás letölthető és (lejátszási listánál) saját M3U-t és borítót kap, de a [Lejátszási lista figyelő](features/playlist-monitor.md) nem figyelheti.
:::

## 3. Letöltés és címkézés — yt-dlp + ffmpeg + mutagen

### Letöltés

A [yt-dlp](https://github.com/yt-dlp/yt-dlp) tölti le a hangot a YouTube-ról. A Downtify úgy állítja be, hogy több lejátszókliensen próbálkozzon sorban (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`), hogy kikerülje a YouTube botfelismerési kihívásait. A haladó bot-ellenes beállításokat lásd: [Környezeti változók](getting-started/environment-variables.md).

### Átalakítás

Az [ffmpeg](https://ffmpeg.org/) a nyers hangot a kiválasztott formátumra (MP3, FLAC, M4A, OGG vagy OPUS) alakítja a kiválasztott bitrátával.

### Címkézés

A [mutagen](https://mutagen.readthedocs.io/) beleírja a metaadatokat az átalakított fájlba:

| Címke | Beírja |
|-----|---------|
| Cím | Igen |
| Előadó(k) | Igen, minden közreműködő előadó, egy `ARTISTS` címkében értékenként egy is |
| Album előadója | Igen, az album saját előadója, ahogy a forrás feltünteti, egyébként az első előadó |
| Válogatás jelző | Csak olyan albumnál, amelyet a forrás „Various Artists” előadónak tulajdonít, vagy amelyet egy admin annak jelöl |
| Album | Igen |
| Év | Igen |
| Albumborító (JPEG) | Igen |
| Dalszöveg (sima + időzített) | Igen, ha az lrclib ad találatot |
| Explicit jelölés | Igen, ha a dal explicitként van megjelölve (lásd: [Explicit jelölés](features/explicit-marker.md)) |

A pontos ID3/Vorbis/MP4 címkék a kimeneti formátumtól függenek. A dalszövegek beágyazásának részleteit lásd: [Dalszövegek](features/lyrics.md).

## Valós idejű előrehaladás

A Downtify a letöltések előrehaladását **WebSocket**-kapcsolaton (`/api/ws`) keresztül streameli a böngészőnek. Ahogy a yt-dlp jelzi az előrehaladást, a szerver százalék- és állapotfrissítéseket küld az összes csatlakozott kliensnek. Így valós időben látod mozogni az előrehaladássávot — lekérdezés és oldalújratöltés nélkül.

## Fájlnevek és szervezés

A kimeneti fájlnév a Beállításokban megadott sablonból épül fel (alapértelmezés: `{artists} - {title}`). A fájlnevekben érvénytelen karakterek eltávolításra kerülnek.

Ha a *Rendezés előadó szerint* be van kapcsolva, a fájl az album előadójának nevét viselő almappába kerül — több előadós válogatás számánál pedig az első előadójáéba. Egyébként az önálló számok a letöltési könyvtár gyökerébe, a lejátszási lista-/albumszámok pedig lejátszási listánkénti vagy albumonkénti almappába mennek. Lásd: [Több előadó és válogatások](features/file-organization.md#several-artists-and-compilations).
