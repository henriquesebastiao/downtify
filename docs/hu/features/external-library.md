---
icon: lucide/folder-plus
---

# Meglévő zenemappák

A Downtify Könyvtára a letöltött fájlokból épül fel — plusz azokból a **további mappákból**, amelyekre rámutatsz. Ezek a mappák nem másolódnak a `/downloads` könyvtárba. A Downtify beolvassa minden fájl címkéit (cím, előadó, album, sorszám, év), kihagyja a már meglévő dalokat, a többit pedig a megfelelő előadó alá sorolja a Könyvtárban és a lejátszóban.

## Mappák hozzáadása

1. Csatold a gazdagép mappáját a konténerbe (Docker). A Beállításokban megadott útvonal a **konténeren belüli** útvonal, ugyanaz a szabály, mint a [slskd letöltési mappájánál](slskd-navidrome.md).
2. Nyisd meg a **Beállítások → Könyvtár** oldalt.
3. A **Meglévő zenei mappák** alatt adj hozzá egy vagy több útvonalat (például `/music/collection`). A mező gépelés közben könyvtárakat javasol.
4. Kattints a **Mentés** gombra, ha szinkronizálás nélkül is meg akarod tartani őket, vagy a **Mappák szinkronizálása** gombra — ez elmenti a listát és azonnal szkennel.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Ekkor a mappa a Beállításokban `/music/collection`.

::: warning A fájlok ott maradnak, ahol vannak
A szinkronizálás nem másol fájlokat a `/downloads` könyvtárba. Ha a mappa írható, **beleír** ezekbe a fájlokba ugyanazokat a kiegészítőket, mint egy letöltés: dalszöveget (és egy `.lrc` kísérőfájlt — a fájl mellé vagy a Beállításokban választott mappába), borítót, ha a fájlnak nincs, és műfajt az iTunes-ról, ha tud. Egy későbbi szinkronizálás akkor is megírja a hiányzó kísérőfájlt, ha a dalszöveg már a címkékben van, és **áthelyez** egy meglévő `.lrc` fájlt a Beállításokban jelenleg választott helyre, ha az a forrásfájl írható. A Könyvtárból egy szám törlése továbbra is törli az adott fájlt a lemezről.
:::

