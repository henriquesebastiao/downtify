---
icon: lucide/list-music
---

# M3U-exportálás

A Downtify automatikusan szabványos `EXTM3U` lejátszásilista-fájlt hoz létre, valahányszor egy Spotify-lejátszási lista letöltődik — kézzel vagy a [Lejátszási lista figyelő](playlist-monitor.md) révén.

## A fájl helye

| Helyzet | M3U elérési útja |
|-----------|---------|
| Normálisan letöltött lejátszási lista | `<downloads>/<lejátszási-lista-neve>/<lejátszási-lista-neve>.m3u` |
| Bekapcsolt *Rendezés előadó szerint* mellett letöltött lejátszási lista | `<downloads>/Playlists/<lejátszási-lista-neve>.m3u` |

Ha a *Rendezés előadó szerint* be van kapcsolva, a számok több előadómappában oszlanak szét, ezért az M3U egy központi `Playlists/` könyvtárba kerül a lejátszási lista almappája helyett.

A [Kedvelt számok](liked-songs.md) is a `Playlists/Downtify Liked Songs.m3u` fájlba íródnak, az elrendezéstől függetlenül, és attól is függetlenül, hogy az *M3U listák írása* be van-e kapcsolva.

## Relatív útvonalak

Az M3U-ban a számok útvonalai **magához az M3U fájlhoz képest relatívan** vannak megírva, nem abszolút útvonalként. Így ugyanaz a fájl működik, akár a Downtify-konténeren belülről (`/downloads/…`), akár másik fogyasztótól olvassák, amely ugyanazt a könyvtárat más gyökérnél csatolja — például a Jellyfin a `/nas/music/…` alatt. Elég a médiaszervert ugyanarra a könyvtárcsatolásra irányítani, és a lejátszási lista egy egységként jelenik meg.

## Be- és kikapcsolás

Az M3U-generálást a **Beállítások → Letöltések és fájlok → M3U listák írása** szabályozza (alapértelmezetten be van kapcsolva). Kikapcsolva teljesen kimarad az M3U létrehozása; a letöltési folyamat többi része nem változik.

## Borító

Közvetlenül e beállítás alatt a **Lejátszási lista borítójának mentése** (alapértelmezetten be van kapcsolva) a lejátszási lista saját borítóképét az M3U mellé írja, azonos néven — a számok előtt, hogy a mappa a kezdetektől a lejátszási listához hasonlítson. A Downtify ezután ezt a képet mutatja a lejátszási listához a számborítók rácsa helyett. A Könyvtárban létrehozott lejátszási lista legfeljebb négy számborítóból álló mozaikot kap, ugyanígy megírva. Lásd: [Lejátszási lista borítók](playlist-cover-art.md).

## Mikor íródik

Az M3U **minden szám letöltésének befejezése után** újraíródik, így a lejátszási listafájl a letöltéssel együtt nő, ahelyett hogy a végén egyszerre jelenne meg. Ez egyaránt vonatkozik a lejátszási listák és albumok letöltésére, a [CSV-importokra](library-import.md) és a [Lejátszási lista figyelő](playlist-monitor.md#m3u-integration) átfutásaira.

Ez azt jelenti, hogy a lejátszási lista az első szám megérkezésétől lejátszható, menet közben látod, hogy a szinkronizálás működik, és egyetlen lassú vagy megakadt letöltés sem akadályozhatja meg, hogy az M3U — vagy a már elkészült számok — megjelenjen.

Egy végső újraírás akkor fut, amikor az egész futás befejeződött. Minden számot a fájlrendszerhez képest old fel (nem a memóriabeli listához képest, hogy ez a futás mit töltött le), így felveszi a korábbi futások fájljait is, és javít mindent, ami futás közben megváltozott a lemezen.

Minden írás a számokat **a lejátszási lista sorrendjében** sorolja fel, nem a letöltések befejezésének sorrendjében, így egy részben megírt M3U is helyesen rendezett.

::: info A lemezen már meglévő számok
A korábbi futás által letöltött számok végig az M3U-ban maradnak — az első írástól benne vannak, nem csak a végső tölti be őket.
:::

## Újragenerálás

Az M3U minden futáskor újragenerálódik — ugyanazon lejátszásilista-URL ismételt beillesztése teljes, rendezett fájlt eredményez, a korábbi futásokból hiányzó számokkal együtt.

A letöltésükben meghiúsult, vagy YouTube Music-találat nélküli számokat szó nélkül kihagyja.

## Kompatibilitás

A generált fájl a következőket használja:

- UTF-8 kódolás, BOM nélkül
- LF sorvégek
- A szabványos `#EXTM3U` / `#EXTINF` formátum

Kompatibilis a Jellyfinnel, Navidrome-mal, Plexszel, VLC-vel, Kodival, Sonosszal és minden más lejátszóval vagy médiaszerverrel, amely szabványos M3U lejátszási listákat fogyaszt.

## Általad létrehozott lejátszási listák

A **Könyvtár → Lejátszási listák → Új lista** ugyanilyen M3U-t ír a `Playlists/` alá, egy extra `#EXTDOWNTIFY:manual` sorral, hogy a Downtify meg tudja különböztetni a letöltött Spotify/YouTube-lejátszási listától. Átnevezheted, és dalokat adhatsz hozzá vagy távolíthatsz el (a [további mappákból](external-library.md) valókat is). A lejátszási lista törlése, egy szám törlése vagy egy további mappa leválasztása frissíti az M3U-t; a hang csak akkor törlődik, ha magát a számot vagy egy importált lejátszási listát törlöd.

### Dalok hozzáadása lejátszási listához

Az adminisztrátorok több helyről is betehetnek dalokat ezek egyikébe, vagy egy újba:

- **Egy dal ⋯ menüje** (bármely számlistában) → **Hozzáadás a listához**.
- **Jelölj ki több dalt** a Könyvtárban, és nyomd meg a **Hozzáadás a listához** gombot.
- **Egy album ⋯ menüje** → **Hozzáadás a listához** hozzáadja az album minden dalát.
- **Egy előadó ⋯ menüje** (az előadó oldalán) → **Hozzáadás a listához** hozzáad mindent, amit az előadó a könyvtáradban birtokol, albumonként.

Minden menü felsorolja a lejátszási listáidat és egy **Új lista…** bejegyzést, amely már ezekkel a dalokkal hoz létre egyet. A lejátszási listán már szereplő dalt kihagyja, a megerősítés pedig megmondja, hány került ténylegesen hozzáadásra (vagy hogy már mind ott volt). Egy lejátszási lista legfeljebb 500 dalt tartalmazhat.
