---
icon: lucide/eye
---

# Lejátszási lista figyelő

A Lejátszási lista figyelő a kedvenc Spotify-, nyilvános Deezer- és YouTube Music-lejátszási listáidat — és az általad követett előadókat — figyeli, és automatikusan letölti az új számokat és az új kiadványokat, ahogy megjelennek, anélkül hogy bármit tenned kellene.

Kétféle figyelés van, mindegyik a Figyelő oldal saját fülén (**Lejátszási listák** és **Előadók**, a `/monitor/playlists` és `/monitor/artists` címen):

| Figyelés | Illeszd be | Letölti |
|-------|-------|-----------|
| **Lejátszási lista** | Egy Spotify-, nyilvános Deezer- vagy YouTube Music-lejátszásilista-URL | A lista minden számát, majd később minden hozzáadottat |
| **Előadó** | Egy Spotify-**előadó** URL-je, vagy egy YouTube Music-előadó URL-je | Az előadó teljes diszkográfiáját, majd minden új kiadványt |

Minden figyelés a neve alatt megmutatja a követett hivatkozást, és egy **Spotify**, **Deezer** vagy **YouTube Music** jelvényt arról a szolgáltatásról, amelyből hozzáadták.

Lásd: [Előadófigyelés](#artist-watch), hogyan működnek az előadófigyelések.

A figyelések azoké, akik létrehozták őket: minden fiók a saját lejátszási listáit és előadóit követi (ugyanaz az URL kétszer figyelve kétszer fut le), és egy átfésülés a letöltéseit a figyelés tulajdonosának tulajdonítja. Egy admin minden figyelést lát.

## Hogyan működik

A Downtify egy háttérfeladatot futtat 60 másodpercenként. Minden átfésüléskor ellenőrzi, hogy minden engedélyezett figyelés esedékes-e vizsgálatra (a beállított intervalluma alapján). Amikor egy *lejátszási lista* esedékes, a Downtify:

1. Lekéri a teljes számlistát a Spotifyról, a Deezerről vagy a YouTube Musicról
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
    - Nyilvános Deezer-lista: `https://www.deezer.com/playlist/…` (a nyelvi előtagos hivatkozások is működnek)
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (a `www.youtube.com/playlist?list=…` hivatkozás is működik)
3. Válassz ellenőrzési intervallumot (15 perctől havonta egyszerig)
4. Kattints a **Lista figyelése** gombra

Minden fülnek saját mezője van. Egy előadóhivatkozás beillesztése a Lejátszási listák fülre (vagy lejátszásilista-hivatkozásé az Előadókhoz) nem ad hozzá semmit: az oldal megmondja, milyen hivatkozás, és felajánlja, hogy áthelyezi a megfelelő fülre.

A figyelést egy lejátszási lista oldaláról is elindíthatod: illeszd be a hivatkozását a keresősávba, és használd az **Új számok figyelése** (vagy egy YouTube Music-előadónál az **Új kiadások figyelése**) lehetőséget. A Könyvtárban lévő letöltött lejátszási listák ugyanezt a műveletet kínálják a **⋯** menüjükben. Az így hozzáadott figyelések 6 órás intervallumot használnak — módosítsd a Figyelő oldalon.

## Deezer-lejátszási listák

A nyilvános Deezer-lejátszási listák ugyanúgy figyelhetők, mint a többi: illeszd be a linket a **Lejátszási listák** fülön, használd az **Új számok figyelése** gombot a lista oldalán, vagy válaszd az **Új számok figyelése** pontot egy lejátszásilista-kártya **⋯** menüjében a [Toplisták](charts.md) oldalon. Nem kell Deezer-fiók, és a lista minden száma lekérődik, bármilyen hosszú is. A számok a [hangforrásaidból](download-settings.md) töltődnek le, mint bármely más Deezer-link esetén, és a lista megkapja az M3U-fájlját, a borítóját és a könyvtárbeli bejegyzését, ahogy egy Spotify-lista is — a Könyvtár akkor is számon tartja, mely számok tartoznak hozzá, ha az M3U-fájlok ki vannak kapcsolva. Csak nyilvános listák figyelhetők, és egy Deezer-**előadó** linkje letölthető, de nem figyelhető.

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
A Spotify nyilvános embedje megadja egy előadó nevét és a legnépszerűbb számainak előnézetét, de a diszkográfiáját **nem** — ennek olvasásához Spotify API-hitelesítő adatok kellenének, amelyeket a Downtify szándékosan nem használ. Így egy Spotify-előadóhivatkozás a nevére oldódik fel, és ugyanazzal az előadóval egyeztetődik a YouTube Musicon, ahonnan a hang is jön. Az előny: minden kiadvány, amelyet a Downtify lát, olyan, amelyet ténylegesen le is tud tölteni. A kompromisszum: a hivatkozás a pontosan ilyen nevű YouTube Music-előadót követi (a kis- és nagybetűktől és az írásjelektől eltekintve), több azonos nevű esetén a YouTube Music legjobb találatát. Gyakori névnél ellenőrizd, hogy a figyelés az az előadó-e, akit szántál, és ha nem, illeszd be közvetlenül a YouTube Music-előadó URL-jét. Egy Spotify-előadót, akinek pontos nevét egyetlen YouTube Music-előadó sem viseli, csak így lehet hozzáadni: a Downtify nem találgat.
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

### Javasolt előadók

Az előadófigyelések listája alatt az **Előadók** fül követhető előadókat javasol, két listában:

| Lista | Kik vannak benne |
|-------|------------------|
| **A hallgatásaid alapján** | Az előadók, akiket a legtöbbet hallgatsz: a saját lejátszásaid, amelyeket a [Felfedezés](discover.md) számol. A friss lejátszások többet számítanak: egy lejátszás súlya 45 naponta a felére csökken, így egy tavaly sokat hallgatott előadó lejjebb kerül annál, akit most minden nap hallgatsz. |
| **A könyvtárad alapján** | Az előadók az általad látott könyvtárban, a legtöbb szám, majd album szerint. |

A már figyelt előadók (a szüneteltetett figyelések is) és az olyan válogatásnevek, mint a **Various Artists**, kimaradnak. Minden lista egyszerre 20 előadót mutat; a **Több megjelenítése** betölti a következőket. A listák csak a tieid, adminként is: egy másik fiók lejátszásai sosem jelennek meg. Egy előadó, akit egy admin elrejtett a felhasználók elől, kimarad a felhasználó listáiból, ahogy a Könyvtárából is.

A listák betöltése semmit sem keres. A **Követés** megkeresi a nevet a YouTube Musicon, ahol egy előadófigyelés az előadót követi:

- ha ott pontosan egy előadónak ez a neve, a figyelés azonnal létrejön, a fenti mezőben beállított intervallummal és **Letöltés** / **Csak új kiadások** beállításokkal;
- különben (névrokonok, vagy egyetlen előadónak sem pontosan ez a neve) egy ablak mutatja a talált YouTube Music-előadókat, mindegyiket a fotójával és a profiljára mutató linkkel. Válassz egyet az **Előadó követése** gombbal, vagy a **Link beillesztése** gombbal illeszd be magad az előadó linkjét a fenti mezőbe.

A javaslatok csak azt választják ki, melyik előadót figyeld: a számok továbbra is a szokásos módon, a [hangforrásaidból](download-settings.md) töltődnek le.

### Egy előadó oldaláról a Könyvtárban

Egy előadó oldalán a Könyvtárban (`/library/artist`) van egy **Előadó figyelése** gomb, így követhetsz egy előadót, akitől már van zenéd, anélkül hogy kikeresnéd a linkjét. Ugyanúgy keresi meg a nevet a YouTube Musicon, mint a fenti **Követés**:

- ha ott pontosan egy előadónak ez a neve, a figyelés azonnal létrejön. Naponta ellenőrződik, és be van kapcsolva a **Csak új kiadások**, hiszen a korábbi zenéi már megvannak a könyvtárban;
- különben (névrokonok, egyetlen előadónak sem pontosan ez a neve, vagy a keresés nem sikerült) egy ablak mutatja a talált YouTube Music-előadókat, mindegyiket a fotójával és a profiljára mutató linkkel, valamint egy mezőt egy Spotify- vagy YouTube Music-előadó linkjének. A fenti **Letöltés** és **Csak új kiadások** beállítások arra vonatkoznak, akit követsz.

Amint a szerver létrehozta a figyelést, a gomb a **Figyelő** oldalra mutató linkké válik, ahol az intervallumot és a beállításokat módosíthatod; ha a szerver elutasítja (például mert az előadót már figyeled), az az ablakban jelenik meg. [Csak könyvtár módban](library-only.md) és a **Various Artists** oldalon nem jelenik meg.

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
- Egy sáv arról, hány szám érkezett a választott időszakban (**7 nap**, **30 nap** vagy **90 nap**), és az összes figyelésre nézve hány számot tartanak, mennyi helyet foglalnak (**A lemezen**) és hány van **Több figyelésben** — lásd [Aktivitás és tárhely figyelésenként](#activity-and-storage-per-watch)

Minden soron:

- **Aktív** kapcsoló — a figyelés szüneteltetése vagy folytatása eltávolítás nélkül
- **Ellenőrzések** — milyen gyakran ellenőrzik
- **Ellenőrzés most** (↻) — azonnali ellenőrzés, az ütemezésen kívül
- **Aktivitás** — az új számok a választott időszakban, a heti átlag, és hogy ez a tempó nő vagy csökken; kattints rá a figyelés saját oldalához
- **Tárhely** — a csak ebben a figyelésben lévő számok helye, és hogy hányat oszt meg más figyelésekkel
- **Szerkesztés** (✎) — a figyelés hivatkozásának, intervallumának és aktív állapotának megtekintése és módosítása (lásd: [Figyelés szerkesztése](#editing-a-watch))
- **⋯** — **Aktivitás és számok** (a figyelés saját oldala), szüneteltetés/folytatás, a hivatkozás másolása, az eredeti megnyitása, vagy **Figyelés leállítása** (a bejegyzés törlődik; a letöltött fájlok megmaradnak)

Az **Aktivitás** és a **Tárhely** ugyanolyan oszlop, mint a többi: az **Oszlopok** alatt elrejtheted vagy átméretezheted őket.

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
| Legutóbbi aktivitás | Új számok a választott időszakban |
| Átlagos tempó | Új számok naponta az időszakban |
| Tárhely növekedése | Az időszak új számainak helye |
| Saját tárhely | Azoknak a számoknak a helye, amelyek más figyelésben nincsenek |
| Letöltött számok | A lemezen lévő számok, amelyeket maga a figyelés töltött le |

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
- Minden szám, amelyet egy figyelés hozzáadott (`watch_events`): mikor, a fájl, melyik hangszolgáltató szerezte be, a figyelés letöltötte-e vagy már a könyvtárban találta, és az első ellenőrzésével jött-e. Ezek a sorok megőrzik a figyelés azonosítóját, nevét és tulajdonosát, ahogy akkor voltak, és túlélik a figyelést: leállítása vagy átirányítása után is megmaradnak, így a számai továbbra is megmondják, honnan jöttek
- Azok a számok, amelyeket egy figyelés továbbra sem tud letölteni (`watch_failures`), amíg az egyik sikerül, kikerül a listából, vagy a figyelést átirányítják

Az Előadófigyelés előtt létrehozott adatbázisok indításkor automatikusan migrálódnak; a meglévő sorok lejátszásilista-figyelésként működnek tovább. A fenti előzmény előtt rögzített számok az első indításkor egyszer bekerülnek ide ismeretlen eredménnyel (**A rögzítés előtt**) — a figyelés első napjáról származók az első ellenőrzéséhez számítanak.

## Aktivitás és tárhely figyelésenként

A figyelő oldala és minden figyelés saját oldala (**Aktivitás és számok** a figyelés **⋯** menüjében, vagy kattintás az **Aktivitás** oszlopára) megmutatja, mely figyelések növelik a könyvtáradat — hasznos sok figyelés esetén, vagy ha ki akarod deríteni, miért hozott egy generált mix váratlan számokat.

**Mi számít aktivitásnak.** Csak azok a számok számítanak, amelyeket egy figyelés ténylegesen hozzáadott: amelyeket letöltött. Azok, amelyeket már a könyvtáradban talált (egy másik figyelés vagy a saját letöltésed már tartalmazta), külön számítanak **Már a könyvtárban** néven, ahogy az első ellenőrzés hozama is, amikor letölt mindent, ami a listán már rajta volt. Így egy statikus lista tétlennek látszik, még ha az első ellenőrzése 300 számot töltött is le, egy hetente 15 számot hozzáadó mix pedig heti 15-öt mutat. Az előzmény vezetése előtt rögzített számok hozzáadottnak számítanak, és az oldal megmondja, hány ilyen van.

A választott időszakban (7, 30 vagy 90 nap, a böngésző megjegyzi) egy figyelés ezt mutatja:

| Szám | Mi ez |
|--------|------------|
| Új számok | Az időszakban hozzáadott számok |
| Naponta / Hetente / Havonta | Az átlagos tempó az időszakban — vagy a figyelés kezdete óta, ha az későbbi |
| Trend | A tempó nő (**Mostanában többet ad hozzá**), csökken (**Mostanában kevesebbet ad hozzá**) vagy egyenletes, a napi (7 nap) vagy heti (30 és 90 nap) új számok alapján; **Még túl új**, amíg háromnál kevesebb van belőlük az összevetéshez |
| Tárhely növekedése | Az időszak új számainak helye, amelyek még a lemezen vannak |

**Tárhely.** Egy fájl egyszer tárolódik, akárhány figyelés tartalmazza, és a számok ezt mutatják: a **Csak ebben a figyelésben** azoknak a számoknak a helye, amelyek más figyelésben nincsenek (ennyi szabadulna fel, ha leállítanád a figyelést és törölnéd a számait), a **Közös** azok a számok, amelyek más figyelésekben is megvannak, a figyelő oldalának sávja pedig minden fájlt egyszer számol. Más fiókok figyelései beleszámítanak abba, hogy egy fájl közös-e, de név szerint nem jelennek meg.

Egy figyelés oldala ezeket is mutatja:

- **Számok a lemezen**, **Általa letöltve**, **Már a könyvtárban** és **Sikertelen** — hogyan kerültek oda a számai, és hány nem töltődik le újra meg újra (lejjebb felsorolva, a próbálkozások számával és az utolsó hibával)
- **Honnan jött a hanganyag** — YouTube Music, YouTube, Soulseek (slskd) vagy Deemix, a lemezen lévő számonként
- **Számok ebből a figyelésből** — minden szám, amit tartalmaz, a legújabbak elöl, azokkal együtt, amelyek azóta kikerültek a listából, szűrőkkel (**Elmúlt 30 nap** — vagy a választott időszak —, **Általa letöltve**, **Már a könyvtárban**, **A rögzítés előtt**). Jelölj ki számokat a lejátszáshoz, sorba állításhoz, listához adáshoz, ZIP-ként letöltéshez vagy törléshez — például hogy kitakarítsd, amit egy mix az elmúlt héten hozott
- **Megnyitás a könyvtárban** (a lista oldala, előadófigyelésnél az előadóé), **Eredeti megnyitása** és **Ellenőrzés most**

A figyelés azonosítója (`#12`) a neve mellett látszik, így ugyanannak a linknek két figyelése — például két fiók, amely ugyanazt a listát követi — megkülönböztethető.

## Honnan jött egy szám

A szám menüjében (bárhol a könyvtárban) a **Honnan jött** megmondja, melyik figyelés töltötte le először, mikor és melyik szolgáltatóval — **Első ellenőrzés**, ha az első ellenőrzéssel jött —, és felsorolja az összes figyelést, amely most tartalmazza, mindegyiket az azonosítójával, a tulajdonosával (adminnak), azzal, hogy mikor kapta meg a számot, és hogyan: **Letöltötte**, **Már a könyvtárban** vagy **A rögzítés előtt**. Ez egyetlen fájl: a számot megosztó figyelések mind ugyanarra a példányra mutatnak.

Innen az **Aktivitás és számok** a figyelés oldalát nyitja meg, a **Megnyitás a könyvtárban** pedig a listáját. A leállított vagy már más linket követő figyelés továbbra is az általa letöltött számok forrásaként jelenik meg. Az előzmény előtt rögzített számnál az első figyelés látszik, amely rögzítette, **Valószínűleg** jelöléssel. Egy szám, amelyet egyik figyelés sem töltött le (te töltötted le), ezt jelzi.

Egy felhasználó a saját figyeléseit név szerint látja; egy másik fiók figyelése által letöltött szám csak ennyit árul el, és hogy mikor.