::: tip Csak olvasható csatolások
Csatold a gyűjteményt `:ro` móddal, ha nem akarod, hogy a Downtify újraírja az MP3-akat. A szinkronizálás ettől még indexeli őket. Tedd a `.lrc` fájlokat a [dalszövegmappába](lyrics.md#sidecar-lrc-file) (kapcsold ki a **.lrc a hangfájl mellett** beállítást). A hiányzó borítók a `/data/cover_cache` alá kerülnek (a Könyvtár borítóvégpontja), nem az MP3-ba. Az iTunes-műfaj a Downtify könyvtári metaadat-adatbázisában tárolódik, nem a fájlban. Egy csak olvasható fájl mellett már meglévő `.lrc` a dalszövegmappába **másolódik**, és a helyén marad.
:::

## Mit csinál a szinkronizálás

1. Végigjárja az összes beállított mappát lejátszható hang után (ugyanazok a formátumok, mint a könyvtár többi részénél: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Beolvassa a beágyazott címkéket. A cím/előadó nélküli fájl a fájlnévben lévő `Előadó - Cím` mintára támaszkodik, mint a könyvtár többi sora.
3. **Kihagy** egy fájlt, ha a könyvtárban már megvan az a dal (azonos előadó + cím, és néhány másodpercen belüli hossz, ha mindkettő ismert) — akár a Downtify töltötte le, akár másik további mappából származik.
4. **Párosítja az előadókat** a könyvtárban már meglévő nevekkel (a `The Beatles` és a `Beatles` egy előadó lesz). Az ismert előadóval nem egyező nevek új előadóként jelennek meg. Az új előadók sorba kerülnek ugyanarra a profilkitöltésre (fotó/bemutatkozás, ha ezek a beállítások be vannak kapcsolva), mint egy befejezett letöltés.
5. **Úgy címkéz, mint egy letöltés**, ha a mappa írható. Minden importált számhoz ugyanazokat a dalszövegszolgáltatókat, ugyanazt a borítókeresést (csak ha a fájlnak nincs képe) és ugyanazt az iTunes-műfajkeresést használja, mint egy letöltés. A dalszöveg a fájlba kerül; egy `.lrc` kísérőfájl a hang mellé vagy a Beállításokban választott [dalszövegmappába](lyrics.md#sidecar-lrc-file) íródik. A borító és a műfaj a [Letöltési beállításokat](download-settings.md) követi (`download_cover_art`, `download_lyrics`). **Csak olvasható** csatolásnál az MP3 nem íródik újra: a hiányzó borító a `/data/cover_cache` alá kerül, a műfaj a könyvtári katalógusban tárolódik, a `.lrc` fájlok pedig a dalszövegmappába mennek, ha választottál egyet. A keresések **Párhuzamos letöltések** méretű kötegekben futnak; a Beállítások → Letöltések és fájlok alatti **Szünet a szinkronizálás között** vár a kötegek között, hogy a nagy mappák ne ütközzenek a szolgáltatók kéréskorlátaiba.
6. Érvényteleníti a könyvtár útvonal-gyorsítótárát, hogy a Könyvtár oldal és a lejátszó a szokásos rövid szkennelési TTL megvárása nélkül lássa az eredményt.

A szinkronizálás **a háttérben** fut. Elhagyhatod a Beállításokat; ha visszatérsz, miközben még dolgozik, látod, hogy még szinkronizál. Amikor befejeződött, a Beállítások az **utolsó szinkronizálási naplót** mutatják (importált / duplikátum / hiba, plusz dalszöveg/borító megjegyzések).

Futtasd újra a **Mappák szinkronizálása** funkciót, miután további fájlokat tettél ezekbe a mappákba. A mappalista szinkronizálás nélküli mentése is beveszi őket a következő könyvtárszkennelésbe (körülbelül egy perc, vagy a következő letöltés/törlés).

Egy mappa törlése a listáról **leválasztja**: ezek a számok eltűnnek a Könyvtárból és a lejátszóból, a Downtify által készített kiegészítők (`.lrc` kísérőfájlok, gyorsítótárazott borítók) pedig törlődnek. A lemezen lévő hangfájlok a helyükön maradnak.

A nem létező vagy nem olvasható mappákat a szinkronizálás után jelzi; a többit ettől még szkenneli.

## Könyvtári útvonalak

A további mappák fájljai `ext/<id>/…` virtuális útvonalat használnak (az azonosító a mappa útvonalának hash-e, így a lista átrendezhető). A lejátszó és a `GET /media/…` ezt az útvonalat használja, akárcsak a `slskd/…` a helyükön hagyott Soulseek-fájloknál.

Az a mappa, amely már a `/downloads` (vagy a slskd forrásmappája) **belsejében** van, itt figyelmen kívül marad — az a fa már maga a könyvtár.

## API

| Metódus | Útvonal                       | Leírás                                                                           |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Háttérszkennelést indít. Az opcionális `{folders: ["/path", …]}` törzset előbb elmenti. |
| `GET`  | `/api/library/external/sync`  | A futó feladat, vagy az utolsó befejezett napló.                                 |
| `POST` | `/api/library/external/unmap` | Eltávolít egy mappát a könyvtárból a hang törlése nélkül.                        |

A válasz alakját lásd az [API-referenciában](../api-reference.md#post-apilibraryexternalsync).

## Elsődleges könyvtármappa

Válaszd a **Beállítások → Könyvtár → Primary library folder** lehetőséget, hogy a regisztrált
külső mappák egyikét előnyben részesítsd. Az alapértelmezés a meglévő viselkedést őrzi meg.
Egyező előadó, teljes cím (a verziót is beleértve) és album szükséges;
az ismeretlen metaadatok nem rejtenek el másik fájlt. Egy kiválasztott forrás képviselhet
olyan felvételt, amelynek másik másolata klipintrókat vagy -outrókat tartalmaz.

Ez megjelenítési beállítás, nem migráció. A forrásfájlok, a tárolt lejátszásilista-útvonalak,
a tulajdonjog, a kedvelések és a láthatósági szabályok nem íródnak újra, és nem törlődnek.
A lejátszási lista jelvényei a megjelenített képviselőn egyesülnek; az explicit módon mentett lejátszási listák
továbbra is az eredeti útvonalukat játsszák. A kiválasztott mappában lévő különböző albumok és verziók
külön maradnak. Az üres vagy elérhetetlen mappa a könyvtár többi részére esik vissza.
Eltávolítása visszaállítja a beállítást.
