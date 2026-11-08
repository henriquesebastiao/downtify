---
icon: lucide/mic-vocal
---

# Dalszövegek

A Downtify a szám letöltése közben keresi meg a dalszövegeket, és beágyazza őket a fájlba, valamint egy `.lrc` kísérőfájlt is készít, ha időzítettek.

## A dalszövegek bekapcsolása

A dalszövegek **alapértelmezetten be vannak kapcsolva**. Kikapcsolás: **Beállítások → Címkék és dalszövegek → Dalszövegek letöltése**.

## Szolgáltatók és tartalék sorrend

A katalógusok különböznek: egy dal, amelyet az egyik szolgáltató nem ismer, gyakran megvan egy másiknál. A Downtify ezért rendezett szolgáltatólistát vezet, és egyenként próbálja őket, az első találatnál megállva.

| Szolgáltató | Dalszövegek | Megjegyzések |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Sima és időzített | Ingyenes közösségi adatbázis, kulcs nélkül. Cím, fő előadó, album és hossz alapján egyeztet. |
| **NetEase Cloud Music** | Általában időzített | Nagy katalógus, erős az ázsiai kiadványoknál és gyakran a nyugatiaknál is. Cím, előadó és hossz alapján egyeztet; az az eltérően írt előadónevű találat (például hagyományos és egyszerűsített kínai), csak akkor fogadható el, ha a cím és a hossz is egyezik. |

A **Beállítások → Címkék és dalszövegek → Szolgáltatók** alatt a szolgáltatókat a kívánt sorrendbe húzhatod, vagy a nyilakat használhatod, és bármelyiket kikapcsolhatod. Legalább egy bekapcsolva marad; a dalszövegek keresésének teljes leállításához használd a **Dalszövegek letöltése** kapcsolót.

::: info És a Genius, a Musixmatch meg az AZLyrics?
Nem érhetők el, és a Downtify már nem kínálja őket:

- Az **AZLyrics** tiltja a dalszövegeinek harmadik fél általi felhasználását magán az oldalon.
- A **Musixmatch** asztali API-ja üres tokent ad vissza, hacsak nincs olyan hitelesítő adatod, amelyet nem ad ki alkalmazásoknak.
- A **Genius** `robots.txt` fájlja letiltja a dal oldalának megtalálásához szükséges keresési végpontot.

A mentett beállítások, amelyek még megnevezik őket, tovább működnek: a neveket figyelmen kívül hagyja, és az a lista, amelyben semmi más nem marad, visszaáll az alapértelmezett szolgáltatókra.
:::

## A semmit sem találó szolgáltatók kihagyása

Egy keresés után a Downtify minden dalhoz feljegyzi, mely szolgáltatók válaszoltak és melyek jöttek vissza üresen, a `/data` alatti `downtify_library.db` fájlban.

Az a szolgáltató, amelynek nem volt semmi egy dalhoz, **30 napig** nem kérdezhető meg újra róla, hogy az újralétöltések és a nagy könyvtár-átfutások ne ismételjék ugyanazokat a sikertelen kereséseket. Ezután újra próbálja, mert a katalógusok bővülnek. Az a szolgáltató, amelynek *volt* dalszövege, soha nem marad ki, így egy újra letöltött fájl visszakapja.

## Beágyazás

| Formátum | Sima dalszöveg címkéje | Időzített dalszöveg címkéje |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` időbélyegekkel |
| FLAC | `LYRICS` (Vorbis-megjegyzés) | `LYRICS` LRC-tartalommal |
| M4A | `©lyr` | `©lyr` LRC-tartalommal |
| OGG / OPUS | `LYRICS` (Vorbis-megjegyzés) | `LYRICS` LRC-tartalommal |

## .lrc kísérőfájl

Ha időzített dalszöveg áll rendelkezésre, a Downtify `.lrc` fájlt is mentet. Alapértelmezetten **a hang mellett** található, azonos alapnévvel. A **Beállítások → Címkék és dalszövegek** alatt ezt kikapcsolhatod, és helyette **dalszövegmappát** választhatsz (alapértelmezés: `/data/lyrics`). Ennek a mappának a `/downloads`, a slskd-fa és az összes további zenemappa **kívül** kell lennie — a hang relatív útvonala létrejön benne (`Előadó/Album/szám.lrc`). Azok a lejátszók, amelyek külső dalszöveget olvasnak (és a [beépített lejátszó](player.md#now-playing)), továbbra is megtalálják a kísérőfájlt. E beállítás módosítása és a **Szinkronizálás** futtatása egy további mappán a meglévő `.lrc` fájlokat az új helyre másolja; a forrásfájl törlődik, ha az a fa írható, és csak olvasható csatolásnál a helyén marad. Kísérőfájl akkor is íródik, ha a dalszöveg már be van ágyazva a címkékbe.

A szám törlése a Könyvtár oldalról a `.lrc` fájlt (a fájl mellettit és a dedikált mappában lévőt) is eltávolítja a hanggal együtt, így a dalszöveg soha nem marad árva fájlként.

## Ha semmit sem talál

Ha egyik szolgáltatónál sincs meg a dal, a letöltés normálisan folytatódik — a hangfájl dalszöveg nélkül mentődik, és nem keletkezik hiba.
