---
icon: lucide/eye
---

# Lejátszási lista figyelő

A Lejátszási lista figyelő a kedvenc Spotify- és YouTube Music-lejátszási listáidat — és az általad követett előadókat — figyeli, és automatikusan letölti az új számokat és az új kiadványokat, ahogy megjelennek, anélkül hogy bármit tenned kellene.

Kétféle figyelés van, mindegyik a Figyelő oldal saját fülén (**Lejátszási listák** és **Előadók**, a `/monitor/playlists` és `/monitor/artists` címen):

| Figyelés | Illeszd be | Letölti |
|-------|-------|-----------|
| **Lejátszási lista** | Egy Spotify- vagy YouTube Music-lejátszásilista-URL | A lista minden számát, majd később minden hozzáadottat |
| **Előadó** | Egy Spotify-**előadó** URL-je, vagy egy YouTube Music-előadó URL-je | Az előadó teljes diszkográfiáját, majd minden új kiadványt |

Minden figyelés a neve alatt megmutatja a követett hivatkozást, és egy **Spotify** vagy **YouTube Music** jelvényt arról a szolgáltatásról, amelyből hozzáadták.

Lásd: [Előadófigyelés](#artist-watch), hogyan működnek az előadófigyelések.

A figyelések azoké, akik létrehozták őket: minden fiók a saját lejátszási listáit és előadóit követi (ugyanaz az URL kétszer figyelve kétszer fut le), és egy átfésülés a letöltéseit a figyelés tulajdonosának tulajdonítja. Egy admin minden figyelést lát.

## Hogyan működik

A Downtify egy háttérfeladatot futtat 60 másodpercenként. Minden átfésüléskor ellenőrzi, hogy minden engedélyezett figyelés esedékes-e vizsgálatra (a beállított intervalluma alapján). Amikor egy *lejátszási lista* esedékes, a Downtify:

1. Lekéri a teljes számlistát a Spotifyról vagy a YouTube Musicról
2. Összeveti a már letöltött számok halmazával
3. Letölti az új számokat ugyanazzal a folyamattal, mint egy kézi letöltést
4. Frissíti a lejátszási lista M3U-fájlját (ha az M3U-generálás be van kapcsolva)

Az első ellenőrzés, amely a figyelés hozzáadásakor azonnal elindul, letölt mindent, ami már a listán van; a későbbiek csak a közben hozzáadottat töltik le. A „már letöltött” egy kis SQLite-adatbázisban (`downtify_monitor.db` a `/data` alatt) van nyilvántartva, nem a letöltési mappa vizsgálatával — így egy letöltött fájl áthelyezése a lemez máshová (a saját könyvtárszerkezetedbe, másik meghajtóra, bárhová) **nem** készteti a Downtifyt arra, hogy hiányzónak higgye, és a következő ellenőrzéskor újra letöltse.

Egy külön átfésülés óránként fut, és ellenőrzi, hogy minden letöltött szám fájlja még megvan-e. A valóban törölt fájlokat (szemben az áthelyezettekkel) ekkor elfelejti, így a szám újra letölthetővé válik — a figyelés következő ellenőrzésekor az óránkénti átfésülés után, nem azonnal.

Egy figyelést soha nem ellenőriz kétszer egyszerre. A figyelés hozzáadása azonnal elindítja az első ellenőrzését; ha az még tölt, amikor a következő ütemezett átfésülés eljön, az átfésülés kihagyja a figyelést ahelyett, hogy ugyanazon számok második, átfedő letöltését indítaná.

## Lejátszási lista hozzáadása

1. Nyisd meg a **Figyelő** oldalt az oldalsávról (telefonon: **Továbbiak → Figyelő**), és maradj a **Lejátszási listák** fülön
2. Illessz be egy lejátszásilista-URL-t:
    - Spotify: `https://open.spotify.com/playlist/…`
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (a `www.youtube.com/playlist?list=…` hivatkozás is működik)
3. Válassz ellenőrzési intervallumot (15 perctől havonta egyszerig)
4. Kattints a **Lista figyelése** gombra

Minden fülnek saját mezője van. Egy előadóhivatkozás beillesztése a Lejátszási listák fülre (vagy lejátszásilista-hivatkozásé az Előadókhoz) nem ad hozzá semmit: az oldal megmondja, milyen hivatkozás, és felajánlja, hogy áthelyezi a megfelelő fülre.

A figyelést egy lejátszási lista oldaláról is elindíthatod: illeszd be a hivatkozását a keresősávba, és használd az **Új számok figyelése** (vagy egy YouTube Music-előadónál az **Új kiadások figyelése**) lehetőséget. A Könyvtárban lévő letöltött lejátszási listák ugyanezt a műveletet kínálják a **⋯** menüjükben. Az így hozzáadott figyelések 6 órás intervallumot használnak — módosítsd a Figyelő oldalon.

## YouTube Music-lejátszási listák

Használj YouTube Music-lejátszási listát olyan dalokhoz, amelyek nincsenek a Spotifyon: remixek, élő szettek, feldolgozások, promóciós csatornák feltöltései. Minden szám **a lejátszási listában lévő pontos videóról** töltődik le. A Downtify nem keresi meg újra, így azt kapod, amit a listához adtál.

- **Minden szám lekérődik**, bármilyen hosszú is a lista. A törölt vagy privát videók kimaradnak.
- **A YouTube Music által szürkített dalok is letöltődnek.** Az átalakítók és importálók (Soundiiz, TuneMyMusic és hasonlók) által készített listák gyakran egyszerű YouTube-feltöltésekként sorolják fel a dalokat, amelyeket a YouTube Music elérhetetlennek mutat, és nem ad dalazonosítót. A Downtify a bejegyzés bélyegképéből találja meg a videót, és úgy tölti le, mint bármelyiket, így egy ilyen lista nem lesz üres. Egy valóban törölt vagy privátra állított videó nem tölthető le: ha a YouTube Music így jelöli, kimarad, ha pedig csak bélyegképet ad, a szám sikertelenként jelenik meg a sorban.
- **Az előadó és a cím a videó címéből jön.** Sok lejátszásilista-bejegyzés a feltöltő csatornának tulajdonított feltöltés (pl. `MrSuicideSheep`), a valódi jóváírás pedig a címben van, mint a `Bronze Whale - Patterns`. Minden olyan esetén, ami nem katalóguskiadvány, a Downtify az `Előadó - Cím` részt szétválasztja a fájlnévbe és a címkékbe. Elhagyja az olyan utótagokat is, mint az `(Official Video)` vagy a `[Lyrics]`. A kötőjel utáni, verziót megnevező rész (`Yellow - Live at Glastonbury`) a címben marad. A katalógusszámok (hivatalos hang, vagy bármi, ami albumhoz van sorolva) megtartják a YouTube Music saját előadóját és címét.
- **Nem minden `list=` hivatkozás lejátszási lista.** Egy album `OLAK5uy_…` hivatkozása továbbra is albumként töltődik le. Egy `watch?v=…&list=…` hivatkozás az az egy dal, amely éppen szólt. Egy rádiókeverék (`list=RD…`) nem rendelkezik rögzített számlistával, és nem figyelhető.

## Előadófigyelés

Ahelyett, hogy előadónként lejátszási listát építenél, illessz be egy előadóhivatkozást, és a Downtify követi a teljes katalógusát. Adj hozzá egyet a Figyelő oldal **Előadók** füléről — illeszd be az URL-t, válassz intervallumot, kattints az **Előadó figyelése** gombra. Az előadófigyelések számok száma helyett kiadványszámot mutatnak.

Elfogadott URL-ek:

- Egy Spotify-előadó URL (`https://open.spotify.com/artist/…`)
- Egy YouTube Music-előadó URL, csatorna szerint (`https://music.youtube.com/channel/UC…`) vagy handle szerint (`https://music.youtube.com/@HenriqueeJuliano`)

A handle a figyelés hozzáadásakor feloldódik az előadó csatornájára, így ugyanaz az előadó handle-lel és csatorna-URL-lel beillesztve egy figyelésként ismerődik fel. Az a handle, amely nem YouTube Music-előadóhoz tartozik, elutasításra kerül.

Minden átfésüléskor a Downtify felsorolja az előadó diszkográfiáját, összeveti a már feldolgozott kiadványokkal, és letölti minden új kiadvány minden számát. Egy állandósult állapotú átfésülés egyetlen kérésbe kerül — a számlistákat csak azokhoz a kiadványokhoz kéri le, amelyeket még nem látott.

::: info Miért a YouTube Musicból jön a diszkográfia
A Spotify nyilvános embedje megadja egy előadó nevét és a legnépszerűbb számainak előnézetét, de a diszkográfiáját **nem** — ennek olvasásához Spotify API-hitelesítő adatok kellenének, amelyeket a Downtify szándékosan nem használ. Így egy Spotify-előadóhivatkozás a nevére oldódik fel, és ugyanazzal az előadóval egyeztetődik a YouTube Musicon, ahonnan a hang is jön. Az előny: minden kiadvány, amelyet a Downtify lát, olyan, amelyet ténylegesen le is tud tölteni. A kompromisszum: egy kétértelmű nevű előadónál ellenőrizd, hogy a figyelés feloldott neve az-e az előadó, akit szántál — illeszd be közvetlenül a YouTube Music-előadó URL-jét, ha rosszat választott.
:::

::: warning Az első átfésülés a teljes régi katalógust letölti
Egy előadó hozzáadása **minden** kiadványát sorba állítja, ami egy termékeny előadónál több száz album és kislemez is lehet. Állítsd be a **[Szünet a letöltések között](download-settings.md#delay-between-downloads)** értéket, mielőtt előadók egy kötegét hozzáadnád, különben nagy eséllyel lelassítanak — vagy kapcsold be az **Csak új kiadások** lehetőséget (lent), hogy a régi katalógust teljesen kihagyd.
:::

### A letöltendők kiválasztása

Az **Előadók** fülön a hivatkozásmező alatt (és egy figyelés **Szerkesztés** párbeszédablakában) két opció dönti el, mit tölt le egy előadófigyelés:

| Opció | Mit csinál |
|--------|--------------|
| **Letöltés: Albumok / Kislemezek / EP-k** | Csak a bejelölt fajták kiadványai töltődnek le. Mindhárom alapértelmezetten be van kapcsolva; legalább egynek bekapcsolva kell maradnia. A fajta a YouTube Music saját címkéje az egyes kiadványokhoz — az a kiadvány, amelyet nem címkéz, albumnak számít. |
| **Csak új kiadások** | Minden, amit az előadó a figyelés indulásakor már kiadott, kimarad; csak ami utána jelenik meg, töltődik le. Alapértelmezetten ki. |

Hogyan viselkednek, ha később módosítod őket:

- **Egy fajta bekapcsolása** letölti az adott fajta kiadványait a figyelés következő ellenőrzésekor — a régi katalógusát is, hacsak a **Csak új kiadások** be nincs kapcsolva (ekkor csak azokat, amelyek a figyelés indulása óta, vagy az opció bekapcsolása óta jelentek meg). A kikapcsolt fajta kiadványai soha nem kerülnek rögzítésre, így semmi nem vész el, ha egy fajtát egy időre kikapcsolsz.
- A **Csak új kiadások bekapcsolása** egy meglévő figyelésen mindent, ami addig megjelent, kihagyottként rögzít; a már letöltött kiadványok maradnak, ahogy vannak.
- **Kikapcsolása** a következő ellenőrzéskor letölti a kihagyott kiadványokat (a bejelölt fajtákból).
- Bármelyik opció mentése a **Szerkesztés** párbeszédablakban azonnal ellenőrzi a figyelést, ahelyett hogy a következő ütemezett ellenőrzésre várna.

A meglévő kiadványok „kihagyásához” egy sikeres pillantás kell az előadó diszkográfiájára: ha a YouTube Music üres listát ad vissza (ami gyakrabban fennakadás, mint olyan előadó, akinek semmije nincs kint), semmi nem rögzítődik, és a következő ellenőrzés újra próbálkozik, így egy rossz válasz soha nem tehet olyat, hogy a régi katalógus később töltődjön le. Egy **Csak új kiadások** figyelés másik előadóra irányítása ugyanígy kihagyja annak az előadónak a régi katalógusát.

A Figyelő listája a figyelés szűrőit a hivatkozása alatt mutatja, ha nem az alapértelmezettek (pl. **Albumok** · **Csak új**).

Egy kiadvány csak akkor kerül feldolgozottként rögzítésre, ha minden száma rendezett, így az átmeneti hibán elbukó számot a következő átfésülés újra megpróbálja, ahelyett hogy örökre kihagyná. A már letöltött számokat soha nem kéri le kétszer.

Az előadófigyelések nem generálnak M3U-fájlokat — a számok a [fájlszervezés](file-organization.md) beállításaid szerint kerülnek el, nem lejátszási listaként.

## Ellenőrzési intervallumok

| Címke | Perc | Legjobb ehhez |
|-------|---------|----------|
| 15 percenként | 15 | Gyakran frissülő lejátszási listák |
| 30 percenként | 30 | |
| Óránként | 60 (alapértelmezett) | A legtöbb lejátszási lista |
| 3 óránként | 180 | |
| 6 óránként | 360 | |
| 12 óránként | 720 | |
| Naponta | 1 440 | Lassan változó lejátszási listák |
| Hetente | 10 080 | Hetente frissülő lejátszási listák |
| 2 hetente | 20 160 | |
| Havonta | 43 200 | Archívum vagy ritkán frissülő lejátszási listák |

Egy meglévő lejátszási lista intervallumát bármikor módosíthatod a figyelőkártyáról, eltávolítás és újbóli hozzáadás nélkül.

## A figyelt lejátszási listák kezelése

Minden fül csak a saját fajta figyeléseit listázza. A lista felett:

- **Szűrés** — gépeld be egy név vagy a hivatkozás egy részét (pl. egy lejátszásilista-azonosítót) a lista szűkítéséhez
- **Mind / Szüneteltetett** — csak a szüneteltetett figyelések megjelenítése
- **Összes ellenőrzése most** — az aktuális fül minden aktív figyelésének ellenőrzése

Minden soron:

- **Aktív** kapcsoló — a figyelés szüneteltetése vagy folytatása eltávolítás nélkül
- **Ellenőrzések** — milyen gyakran ellenőrzik
- **Ellenőrzés most** (↻) — azonnali ellenőrzés, az ütemezésen kívül
- **Szerkesztés** (✎) — a figyelés hivatkozásának, intervallumának és aktív állapotának megtekintése és módosítása (lásd: [Figyelés szerkesztése](#editing-a-watch))
- **⋯** — szüneteltetés/folytatás, a hivatkozás másolása, az eredeti megnyitása, vagy **Figyelés leállítása** (a bejegyzés törlődik; a letöltött fájlok megmaradnak)

### Figyelés szerkesztése

Kattints egy figyelés nevére vagy a **Szerkesztés** gombjára. A párbeszédablak megmutatja a követett teljes hivatkozást a **Link másolása** és **Eredeti megnyitása** gombokkal, valamint hogy mikor adták hozzá a figyelést, mikor ellenőrizték utoljára, és hány száma vagy kiadványa van. Módosíthatod:

- **Hivatkozás** — ugyanolyan fajtájú hivatkozásnak kell lennie (lejátszási lista a lejátszásilista-figyeléshez, előadó az előadófigyeléshez):
    - Egy másik hivatkozás ugyanahhoz a lejátszási listához vagy előadóhoz (például más `?si=` megosztási kóddal, vagy a `www.youtube.com` helyett a YouTube Music hivatkozásával) csak a tárolt címet frissíti. Semmi más nem változik.
    - Egy **másik** lejátszási listára vagy előadóra mutató hivatkozás odairányítja a figyelést. A figyelés megtartja az intervallumát és az aktív állapotát, de átveszi az új nevet, és elölről kezdi: a letöltési vagy kiadványtörténete törlődik, és ha aktív, azonnal ellenőrzik. A könyvtáradban már meglévő számok nem töltődnek le újra, az előző cél fájljai pedig ott maradnak, ahol vannak.
    - Egy már figyelt dologra mutató hivatkozást elutasít.
- **Ellenőrzés ennyi időnként** és **Aktív**.

Ez hasznos a lecserélt „élő” lejátszási listáknál: nyisd meg a figyelést, hogy lásd, valójában melyik listát követi, és illeszd be az újat, ha megváltozott.

## Rendezés

A lista feletti **Rendezés** vezérlő az aktuális fület ez szerint rendezi:

| Mező | Megjegyzések |
|-------|-------|
| Hozzáadás dátuma | Alapértelmezett — legújabb elöl |
| Név | Betűrendben |
| Utolsó ellenőrzés | A legutóbb ellenőrzött elöl; a soha nem ellenőrzöttek legvégül |
| Ellenőrzési gyakoriság | A legritkább (leghosszabb intervallum) elöl |
| Számok / kiadványok száma | A legtöbb elöl |

Mellette lévő gomb váltogat a növekvő és csökkenő sorrend között. A választás megjegyződik a böngészőben, és csak a listát változtatja — az ellenőrzési sorrendet és az ütemezést nem.

## Napi szinkronizálási idő választása

Alapértelmezetten egy naponta (vagy hetente / 2 hetente / havonta) ellenőrzött lejátszási lista abban az időpontban szinkronizál, amikor eredetileg hozzáadták vagy utoljára ellenőrizték — nincs garantált napszak. Hogy a napos vagy hosszabb szinkronizálásokat egy adott órához rögzítsd (pl. éjjel 3-kor fussanak, bármikor helyett), állítsd be a `DOWNTIFY_MONITOR_SYNC_TIME` környezeti változót a `TZ` mellett. A teljes referenciáért lásd: [Környezeti változók](../getting-started/environment-variables.md#playlist-monitor).

- Csak a teljes napos vagy hosszabb intervallumokat érinti — a rövidebbeket (15 perc – 12 óra) nem, mert egyetlen napi időponthoz rögzítésük megtörné a ritmusukat.
- A lejátszási lista hozzáadása utáni legelső ellenőrzés mindig azonnal fut, ettől a beállítástól függetlenül.

## Számonkénti metaadat-gazdagítás

A Spotify lejátszási lista embed bejegyzéseiből hiányzik a megjelenés éve, és a számonkénti albumborító helyett a lejátszási lista borítóját használják. A Downtify minden új számot külön újra lekér, hogy letöltés előtt megkapja a helyes borítót és évet — ha a számonkénti lekérés meghiúsul, a lejátszásilista-szintű adatokra esik vissza. A YouTube Music-lejátszási lista bejegyzései kihagyják ezt a lépést: mindegyik már hordozza a saját videója metaadatait.

## M3U-integráció

A lejátszási lista M3U-ja **minden szám befejezése után** újraíródik, így az átfésülés letöltése közben nő, ahelyett hogy csak akkor jelenne meg, ha minden kész. A lista az első számtól kezdve lejátszható, és egy lassú vagy elakadt letöltés a lista lejjebb soha nem tartja fel a már megérkezett számokat. Az átfésülés végén egy utolsó újraírás mindent újra feloldoz a fájlrendszerrel szemben.

A kézi lejátszásilista-/albumletöltések és a CSV-importok ugyanígy viselkednek. A részletekért lásd: [M3U-exportálás](m3u-export.md#when-it-is-written).

Ha a [Lejátszási lista borítójának mentése](playlist-cover-art.md) be van kapcsolva, a borító átfésülésenként egyszer töltődik le, amelynek van letöltendő száma — az első előtt, hogy a mappa úgy nézzen ki, mint a lista, miközben telik. Az az átfésülés, amely nem talál újat, nem kéri le újra.

## Mi történik a listát elhagyó dalokkal

Az élő lejátszási listák (a Spotify *Top 50*-e, a *Discover Weekly*, szerkesztőségi toplisták) hetente változnak. A Downtify a figyelést **új zene forrásaként** kezeli, soha nem olyasmiként, ami azt szabályozza, mit tartasz meg:

- **A letöltött hangfájlokat egy figyelés soha nem törli.** Sem akkor, ha egy szám elhagyja a listát, sem ha minden általad figyelt listát elhagy, sem ha maga a lista zsugorodik, sem ha a **Figyelés leállítása** gombot nyomod.
- **Csak a lejátszási lista követi a lejátszási listát.** Minden átfésüléskor az [M3U-fájl](m3u-export.md) újraíródik a lista aktuális számaiból, az aktuális sorrendben, így egy kiesett szám eltűnik az M3U-ból. A fájlja a mappában marad, és a könyvtáradban is, kereshetően és lejátszhatóan — a Navidrome-on, Jellyfinen vagy bármin keresztül is, ami ugyanarra a mappára mutat.
- **Az a szám, amely semmilyen listán nincs rajta, továbbra is szám.** Semmi nem söpör „árva” fájlok után.

Ettől egy toplista használható felfedezési feeddé válik: új dalok érkeznek automatikusan, és amit hátrahagynak, az könyvtáradként gyűlik.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

Az egyetlen dolgok, amelyek hangot törölnek, azok, amelyeket kifejezetten kérsz: **Törlés** egy számon vagy kijelölésen a Könyvtárban, egy lejátszási lista törlése a Könyvtárból (ami törli a számait — előtte rákérdez), vagy a fájlok saját kezű eltávolítása a fájlrendszerből.

Ha egy nem kívánt számot ki akarsz venni a listából, és minden ellenőrzéskor kint akarod tartani, rejtsd el: lásd [Elrejtett számok a listákban](hidden-playlist-songs.md). A fájlja a könyvtáradban marad.

::: info Figyelés törlése vs. lejátszási lista törlése
A **Figyelés leállítása** (a figyelés ⋯ menüjében) csak a figyelést felejti el: a lemezen semmi nem változik. A **Törlés** egy lejátszási listán a **Könyvtár** oldalon a romboló — eltávolítja a lista számait, az M3U-ját és a katalógusbejegyzését.
:::

Ha egy fájl tényleg eltűnik — kivitted a letöltési mappából, vagy kézzel törölted —, egy óránkénti átfésülés észreveszi, és elfelejti a Downtify róla vezetett nyilvántartását, így egy még listázott szám figyelésének következő ellenőrzése újra letölti. Egy csak a letöltési mappán *belül áthelyezett* fájl továbbra is megtalálható, és nem töltődik le újra.

## Tárolás

A figyelő állapota egy SQLite-adatbázisban van a `/data/downtify_monitor.db` helyen. Az adatbázis rögzíti:

- Minden figyelést (fajta, Spotify- vagy YouTube Music-lejátszásilista-azonosító vagy YouTube Music-csatornaazonosító, név, URL, intervallum, engedélyezett állapot, utolsó ellenőrzés ideje). Hogy egy figyelés Spotify vagy YouTube Music, azt a tárolt URL-jéből olvassa ki, így nem kell külön oszlop.
- Minden sikeresen letöltött számot figyelésenként, a lemezen lévő fájlnévvel együtt
- Az előadófigyeléseknél a már feldolgozott kiadványokat, hogy egy átfésülés csak a valóban újakhoz kérjen le számlistákat — beleértve azokat is, amelyeket a **Csak új kiadások** kihagyott, ekként megjelölve, hogy a kikapcsolása visszahozhassa őket — plusz a figyelés kiadványfajtáit és hogy csak új kiadásokra szól-e

Az Előadófigyelés előtt létrehozott adatbázisok indításkor automatikusan migrálódnak; a meglévő sorok lejátszásilista-figyelésként működnek tovább.
