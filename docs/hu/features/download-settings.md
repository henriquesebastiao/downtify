---
icon: lucide/sliders-horizontal
---

# Letöltési beállítások

Nyisd meg a **Beállítások** oldalt az oldalsávról (telefonon: **Továbbiak → Beállítások**). Az oldal szakaszokra oszlik — Általános, Hangforrások, Letöltések és fájlok, Címkék és dalszövegek, Navidrome, Könyvtár és Névjegy. A módosítások addig függőben maradnak, amíg meg nem nyomod a lent megjelenő sávban a **Változások mentése** gombot; mentetlen módosításokkal az oldalt elhagyva előbb rákérdez. A beállítások lemezre mentődnek, és túlélik a konténer újraindításait.

## Formátum

| Formátum | Kiterjesztés | Megjegyzések |
|--------|-----------|-------|
| MP3 | `.mp3` | Alapértelmezett. Univerzális kompatibilitás. |
| FLAC | `.flac` | Veszteségmentes. A bitráta beállítása figyelmen kívül marad. |
| M4A | `.m4a` | AAC MPEG-4 konténerben. Jó Apple-eszközökhöz. |
| OGG | `.ogg` | Ogg Vorbis. Nyílt formátum, jó minőség/méret arány. |
| OPUS | `.opus` | A legjobb tömörítés alacsony bitrátáknál. |

## Bitráta

Veszteséges formátumoknál (MP3, M4A, OGG, OPUS) érhető el. A FLAC figyelmen kívül hagyja ezt a beállítást.

| Opció | Kbps |
|--------|------|
| Alacsony | 128 |
| Közepes | 192 |
| Magas | 256 |
| Legjobb | **320** (alapértelmezett) |

A letöltött hang minden veszteséges formátumnál a választott bitrátán kódolódik. Ha a YouTube által szolgáltatott hang már a célkodekkel rendelkezik nagyjából azon a bitrátán (pl. a ~128 kbps AAC-adatfolyam az **M4A @ 128** esetén), akkor változatlanul megmarad az újrakódolás helyett, mert az újrakódolás csak minőséget veszítene.

::: info A magasabb bitráta nem ad hozzá minőséget
A YouTube hangja legfeljebb nagyjából **128–160 kbps**-ig terjed (AAC vagy Opus), a Downtify pedig mindig a legjobb elérhető adatfolyamot tölti le. 256 vagy 320 kbps-en kódolva nagyobb fájlokat kapsz, amelyek hűen megőrzik azt a forrást, de nem tudnak olyan részletet visszahozni, ami a forrásban sosem volt. Válassz alacsonyabb bitrátát, ha a fájlméret fontosabb.
:::

## Kimeneti fájlnév-sablon

Az alapértelmezett fájlnév-sablon:

```
{artists} - {title}
```

Ez olyan fájlneveket hoz létre, mint a `The Night Owls - Do I Still Recall.mp3`.

Elérhető tokenek:

| Token | Leírás |
|-------|-------------|
| `{title}` | A szám címe |
| `{artists}` | Vesszővel elválasztott előadónevek |
| `{album}` | Az album neve |
| `{tracknumber}` | A szám helye az albumán, 2 számjegyre nullákkal kiegészítve (pl. `01`, `12`). Üres, ha a forrásnak nincs számsorszáma (pl. szabad szöveges/YouTube-keresési találat). |
| `{year}` | Megjelenés éve (pl. `2025`). Üres, ha a forrásnak nincs megjelenési dátuma (pl. szabad szöveges/YouTube-keresési találat). |

A sablon `/` jelet is tartalmazhat almappák létrehozásához. Például egy könyvtár `Előadó/Album (2025)/01 - Cím.mp3` elrendezéséhez — hasznos egy teljes diszkográfia letöltésekor, mert minden album a saját mappájába kerül a megjelenési évével együtt:

```
{artists}/{album} ({year})/{tracknumber} - {title}
```

