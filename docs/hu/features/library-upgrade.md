---
icon: lucide/wand-sparkles
---

# Könyvtár feljavítása

Az idők során felépült könyvtár azt hordozza, amit a Downtify adott verziója egy szám letöltésekor tudott: a legkisebb borítót, amelyet egy forrás kínált, dalszöveg nélkül, album vagy év nélküli címkékkel. A **Könyvtár feljavítása** megnézi, mi van már a lemezen, és csak azt javítja, ami le van maradva — újbóli letöltés nélkül, és kézzel rendezendő semmivel.

Nyisd meg a **Könyvtár → Könyvtár feljavítása** oldalról.

::: info Az alapértelmezett feljavítások csak címkéket írnak újra
Az alapértelmezett mód **borítókat, dalszövegeket és címkéket** ír újra. Az opcionális [Deemix-csere](#deemix-recording-replacement) külön beolvasási mód, alapértelmezetten kikapcsolva. A [Hang cseréje](replace-audio.md) használatával kézzel választhatsz másik verziót.
:::

## Hogyan működik

1. **Beolvasás.** A Downtify beolvas minden könyvtári számot, és kategóriánként jelzi, mi van lemaradva. Semmi nem íródik ki.
2. **Választás.** Minden kategória, amelyhez a beolvasás talált valamit, a számok számával és egy kapcsolóval szerepel. Vedd ki a jelölést, amit nem akarsz.
3. **Feljavítás.** A kiválasztott számok egy sorba kerülnek, amelyet egyesével dolgoz fel. Szüneteltetheted, folytathatod vagy leállíthatod, és túléli az újraindítást.

## Mit javít

| Kategória | Mit csinál | Hol keres |
|---|---|---|
| **Borítók feljavítása** | Lecseréli a célméretnél kisebb borítót | Spotify, Apple Music (iTunes), YouTube Music |
| **Hiányzó dalszövegek pótlása** | Pótolja azoknak a daloknak a dalszövegét, amelyeknek nincs, beágyazva és `.lrc` kísérőfájlként | A [dalszöveg-szolgáltatóid](lyrics.md), a te sorrendedben |
| **Címkék frissítése** | Kitölti az albumot, albumelőadót, megjelenési dátumot és számsorszámot — beleértve azt az albumot, amely a régebbi egyedi számletöltésekből hiányzik | Spotify |

Egy szám akkor számít lemaradottnak, ha:

- a beágyazott borítója rövidebb oldala **kisebb a célméretnél** (a borító nélküli szám is számít);
- **sem** beágyazott dalszövege, **sem** `.lrc` kísérőfájlja nincs (a fájl mellett vagy a Beállítások dalszövegmappájában);
- a címkéiből hiányzik az **album**, az **albumelőadó**, az **év** vagy a **számsorszám**.

A **Címkék frissítése** csak olyan számokra működik, amelyekhez a Downtifynak még megvan a Spotify-számazonosítója — azokra, amelyeket Spotify-hivatkozásból töltött le, és a [számindexben](library-catalog.md#what-gets-stored) tart. A többi szám sorba kerül, de _Nincs tennivaló_ eredménnyel jön vissza.

## Beállítások

### Borítók feljavítása ez alatt

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Az ennél a méretnél nagyobb vagy ekkora borítókat békén hagyja. A Downtify csak olyan borítót ír ki, amely **szigorúan nagyobb** a fájlban lévőnél, így egy feljavítás kétszeri futtatása soha nem ír újra semmit feleslegesen.

Honnan jönnek a méretek:

| Forrás | Tipikus méret |
|---|---|
| **Apple Music (iTunes)** | 1200px és fölötte |
| **Spotify** | legfeljebb 640px |
| **YouTube Music** | a [borító felbontása](download-settings.md) beállításig, legfeljebb ~1200px |

Ezért ragad a korábban letöltött könyvtár is gyakran 300–640px-en: a Spotify a borítóit fix méretekben publikálja, és a legnagyobb, amit kínál, 640px.

### Borító forrása

| Választás | Viselkedés |
|---|---|
| **A legnagyobb elérhető felbontás** (alapértelmezett) | Minden forrást megkérdez, és a legnagyobb képet tartja meg |
| **A Spotify előnyben** / **Az Apple Music előnyben** / **A YouTube Music előnyben** | Azt a forrást használja, ha van nála bármi; a többiek csak tartalékok arra az esetre, ha nála nincs semmi |

### Egy szám ne legyen újra ellenőrizve ennyi ideig

`Mindig minden számot ellenőrizzen` · `7 nap` · **`30 nap`** · `90 nap` · `365 nap`

Miután egy számot megnéztek, a következő beolvasás ennyi ideig kihagyja, így egy nagy könyvtáron a második futás nem kérdezi meg újra ugyanazokat a forrásokat ugyanazokról a számokról.

A memória **számonként és kategóriánként** van vezetve, ami a részleges futásokat működtetni képes: 16 000 szám borítóinak javítása semmit nem mond arról, hogy valaha keresték-e a dalszövegeiket, így egy későbbi dalszöveg-futás továbbra is mindet figyelembe veszi. A beolvasás azokat a kategóriákat is rögzíti, amelyeket megvizsgált, és amelyeknél nem talált tennivalót — a megnézés és semmi találása is ellenőrzés, mint bármi más.

A Downtify minden számhoz és kategóriához megjegyzi: mikor ellenőrizték, melyik Downtify-verzió ellenőrizte, és — borítóknál — a legnagyobb talált borítót és azt, honnan jött. Hogy mely dalszöveg-szolgáltatóktól kérdeztek már, azt külön tárolja, dalonként és szolgáltatónként (lásd: [Dalszövegek](lyrics.md)).

Két dolog mindig felülírja:

- egy **újabb Downtify-verzió** mindent újra ellenőriz, mert jobban tud egyeztetni vagy címkézni, mint az előző;
- a **Mindig minden számot ellenőrizzen** választása figyelmen kívül hagyja a memóriát az adott beolvasásnál.

Amikor egy beolvasás azért nem talál tennivalót, _mert_ mindent nemrég ellenőriztek, ezt megmondja, és felajánlja az újrafuttatást a memória nélkül, ahelyett hogy megmagyarázatlan „nincs mit feljavítani” üzenettel hagyna.

## Futás közben

Az előrehaladás panel a sorból elkészült számokat, egy hozzávetőleges adatmennyiséget (`8.4 GB of 51.3 GB`) és azt mutatja, hány lett feljavítva, hánynál nem volt tennivaló, vagy hány hibázott. Minden szám megmutatja, mit csinál — _Azonosítás_, _Borító keresése_, _Dalszöveg keresése_, _Fájl írása_ — és azzal zárul, ami változott, pl. `artwork 1200px (itunes)`.

A **Szünet** a folyamatban lévő szám után megáll, és megtartja a sort. A **Leállítás** eldobja a többit; a már feljavított számok feljavítva maradnak. Elhagyhatod az oldalt — a futás megy tovább, és bármely másik megnyitott lap követi.

A sor a `/data/downtify_library.db` fájlban él, így **a Downtify (vagy a konténer) újraindítása futás közben ott folytatja**, ahol abbahagyta. Az a szám, amely folyamatban volt, amikor a folyamat leállt, visszakerül a sorba.

## Semmi nem vész el, ha egy feljavítás hibázik

Minden írás egy munkamásolatba megy az eredeti mellett (`<név>.downtify-upgrade.<kiterjesztés>`). A másolatnak azonos hosszúságú hangként meg kell nyílnia, mielőtt a helyére kerül; ha nem, eldobja, és az eredeti érintetlen marad. Ez a fájl soha nem jelenik meg önálló számként, és a szám befejezésekor eltűnik.

Az eredeti **módosítási idő megmarad**, így egy könyvtár feljavítása nem keveri újra a _Nemrég hozzáadva_ sorrendet.

### Csak olvasható zenemappák

Egy feljavítás helyben írja újra a címkéket, ezért a csak olvasható fájlrendszeren lévő számokat **kihagyja**, magyarázattal, még mielőtt metaadatot, borítót vagy dalszöveget keresne. Lejátszhatók maradnak, és a listáikban is; a fájljaik és a csatolási jogosultságaik változatlanok. Egy kihagyott csak olvasható számot nem jegyez meg sikeresen ellenőrzöttként, így újra figyelembe vehető, ha a mappája később írhatóvá válik. A váratlan jogosultsági, lemezterület- és I/O-hibák továbbra is hibaként jelennek meg.

Ez eltér a [meglévő mappák gazdagításától](external-library.md), amely a borítókat és dalszövegeket külön, a Downtify adatmappájában tarthatja a védett hangfájlok újraírása nélkül.

## Miért nem cseréli a hangot

A szokásos címkefeljavítások nem cserélik a hangot. Az alábbi külön mód pontos felvétel-metaadatot és megjelenési hivatkozást követel; a bizonytalan verziók kézi átvizsgálásra maradnak.

## Felvételek cseréje Deemixszel

A [Deemix-forrás](deemix.md) engedélyezése és tesztelése után a **Könyvtár feljavítása** a beolvasás előtt két független kapcsolót kínál:

- **Use verified Deemix recordings**: beolvassa az eredeti Downtify-letöltéseket, az egyik előnyben részesített külső gyűjtemény által elfedett másolatokat is. Pontosan egyezteti az előadót, a teljes címet/verziót és az albumot; elutasítja a félreérthető katalóguseredményeket. A régi klip hossza nem szolgál egy helyes katalógusfelvétel elutasítására. Ellenőrzi a letöltött címkéket, a katalógus hosszát, a választott minőséget és a teljes FFmpeg-dekódolást.
- **Remove old Downtify audio after import**: ezen felül a közzététel után eltávolít minden változatlan eredetit. Alapértelmezetten ki van kapcsolva. Az eredetik megtartása is frissíti a lejátszási listákat és a kedvenceket a Deemix-felvételre.

Ez a beolvasás borító-/dalszöveg-/címkefeladatok helyett egy **hang** kategóriát hoz létre. A kimeneti fájlok, a borító, az albumelrendezés és a natív dalszövegek a Deemix tulajdonában vannak. A Downtify helyben olvassa őket. A meglévő natív vagy beágyazott dalszövegek megmaradnak; csak a hiányzó dalszövegek pótolhatók egy írható, dedikált dalszövegmappában, a hang újraírása nélkül. A magasabb minőségű veszteségmentes eredeti megmarad, ha a Deemix MP3-ra van állítva.

A közzététel kötegenként egyszer történik. Az M3U-megjegyzések, a kézi jelölők és a számsorrend megmaradnak, majd a katalógusútvonalak, a lejátszásilista-tagságok, minden felhasználó kedvelései, a tulajdonlás és az elrejtett számok szabályai egyetlen SQLite-tranzakcióban költöznek. A régi fájlok gyorsítótárazott Navidrome-azonosítói érvénytelenné válnak egy friss natív keresésért. A már kiadott mobilazonosítók és a régi lejátszási URL-ek csak olvasható aliasokat tartanak a regisztrált cseréhez; a módosítások soha nem használják ezeket az URL-aliasokat.

A könyvtáradatbázisban lévő tartós visszaigazolások rögzítik a forrás/cél SHA-256-értékeit és a közzététel állapotát. A források megmaradnak, amíg a csere és a hivatkozások ellenőrzése meg nem történik. Egy megváltozott vagy hiányzó csatolás, szerkesztett fájl, külső csak olvasható lejátszási lista-hivatkozás, aktív lejátszás vagy sikertelen katalógus-közzététel látható indokkal megállítja a takarítást. A szünet/folytatás és az újraindítás újrahasználja a visszaigazolásokat. Nincs általános duplikátum-átfésülés vagy kor alapú takarítás: csak a Downtify letöltési mappájában lévő ellenőrzött eredetik jöhetnek szóba. A kézi Deemix-/slskd-letöltések, a külső eredetik, a könyvtárak és a kísérőfájlok soha nem törlődnek. Miután egy eredetit eltávolítottak, a konténer visszaállítása nem állítja vissza azt a fájlt; szükség esetén állítsd vissza a saját tároló-biztonsági mentésedből.

Azoknak a NAS-felhasználóknak, akiknél a csatolási nevek eltérnek a Docker-útvonalaktól, egy adminisztrátor beállíthatja a `DOWNTIFY_DEEMIX_M3U_ROOT` értéket egy konténeraliasra, amely a Deemix gyökerére mutat. A relatív M3U-útvonalak ezt az aliast használják (például a `/music/existing` útvonalra leképezett `/Download`). Az opcionális `DOWNTIFY_LIBRARY_READY_MARKERS` jelölőútvonalak és várt szöveg JSON-objektuma, amelyet az előkészítés és a takarítás előtt ellenőriz. Egy hiányzó jelölő biztonsági okból hibával végződik. Az alapértelmezett módhoz egyik változó sem szükséges.

A beolvasási API elfogadja a `replace_audio_deemix: true` értéket, opcionálisan a `delete_replaced_audio: true` értéket, és opcionálisan a `files: ["relative/original.mp3"]` értéket egy korlátozott kísérleti futáshoz. Ennek a beolvasásnak az indítása a `categories: ["audio"]` értéket választja. A futás állapota tartalmazza a csere számait és egy `finalization_error` mezőt, amikor a közzététel szünetel. Egyetlen forrásfájl sem törlődik pusztán azért, mert egy Deemix-sorelem „kész”-et mond.

### Bizonytalan felvétel átnézése

Egy kihagyott vagy sikertelen hangfeladat felkínálja a **Choose a Deezer recording** lehetőséget. Illessz be egy pontos számhivatkozást, nézd meg az előadóját, albumát és hosszát, majd válaszd az **Analyze this choice** lehetőséget. Ez csak egy új egyszámos beolvasást készít elő; a csere indításához erősítsd meg azt a beolvasást. Az alapértelmezett automatikus egyeztető soha nem találgat más albumot.

Ez a kifejezett választás kijavíthat egy régi albumcímkét, de a teljes címnek/verziónak és az előadónak továbbra is egyeznie kell. Egy ismert explicit eredeti nem válhat csendben tisztított verzióvá. A választott felvétel ugyanazokon a hossz-, minőség-, dekódolás-, hivatkozás- és törlésellenőrzéseken megy át. Egy eltérő választás nem használhatja újra csendben egy már előkészített visszaigazolást. A haladó beolvasási adat a választást `deemix_recordings: {"relative/original.mp3": "123456"}` formában rögzíti; ehhez a fájlhoz van kötve, és az újraindítás/folytatás miatt mentődik.

## API

| Metódus | Útvonal | Leírás |
|---|---|---|
| `GET` | `/api/library/upgrade` | A futás állapota, a sor számai és amit a beolvasás talált |
| `GET` | `/api/library/upgrade/jobs` | Számonkénti sorok (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Beolvassa a könyvtárat; nem ír semmit |
| `POST` | `/api/library/upgrade/start` | Elindítja a futást a kiválasztott `categories` kategóriákra |
| `POST` | `/api/library/upgrade/pause` | Az aktuális szám után megáll, megtartja a sort |
| `POST` | `/api/library/upgrade/resume` | Folytat egy szüneteltetett futást |
| `POST` | `/api/library/upgrade/cancel` | Eldobja a sor többi részét |

Az előrehaladást a [WebSocketen](../api-reference.md#websocket) is küldi `{"type": "library_upgrade", "upgrade": {…}}` formában.

A kérések és válaszok alakjáért lásd az [API-referenciát](../api-reference.md#library).
