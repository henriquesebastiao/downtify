---
icon: lucide/image
---

# Előadófotó, banner és életrajz

A Downtify a Könyvtárad minden előadójához megjeleníthet valódi profilfotót, bannert és életrajzot – generált kezdőbetű és szöveg nélküli állapot helyett. Ez magától kitöltődik, amikor először nyitod meg egy új előadó oldalát, vagy amint az egyik száma letöltődött; ezután te választasz másik fotót/bannert, kéred le újra, vagy írod meg a saját életrajzodat, és töltöd ki kézzel a közösségi linkeket.

A szerkesztés a Könyvtár minden előadójának oldalán mindig elérhető, anélkül hogy előbb be kellene kapcsolnod bármilyen beállítást.

::: info Az „Előadófotók automatikus beszerzése” / „Előadóbannerek automatikus beszerzése” a Beállításokban
**Beállítások → Letöltések és fájlok → Előadófotók automatikus beszerzése / Előadóbannerek automatikus beszerzése** dönti el, hogy a Downtify magától elmentheti-e egy előadó fotóját/bannerét – ez akkor történik, amikor először megnyitod egy előadó oldalát, és amikor az egyik száma letöltődik (lásd [Amikor először nyitsz meg egy új előadót](#the-first-time-you-open-a-new-artist) és [Amikor egy letöltés befejeződik](#when-a-download-finishes)). A fotók alapból be vannak kapcsolva, a bannerek ki. Soha nem korlátozzák a szerkesztőablakot: mindig kiválaszthatsz kézzel fotót vagy bannert, bármit mondanak is.
:::

## A szerkesztőablak

**Ha egy előadónak van bannere, a kerek fotója el van rejtve az oldal fejlécében** – a banner egyedül is általában elég, és mindkettő megjelenítése zsúfoltnak hatott. A fotó azonban nem tűnt el: még mindig ott van szerkesztésre, egy fül távolságra.

Egy előadó oldalán a Könyvtárban (`/library/artist?name=…`) vidd az egeret a kerek fotó fölé (ha megjelenik) a **Fotó szerkesztése** gombért, vagy a bannerterület fölé az **Előadó szerkesztése** gombért – mindkettő ugyanazt az ablakot nyitja: felül az előadó jelenlegi fotója, alatta négyfüles menü. Attól függően nyílik a **Profil** vagy a **Banner** fülön, melyik gombra kattintottál (alapból **Banner**, mivel a fotó nem mindig látható a kattintáshoz).

- **Profil** / **Banner** – képet mindkettőben ugyanúgy választasz:
  - **Keresés név szerint** – a YouTube Music és a Deezer között keres egyező előadófotót (azok a Deezer-előadók, akiknek csak az általános helyettesítő képük van, kimaradnak). Írj be mást, hogy más nevet keress, vagy egy közvetlen `http(s)://` képlinket, hogy különálló jelöltként használd.
  - **Feltöltés az eszközről** – bármilyen képfájl.
  - **Fotó eltávolítása / Banner eltávolítása** – csak akkor jelenik meg, ha az aktív fül képe el van mentve; megerősítést kér, majd törli a kísérőfájlt (sidecar).

  Minden keresési találati kártyán jelvény mutatja, honnan jött. Egy kiválasztása azonnal letölti és elmenti. Az a kártya, amelynek a képe jelenleg el van mentve, zöld kerettel és pipával van megjelölve, a Profil és a Banner fülön külön – így egy pillantással látod, melyik jelöltet használod. A feltöltött fotónak, vagy annak, amelyet még azelőtt mentettek el, hogy a Downtify megjegyezte volna, nincs megjelölhető kártyája.
- **Életrajz** – egyszerű szövegmező a jelenleg mentett életrajzzal (üres, ha nincs), hogy magad írd meg vagy szerkeszd. A Mentés közvetlenül felülírja a jelenlegi szöveget. A mező feletti ⚡ **Életrajz lekérése a Streamsből** gomb kitöltheti Apple Music/Deezer adatokkal a kézi begépelés helyett – lásd [Életrajz automatikus lekérése](#fetching-a-bio-automatically) alább.
- **Közösségi média** – Twitter/X, Instagram, Facebook, YouTube és weboldal linkek, közvetlenül szerkeszthetők. A Mentés mindig mind az öt mezőt az űrlap tartalmára cseréli, még az üresen hagyott mezőt is. Életrajz lekérése soha nem nyúl olyan linkhez, amelyet te töltöttél ki: a Deezer közösségi linkjei csak a még üres mezőket töltik ki (a Deezer nem ismer minden hálózatot, ezért a többit egészítsd ki kézzel, és úgy marad).

## Amikor először nyitsz meg egy új előadót

Egy Könyvtár-előadó oldalának megnyitása automatikusan feltölti a profilját, de csak akkor, ha még semmi sem lett mentve hozzá – az első utáni minden látogatás gyors üres művelet, így ez soha nem ismétlődik, és lefutás után nem lassít semmit.

- **Fotó és banner** – a Spotifyból (lásd [Spotify](#spotify) alább), a YouTube Music pontos névegyezésére visszaesve, ha a Spotify nem ad semmit. Csak akkor, ha a Beállításokban bekapcsoltad az **Előadófotók automatikus beszerzése** és/vagy az **Előadóbannerek automatikus beszerzése** opciót (mindkettő alapból ki van kapcsolva, és mindegyik független); a szerkesztőablak mindig be tud állítani kézzel bármelyiket.
- **Életrajz, származás, alapítás éve, műfaj, együttes-jelző, bannerszín, közösségi linkek, hasonló előadók és platformazonosítók** – az Apple Musicból és a Deezerből kérve le, ahogy az [Életrajz automatikus lekérése](#fetching-a-bio-automatically) alább leírja.

Ha az Apple Music vagy a Deezer **hibázik**, miközben ez fut (nem elérhető, vagy a kérési korlát felett van), semmi sem mentődik – sem az életrajz, sem fotó –, és az oldal egyszerűen még nem mutat profilt, így a következő látogatás újra próbálkozik. Csak az számít válasznak, ha egy szolgáltatás azt mondja, nem ismeri az előadót: a profil ekkor abból készül, amije a másiknak volt. A Spotify rész (a hasonló előadók) soha nem akadályozza meg a profil elkészültét.

## Amikor egy letöltés befejeződik

Ugyanez a feltöltés háttérben fut, amikor egy előadó egyik száma letöltődött – akár az alkalmazásban indítottad, akár egy [Lejátszási lista figyelő](playlist-monitor.md) átfésülése –, ha az előadónak még nincs profilja, így a letöltött előadók készen állnak, mielőtt megnyitnád az oldalukat. Soha nem lassítja a letöltést: az előadó sorba kerül, és néhány másodperccel később töltődik ki, egyszerre két előadó, és a már sorban lévő nem kerül újra sorba, akárhány száma érkezik (egy ötvenszámos lejátszási lista egy előadótól egyszer tölti fel). A már a könyvtáradban lévő számok nem töltődnek le újra, és semmit sem indítanak el.

- **Melyik előadó** – az, amelyik alatt a fájl el van téve: az albumelőadó, különben az első feltüntetett előadó. A `Various Artists` kimarad.
- **Nyelv** – az életrajz és a műfaj a webes felület nyelvén érkezik, amelyet az oldal a szerveren tart (lásd [Nemzetköziesítés](internationalization.md)); amíg egy oldal nem szólt, angolul.
- **Fotó és banner** – csak annyira, amennyire az **Előadófotók automatikus beszerzése** / **Előadóbannerek automatikus beszerzése** engedi, abban a pillanatban kiolvasva, így egy beállítás átállítása már a következő számra érvényes.
- **Top songs** – nem így készülnek; az előadó oldalára várnak (lásd [Top songs](top-songs.md)).

Ha egy előadóhoz sehol sem találtak semmit, ez akkor is csak egyszer fut le – nem próbálkozik újra minden további látogatáskor. Használd a szerkesztőablakot, hogy később bármikor kézzel válassz fotót/bannert, vagy újra megpróbáld a lekérés gombot.

## A Linkek fül

Az az előadó, akinek legalább egy mentett linkje van, kap egy **Linkek** fület közvetlenül az **Életrajz** előtt (amely továbbra is az utolsó fül), számlálóval. Kártyákként listázza őket, bármilyen képernyőn, és akár van az előadónak bannere, akár nincs: először a **Streaming platformok**, utána a **Közösségi média**. Minden kártya az oldal nevét és címét mutatja, és új fülön nyitja meg. Csak az szerepel, ami ténylegesen el van mentve, és a link nélküli előadónak nincs Linkek füle (nála a `?tab=links` az első fület nyitja).

- **Streaming platformok** – Spotify, YouTube Music, Deezer és Apple Music, a profil `platforms_id` mezőjéből építve: minden mentett azonosítóból link lesz (pl. egy mentett Deezer-azonosítóból link az előadó Deezer-oldalára). Az azonosítókat mind automatikusan oldja fel, amikor először kérnek le életrajzot, minden platformon pontos névegyezéssel (a Spotifyé az előadó saját Spotify-számainak egyikéből jön, ha van, ami nem tud azonos nevű másikat kiválasztani). Egyet kézzel is hozzáadhatsz vagy javíthatsz az előadó profiljának JSON-jában (lásd alább).
- **Közösségi média** – Twitter/X, Instagram, Facebook, YouTube és weboldal: egy kártya a fenti Közösségi média fül minden nem üres mezőjéhez. Csak webcímek nyílnak meg: a `https://` nélkül beírt link megkapja azt, és minden más típusú cím (például egy `javascript:`) figyelmen kívül marad.

## Spotify

A Spotify soha nem jelenik meg szabad szöveges keresési forrásként, de mind a választó, mind az első látogatás automatikus feltöltése (lásd fent) ott mégis megtalálja az előadót. Először az előadó néhány saját, már letöltött számát nézik meg: ha egyet a Spotifyról töltöttek le, a Downtify már ismeri annak a számnak a Spotify-azonosítóját, és közvetlenül oldja fel a képet – ez a legmegbízhatóbb út, mert nem érhet el másik, azonos nevű előadót. Ha egyetlen szám sem a Spotifyról jött (mondjuk a YouTube-ról töltődtek le), az előadót pontos névvel keresik (kis- és nagybetűtől függetlenül – közelítő egyezést soha nem használ). A választóban ez a jelölt jelenik meg elsőként, **Spotify** címkével.

A névkeresés a Spotify saját webes lejátszójának keresőmezőjét használja, ezért egy belső azonosítótól függ, amelyet a Spotify megváltoztathat; ha ez megtörténik, a Downtify a fotóhoz/bannerhez a YouTube Musicra esik vissza, és a Spotify-azonosítót üresen hagyja, ahelyett hogy hibázna.

A fotó és a banner a Spotify-on valóban különböző kép, és másképp oldódik fel: a négyzetes fotó az előadó nyilvános beágyazási oldaláról jön, míg a széles banner a Spotify saját előadóoldalának adataiból (amelyet a beágyazás egyáltalán nem tesz elérhetővé). Nem minden előadónak van bannere – ha nincs, a bannerválasztóhoz nem kínál Spotify-jelöltet, ahelyett hogy a négyzetes fotóra esne vissza.

A Spotifyról származó számok nélküli előadó egyszerűen nem kap Spotify-jelöltet – keress a YouTube Musicon/Deezeren, illessz be egy linket, vagy tölts fel egy képet.

## Életrajz automatikus lekérése

A fejléc alatt az előadó oldala rövid, csak olvasható életrajzot mutat – üres, amíg nem mentenek egyet. A kitöltéséhez nyisd meg a szerkesztőablak **Életrajz** fülét, és kattints a szövegmező feletti **Lekérés az Apple Music-ból** vagy **Lekérés a Deezerből** gombra (lásd [A forrás kiválasztása](#choosing-the-source)), amely az adott szolgáltatás életrajzát betölti a mezőbe, hogy átnézd és elmentsd. Az első látogatás automatikus feltöltése, amely magától ment, az előadót az Apple Musicban pontos névegyezéssel keresi (ugyanazzal a névkereséssel, amelyet az Apple saját Zene alkalmazása használ), és lekéri az életrajzát, származását, alapítási évét, műfaját, együttes-jelzőjét és a banner kiemelőszínét – a szöveget (életrajz és műfaj) a felületed jelenlegi nyelvén –, és elmenti az eredményt. A műfaj (az Apple Music előadónként egyet ad, pl. „Hard rock”) kis tablettaként jelenik meg az előadó oldalának Életrajz fülén felül, a származás és az alapítás éve mellett. Az Apple Music megmondja, hogy az előadó együttes-e: együttesnél ez a dátum „1995-ben alakult”-ként olvasható, szólóelőadónál – akinél a dátum általában születési dátum – „Született: 1984. szeptember 27.” (a felület minden nyelvére lefordítva; az az előadó, akinek az együttes-jelzője ismeretlen, az „alakult” marad). Maga a dátum úgy jelenik meg, ahogy az Apple Music adta, így a lekérés nyelvét őrzi. Ha az Apple Musicnak nincs pontos egyezése, vagy van, de nincs életrajzszöveg a te nyelveden, a következő másodlagos életrajzforrásként a Deezert próbálja – az közösségi linkeket és „a rajongók ezt is szeretik” hasonló előadók nevét is hoz (a hasonló előadók az előadó profilfájljában tárolódnak, de még sehol sem jelennek meg, egy jövőbeli kiegészítésre tartogatva), és a Közösségi média fület is kitölti. Csak ha egyik forrásnak sincs semmije, látsz hibát kitalált/téves életrajz helyett.

Az Apple Music szerkesztőségi életrajzai nem minden előadóhoz készülnek el minden nyelven – ha egy adott előadónál hiányzik egy nyelv, helyette a Deezer életrajza (ha van) szolgál, míg a származás/alapítás éve/együttes-jelző továbbra is az Apple Musicból jön, mivel ezek a tények nem fordított szöveg (a műfaj mindig csak az Apple Musicból való, így üres marad, ha az Applenek nincs egyezése). Néhány nyelvet (a bolgárt az írás idején) az Apple Music egyáltalán nem kínál, és mindig az alapértelmezett nyelvű életrajzára esik vissza.

Az életrajz az előadó JSON-jában egyszerű szövegként tárolódik – HTML-címkék és felsorolásjelek nélkül: üres sor választja el a bekezdéseket, és az Apple Music-életrajz minden `•` felsorolásjele (amelyeket az Apple egyetlen sortöréssel választ el) saját bekezdéssé válik. A Deezer HTML-életrajzait ugyanígy laposítja (minden bekezdésből üres sorral elválasztott bekezdés lesz, minden más címke eldobódik). Az előadó oldala minden bekezdést külön mutat, és megtartja bennük az egyszerű sortöréseket, a Életrajz fül szövegmezője pedig pontosan ezt a szöveget szerkeszti.

Az ilyen újralekérés csak akkor fut, ha rákattintasz a gombra – a fent leírt első látogatásos automatikus feltöltés után magától nem ír felül semmit. Csak az első alkalommal (akár automatikus feltöltés, akár kézi kattintás) kell névre keresni: a feloldott Apple Music és Deezer előadóazonosítók ezután az előadó profilfájljában gyorsítótárba kerülnek, így az újralekérés csak közvetlenül olvassa újra ugyanazokat az előadókat.

Egy mentett életrajz törléséhez nyisd meg az Életrajz fület, ürítsd ki a szövegmezőt, és Mentsd – a származás, az alapítás éve, a műfaj, az együttes-jelző, a közösségi linkek, a hasonló előadók és a gyorsítótárazott platformazonosítók érintetlenek maradnak.

## A forrás kiválasztása

Az Életrajz fülön két link van a szövegmező fölött, hogy te válaszd ki, melyik életrajz olvasmányosabb:

- **Lekérés az Apple Music-ból** – az Apple Music szerkesztőségi életrajzát tölti be a szövegmezőbe. Ha az Apple Musicnak nincs egy sem ehhez az előadóhoz a te nyelveden, hibát kapsz helyettesítés helyett.
- **Lekérés a Deezerből** – a Deezer életrajzát tölti be, akkor is, ha az Apple Musicnak van. Ha a Deezernek nincs, hibát kapsz.

A link kattintása **csak a szövegmezőt tölti ki** – semmi sem mentődik, amíg meg nem nyomod a **Mentés** gombot, így elolvashatod, szerkesztheted, vagy előbb kipróbálhatod a másik szolgáltatást, és az ablak mentés nélküli bezárása a jelenlegi életrajzot úgy hagyja, ahogy volt. Csak az életrajz szövege töltődik be: a származást, az alapítás évét, a műfajt, a közösségi linkeket, a hasonló előadókat és a platformazonosítókat ezek a linkek nem érintik (azokat az első látogatás automatikus feltöltése tölti ki). A feltöltés nem kérdezi, melyik szolgáltatás: az Apple Music életrajzát használja, és csak akkor esik vissza a Deezerére, ha az Apple Musicnak nincs.

## Hová kerülnek a fájlok

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Előadónként egy fájl, az ő nevével (ugyanúgy megtisztítva, mint a számok fájlnevei) – nincs adatbázisrekord, így a fájl jelenléte a lemezen az, amit az előadó oldala ellenőriz. Új fotó/banner mentése felülírja az előzőt (a webes felület megakadályozza, hogy a régi másolata megmaradjon: minden mentett kép URL-je tartalmazza a fájl módosítási idejét, így a lecserélt fotó újra letöltődik, míg az érintetlen a gyorsítótárban marad), az `ArtistData/<Artist>.json` pedig a fent leírt életrajz/közösségi média/hasonló előadók/platformazonosítók adatait tartja, továbbá a `current_cover` és `current_cover_banner` mezőben azt, melyik kép a jelenlegi fotó/banner: annak az URL-nek az elérési útját, ahonnan letöltötték (host és query nélkül, hogy ugyanaz a kép egy másik CDN-címről is egyezzen), vagy `upload` az általad feltöltötthöz. Ezzel veti össze a szerkesztőablak az egyes jelölteket, hogy megjelölje a használtat. Ezek egyszerű fájlok a letöltési mappádban, így az olyan szolgáltatások, mint a Navidrome, közvetlenül olvashatják őket, ha ugyanarra a helyre irányítod.

Az előadónevek úgy egyeznek, ahogy a lemez tartja őket: a Downtify az `AC/DC`-t `ACDC` néven archiválja, mert a fájlnév nem tartalmazhat `/` jelet, az előadó-címke nélküli szám pedig ebből a fájlnévből veszi az előadóját – így ugyanaz az előadó megjelenhet `AC/DC`-ként vagy `ACDC`-ként. Minden névkeresés (Spotify, Deezer, YouTube Music és Apple Music) figyelmen kívül hagyja a kis- és nagybetűt és azokat a karaktereket, amelyeket a fájlnév nem tartalmazhat, így mindkét írásmód ugyanazt az előadót találja meg, és ugyanazokat a fenti fájlokat használja. Bármi másban eltérő név – mondjuk `AC/DC Tribute` – továbbra is másik előadó, és soha nem egyezik.

A `platforms_id` a `spotify`, `youtubemusic`, `deezer` és `applemusic` kulcsokat ismeri, mind automatikusan feloldva – a Spotify az előadó egyik saját Spotify-számából, vagy ha nincs, pontos névvel; a többi pontos névvel. Az életrajz lekérése a hiányzó Spotify-azonosítót is kitölti, így egy előadó, akit ennek megléte előtt nyitottak meg, egy lekérés után megkapja a Spotify-ikonját. Egy már mentett azonosítót soha nem cserél le, és a JSON-fájlt továbbra is szerkesztheted közvetlenül, hogy kézzel állíts be egyet.

## Hatókörön kívül

Itt fotót/bannert választani soha nem érinti a letöltési folyamatot – semmilyen hatása nincs arra, mi ágyazódik be a saját hangfájljaid címkéibe, és egy szám letöltése soha nem kér le automatikusan előadóképet.

A *Hasonlók* fül fotót mutat azokhoz az előadókhoz is, akik nincsenek meg neked, és ugyanezt teszi a Könyvtár *Előadók* rácsa, maga az előadó oldala, a Figyelő *Előadók* füle (a figyelt előadó, a listában és a szerkesztőablakában) és az előadók a [Felfedezés](discover.md) és a [Finder](finder.md) oldalon – ahol az oldal már megkapta az előadó Deezer-képét, így nincs szükség névkeresésre, és helyette az előadóhoz általad mentett fotó jelenik meg – minden előadóhoz, akinek nem választottál fotót (a Könyvtár és maga az előadó oldala az előadó egyik számborítóját használja, ha a Deezernek nincs; a Figyelőnek nincs száma, ezért kezdőbetűket mutat) - csak egy valódit: az az előadó, akinek a Deezernél nincs fotója (általános helyettesítő képet ad), a szokásos kezdőbetűt kapja - de ez csak megjelenítésre való: a szerver a Deezer képét továbbítja a böngésződnek (amely három órára gyorsítótárazza) mentés nélkül, és soha nem lesz egy előadó fotója vagy bannere. Csak a valódi válaszok maradnak meg: ha a Deezer nem elérhető, vagy éppen a kérési korlát felett vagy, a csempe egyelőre a kezdőbetűt (vagy a számborítót) mutatja, és semmi sem jegyződik meg, így a fotó legközelebb jelenik meg, amikor megnyitod az oldalt. A fotók csak azoknak az előadóknak íródnak lemezre, akiknek te magad állítottál be egyet, vagy akiknek a fotóját/bannerét az első látogatáskor mentették, ahogy fent le van írva (amikor a Beállítások engedik). Lásd [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