::: info
Ez független az alábbi **Rendezés előadó szerint** / **Rendezés album szerint** kapcsolóktól — azok a lejátszási lista-/albumletöltéseket közös előadónkénti vagy albumonkénti mappákba irányítják a teljes könyvtárban. A `{tracknumber}` és a `{year}` csak azt teszik lehetővé, hogy egy, a fentihez hasonló sablon ugyanezt az elrendezést kézzel, számonként felépítse, e kapcsolók bekapcsolása nélkül.
:::

## Párhuzamos letöltések

Azt szabályozza, hány dal tölt le egyszerre. Válassz egy előbeállítást (1, 2, 3, 5, 8), vagy írj be bármilyen egyéni értéket **1 és 30** között a mellettük lévő számmezőbe.

| Érték | Viselkedés |
|-------|-----------|
| **1** | Egymás után — egyszerre egy dal (a legbiztonságosabb, legkisebb erőforrás-használat) |
| **3** | Alapértelmezett. Jó egyensúly a sebesség és a stabilitás között. |
| **8** | Gyorsabb nagy lejátszási listáknál |
| **legfeljebb 30** | Nagyon gyors kapcsolatokhoz a legjobb; több CPU-t és sávszélességet használ, és növeli az esélyét, hogy a YouTube korlátozza a kéréseidet. |

A korlát minden kötegelt letöltésre vonatkozik — lejátszási lista-/albumletöltések, a kötegelt sorvégpont és a CSV [könyvtárimportok](library-import.md) —, valamint a **[Meglévő zenei mappák](external-library.md)** szinkronizálási lekérdezéseire (dalszövegek, borítók, műfaj). **Nem** vonatkozik a Lejátszási lista figyelő átfésüléseire, amelyek az új számokat egyesével töltik le. Ennek az értéknek a módosítása a Beállításokban újraindítás nélkül azonnal érvénybe lép; a szerver az `1–30` tartományon kívüli értékeket a tartományba szorítja.

## Szünet a letöltések között

Azt éri el, hogy a Downtify egy dal befejezése után beállítható számú másodpercet várjon a következő megkezdése előtt, ahelyett hogy egymás után sorozatban lőné ki a kéréseket.

| Érték | Viselkedés |
|-------|-----------|
| **0** | Alapértelmezett — ki, nincs késleltetés. |
| **5 / 15 / 30 / 60** | Előbeállítások, vagy írj be bármilyen egyéni értéket **0 és 300 másodperc** között. |

Vonatkozik a lejátszási lista-, album- és kötegelt letöltésekre, a CSV [könyvtárimportokra](library-import.md) és a Lejátszási lista figyelő automatikus átfésüléseire. Kimarad egyetlen kézi számletöltésnél (nincs „következő” dal, amire várni kellene), és minden köteg *utolsó* száma után is, hogy egy futás ne záruljon értelmetlen várakozással.

Alacsonyabb **Párhuzamos letöltések** értékkel kombinálva ez a fő eszköz a YouTube sebességkorlátozásának elkerülésére, amikor egy nagy lejátszási listát vagy importált könyvtárat felügyelet nélkül töltesz le.

## Szünet a szinkronizálás között

Ugyanaz az ötlet, de a **[Meglévő zenei mappákra](external-library.md)** és nem a letöltésekre. A szinkronizálás a dalszövegeket, a hiányzó borítókat és a műfajt **[Párhuzamos letöltések](#parallel-downloads)** számú szám csoportjaiban keresi, majd annyi másodpercet vár a következő csoport előtt. Alapértelmezetten **0** (a lekérdezések továbbra is egyszerre futnak, a Párhuzamos letöltések továbbra is korlátozza őket). Nagy gyűjteménynél használj néhány másodpercet, hogy az LRCLIB, a borítóforrások és az iTunes ne kapjon mindent egyszerre.

## Borítók letöltése

Azt szabályozza, hogy a Downtify beágyaz-e egyáltalán albumborítót. Alapértelmezetten be van kapcsolva. Kapcsold ki, hogy teljesen kihagyja a borítók lekérését — az összes többi címke (cím, előadó, album, év, dalszöveg) továbbra is normálisan beágyazódik, de a fájlok kisebbek lesznek és kicsit gyorsabban töltődnek le, mert a borítóképet soha nem kéri le és nem írja ki.

Ennek kikapcsolása azt a különálló `cover.jpg` fájlt is kihagyja, amelyet a *Rendezés album szerint* opció (lásd: [Fájlszervezés](file-organization.md)) hoz létre, és a [lejátszó](player.md)/könyvtár nem mutat borítót az így letöltött számokhoz (helyette a tartalék hangjegy ikon látszik).

Ezt a `cover.jpg` fájlt az albummappa összes száma megosztja. Egy szám törlése a Könyvtár oldalról ezt is törli, de csak akkor, ha az a mappában maradt **utolsó** szám — amíg ugyanazon album másik száma még ott van, a borító marad.

## Borító felbontása

Csak akkor számít, ha a **Borítók letöltése** (fent) be van kapcsolva. Beállítja a célméretet (szélesség és magasság, pixelben), amelyet a Downtify a **YouTube Music** vagy a **Deezer** forrású beágyazott borítóhoz kér. Válassz egy előbeállítást (300, 600, 800, 1000, 1200), vagy húzd a csúszkát **300 és 1200** között bárhová; a jelenlegi érték pixelben mellette látszik. Az alapértelmezett 600.

Hasznos, ha a könyvtáradat olyan médiaszerverbe táplálod, mint a Plex, amely a borítókat nagyobb felbontásban jeleníti meg, mint amit a Downtify alapból beágyaz.

A két forrás eltérően alkalmazza a beállítást, mivel csak az egyiket lehet ténylegesen igény szerint átméretezni:

- A **YouTube Music** bélyegképei az URL szerkesztésével átméretezhetők — az élő CDN-en ellenőrizve a magasabb előbeállítások a legtöbb albumborítónál valóban több részletet adnak (nem csak felskálázást), egészen a forráskép saját felbontásáig.
- A **Deezer** bármely szám, album, előadó vagy lejátszási lista borítójához csak négy fix méretet kínál (56, 250, 500 és 1000 px) — nincs köztes méret, amit kérni lehetne. A Downtify a négy közül a legkisebbet választja, amely még legalább akkora, mint a beállított érték (300 px kérésére az 500 px-eset kapod, mert nincs pontosan 300 px-es méret); 1000 px-nél többet kérve is az 1000 px-es jön, a Deezer legnagyobbja.

::: info A Spotify-forrású borítókat ez nem érinti
A Downtify már a **legnagyobb** borítót beágyazza, amit a Spotify nyilvános embed API-ja a Spotify által feloldott számokhoz/albumokhoz/lejátszási listákhoz kínál — nincs nagyobb méret, amit kérni lehetne. Ez a beállítás csak a YouTube Musicon keresztül feloldott számoknál (szabad szöveges keresés, YouTube URL-ek, és minden Spotify-szám, amelyet a tényleges hanghoz újra a YouTube Musichoz társítottak), illetve a Deezeren át feloldottaknál (beillesztett Deezer-hivatkozás vagy egy szám a [Listák](charts.md) közül) emeli a plafont.
:::

Ennek az értéknek a módosítása a Beállításokban azonnal érvénybe lép, a jelenleg megnyitott keresőoldalra is — nem kell újra letölteni semmit, ami már a lemezen van.

## Meglévő fájlok felülírása

Alapértelmezetten be van kapcsolva, a Downtify korábbi viselkedésének megfelelően: minden letöltés végigmegy a folyamaton (hang lekérése, címkézés, borító, dalszöveg), és felülírja azt, ami már a kiszámított kimeneti útvonalon van.

### Mit jelent valójában az „újra”

Bekapcsolva az újralétöltés **teljesen új futás**, nem a meglévő fájl javítása. A Downtify nem nézi meg, mid van már: a beállított sorrendben végigkeresi a [hangforrásaidat](#audio-provider) — tehát ha a slskd az első, először a slskd-t próbálja, nem csak tartalékként —, a hangot attól a forrástól kéri le, amelyik válaszol, és ráírja a mai címkéket, borítót és dalszövegeket.

Ennek van egy következménye, amit érdemes tudni, mielőtt egy nagy könyvtárat újra letöltesz:

::: warning Eltérő formátum esetén a régi fájl ott marad
Az új fájl abba az útvonalra íródik, amelyet a [fájlnév-sablon](#output-filename-template) előállít, az **új** hang kiterjesztésével. A Downtify a régi fájlt csak akkor írja felül, ha mindkettő ugyanazzal a kiterjesztéssel végződik.

Tehát ha az `Előadó - Dal.mp3` újralétöltésekor a slskd FLAC-cel válaszol, **mindkettőt** megkapod: az `Előadó - Dal.mp3` (a régi, érintetlenül) és az `Előadó - Dal.flac` fájlt. Ha a [slskd-fájlok helyben hagyása](slskd-navidrome.md#leave-files-in-place) be van kapcsolva — ez az alapértelmezés —, a slskd-fájl még a letöltési mappádba sem másolódik, így a régi pontosan ott marad, ahol volt, az új pedig a `slskd/` alatt él.

Semmi sem vész el, de duplikátumokat kapsz. Egy fájl tényleges lecseréléséhez lásd: [Hang cseréje](replace-audio.md), amely megtartja az útvonalat, a formátumot és a címkéket.
:::

### A borító a Spotifyból vagy a YouTube Musicból jön, nem a fájlból

Bármilyen grafikát is hordoz a letöltött hang — beleértve a slskd-fájlba ágyazott nagy felbontású borítót is —, azt a címkézés során **eldobja és lecseréli**. A Downtify mindig azt a borítót ágyazza be, amelyet a számhoz a Spotifyból vagy a YouTube Musicból kér le, az általad beállított [borító felbontásában](#cover-art-resolution) (alapértelmezetten 600 px). Ugyanez igaz a címre, az előadókra, az albumra és a többi címkére: a forrás saját címkéi nem maradnak meg.

Ha nagyobb borítót szeretnél a már meglévő fájlokra, az újralétöltés a hosszú út. A [Könyvtár feljavítása](library-upgrade.md) pontosan ezt teszi — minden fájl beágyazott borítóját összeveti a Spotifyéval, az iTunesével és a YouTube Musicéval, a legnagyobbat írja be, kitölti a hiányzó dalszövegeket és címkéket, és soha nem nyúl a hanghoz.

Kapcsold ki, hogy soha ne töltsön le olyan dalt, amely már a lemezen van. Ez leginkább lejátszási lista letöltésekor, [CSV-könyvtár](library-import.md) importálásakor vagy akkor számít, ha a [Lejátszási lista figyelő](playlist-monitor.md) olyan listákat szinkronizál, amelyek egymással vagy a könyvtárad meglévő dalaival közös számokat tartalmaznak — bekapcsolt opciónál minden ilyen duplikátum újra letöltődik.

Kikapcsolva a Downtify a dalt **a letöltési mappa bármely pontján** keresi, nem csak ott, ahová az új letöltés kerülne:

- a könyvtár gyökerében (egyedi számletöltések),
- bármelyik lejátszási lista mappájában (lejátszási lista-letöltések, CSV-importok, Lejátszási lista figyelő),
- egy előadó-/albummappában, vagy a *Rendezés előadó/album szerint* be- vagy kikapcsolása előtti lapos elrendezésben.

Egy dal akkor számít már letöltöttnek, ha egy hangfájl (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`) neve megegyezik azzal, amit a [kimeneti fájlnév-sablon](#output-filename-template) előállít hozzá, kis- és nagybetűket nem megkülönböztetve összehasonlítva. Egy magában maradt `.lrc` dalszövegfájl nem számít. Ha a sablon mappákat tartalmaz (pl. `{artists}/{title}`), azoknak a mappáknak is egyezniük kell, hogy egy másik előadó azonos című dala ne legyen összetévesztve ezzel. Mivel a fájlok nem hordoznak Spotify-/YouTube-szám azonosítót, az egyeztetés név alapján történik: egy átnevezett fájl vagy egy másik fájlnév-sablonnal mentett nem lesz felismerve.

Amikor egy dalt kihagy:

- Semmi sem kerül lekérésre: se hang, se borító, se dalszöveg, se újracímkézés. A Spotify-számoknál az ellenőrzés még a YouTube Music keresés előtt lefut, így a már letöltött dalok egyetlen keresési kérésbe sem kerülnek.
- A sor késznek mutatja a dalt, a lejátszási listák [M3U-fájljai](m3u-export.md) pedig a meglévő fájlra mutatnak, bárhol is van (pl. `../Előadó - Cím.mp3`), így a lejátszási lista továbbra is teljes egészében lejátszható.
- Ha ugyanazt a dalt egyszerre kétszer sorba állítják (kétszer szerepel egy listában, vagy két párhuzamosan letöltődő listában), csak egy példány töltődik le. A másik megvárja, majd kimarad.

## Hosszú számok

A **Beállítások → Letöltések és fájlok → Leghosszabb szám** a számhosszt a letöltésekre *és* a streamekre egyaránt korlátozza (alapértelmezés **10 perc**, a `0` mindent elfogad). A hosszabb dalokat elutasítja, mielőtt bármit lekérne, a *„… feletti számokat nem tölti le”* sorhibával — az órás mixek és feltöltések sosem azok, aminek egy könyvtári számnak lennie kellene. Ugyanez a korlát védi a streamelést is: egy hosszabb számot `400`-zal utasít el (azok a hívók, akik ismerik a hosszát, átadják a `duration` értéket, és a gyorsítótárazott fájlt amúgy is megvizsgálja), így a hosszú feltöltések a stream-gyorsítótárban sem halmozódnak fel. A már letöltött fájlokat és a podcast-epizódokat (amelyek rendszeresen hosszabbak) ez nem érinti.

## Hangszolgáltató

Az alapértelmezett hangszolgáltató a **YouTube Music**. A Downtify a [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) segítségével keresi a legjobb találatot a szám hosszának összevetésével. Ha a YouTube Musicnak nincs elfogadható találata, vagy csak olyan, amelynek hossza jócskán eltér (valószínűleg másik felvétel), a Downtify automatikusan a hagyományos YouTube-keresésre vált — lásd: [Hogyan működik](../how-it-works.md#fallback-to-standard-youtube).

A **Beállítások → Hangforrások** használhat csak hagyományos **YouTube**-ot vagy **slskd**-t (Soulseek) is rendezett tartaléklistaként — lásd: [slskd és Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Adott hangforrás kényszerítése

Ha a Downtify rossz YouTube Music videót választ (pl. feldolgozást az eredeti helyett), számonként felülbírálhatod:

**A opció — illessz be közvetlenül egy YouTube Music URL-t**

Illeszd be a `https://music.youtube.com/watch?v=…` címet (vagy egy hagyományos `youtube.com/watch?v=…` URL-t) a keresősávba, és nyomd meg a letöltést. A Downtify a hangot pontosan arról a videóról kéri le.

::: info
YouTube URL-lel letöltve a metaadatok (cím, előadó, borító) a YouTube-ról jönnek a Spotify helyett. Tiszta címkékhez használd a B opciót.
:::

**B opció — hang kényszerítése egy sikertelen számra**

1. A **Letöltési sorban** kattints a **Hangforrás kényszerítése** gombra egy sikertelen szám alatt.
2. Illessz be egy YouTube vagy YouTube Music URL-t a megjelenő mezőbe.
3. Nyomd meg az **Entert**, vagy kattints az **Alkalmaz** gombra.

A Downtify újra letölti a számot pontosan azzal a videóval, miközben megtartja az összes Spotify-metaadatot (cím, előadó, album, borító, dalszöveg).

## Beágyazott metaadatok

A Downtify a következő címkéket ágyazza be minden letöltött fájlba, formátumtól függetlenül:

| Címke | Forrás |
|-----|--------|
| Cím | Spotify embed |
| Előadó(k) | Spotify embed |
| Album | Spotify embed — egyedi számletöltésnél az az album, amelyet a szám nyilvános Spotify-oldala megnevez (maga a szám embedje nem tartalmaz ilyet) |
| Év | Spotify embed (számszintű lekérés) |
| Albumborító | Spotify embed (számszintű borító) a Spotify által feloldott számoknál; egyébként YouTube Music bélyegkép vagy Deezer-borító. Opcionális — lásd: [Borítók letöltése](#download-cover-art) és [Borító felbontása](#cover-art-resolution) |
| Dalszöveg | lrclib (ha engedélyezett) |
