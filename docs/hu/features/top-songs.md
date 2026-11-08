---
icon: lucide/star
---

# Top Songs

Egyes előadóknak hatalmas katalógusuk van, amelyből csak néhány szám számít. Ahelyett, hogy számonként szednéd össze a hivatkozásokat, vagy letöltenél egy 50+ számos „This is…” lejátszási listát a néhány dalért, amit igazán akarsz, illeszd be az előadó saját hivatkozását, és válassz a legnépszerűbb dalai közül.

## Hogyan használd

1. Illessz be egy előadóhivatkozást a keresőmezőbe vagy a Kezdőlapon:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` vagy `https://music.youtube.com/@handle`
   - **Deezer**: `https://www.deezer.com/artist/…`
2. Megnyílik az **előadó oldala** a fotójával és nevével, és felsorolja a kiadványait (albumok, kislemezek, EP-k és válogatások, ahol a szolgáltatás ismeri őket), a Spotifyon és a Deezeren a legújabbal kezdve; kattints egyre, hogy lásd a számait vagy letöltsd. A **Top Songs** gomb mellett a Spotify- és YouTube Music-előadóknál ott van az **Új kiadások figyelése** is — a Deezer-előadóknál nincs, mert a [Lejátszási lista figyelő](playlist-monitor.md) nem támogatja a Deezert.
3. A **Top Songs** megnyitja a legnépszerűbb daljainak listáját, abban a sorrendben, ahogy a szolgáltatás rangsorolja őket. A Spotifynál és a YouTube Musicnál egy szemmel ellátott jelvény mutatja, hányszor játszották le az egyes dalokat, a nyelvedre jellemző módon rövidítve (`1,5 bi` portugálul, `1.5B` angolul) — a Spotifyé zöld, a YouTube Musicé piros. A YouTube Music csak kerekített számot közöl (`1.2B plays`), így az övé közelítés; a Downtify ugyanabból a YouTube Music-kérésből olvassa ki, amely a dalokat felsorolja, plusz még egy kéréssel a lejátszásszámokhoz. A Deezer saját „top” rangsorához nincs nyilvános lejátszásszám, amit meg lehetne jeleníteni, így a dalai jelvény nélkül szerepelnek. Az első öt már be van jelölve; jelölj be továbbiakat, vagy vedd ki bármelyiket, majd nyomd meg a **Kijelöltek letöltése** gombot.

### Dalok meghallgatása letöltés előtt

A Top Songs oldalon és azon az oldalon, amelyet egy beillesztett **album**- vagy **lejátszásilista**-hivatkozás nyit meg, minden dal teljes hosszban szól: vidd az egeret a sora fölé, és a szám lejátszás gombbá változik (telefonon a lejátszás gomb mindig ott van); nyomd meg, és a dal a YouTube-ról közvetlenül a beépített lejátszóba streamelődik. Nyomd meg újra a szüneteltetéshez, vagy egy másik sor gombját a váltáshoz. A könyvtáradban már meglévő dal a könyvtárból szól, a lista többi letöltött dala pedig utána sorba kerül.

A streamet ez a szerver szolgálja ki, soha nem a böngésző közvetlenül a YouTube-ról: a sor a saját YouTube-videójára oldódik fel (egy YouTube Music-dalnál a sajátjára, egyébként a legközelebbi keresési találatra), a szerver pedig egyszer letölti a hangot a stream-gyorsítótárába, majd a gyorsítótárazott fájlt játssza le (lásd: [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Csak a szervernek kell elérnie a YouTube-ot, a korhatáros számhoz pedig YouTube-sütik kellenek (lásd: [YouTube sütik](youtube-cookies.md)), akárcsak egy letöltéshez.

## Források

| Forrás | Mit jelent a „top songs” | Felsorolt dalok |
|--------|------------------------|--------------|
| Spotify | Az előadó saját **Népszerű** polca, ugyanazok a számok, amelyek a Spotify-oldala tetején látszanak | Legfeljebb 10 |
| YouTube Music | Az előadó **Top songs** lejátszási listája, népszerűség szerint rangsorolva | Az első 50 |
| Deezer | Az előadó saját **top** rangsora (ugyanaz a polc, amelyet a `deezer.com` az oldalán mutat) | Az első 50 |

A Spotify nyilvános embedjének nincs diszkográfiája, ezért a Downtify a kiadványokat a Spotify webes lejátszójának saját diszkográfia-lekérdezéséből olvassa, ugyanabból a nem nyilvános API-ból, amelyet az albumnevekhez használ. Ha a Spotify megváltoztatja, a Downtify egy rövidebb listára esik vissza (minden album, de csak a tíz legújabb kislemez), és ha az is kudarcot vall, nem mutat kiadványokat. A Spotify-dalok a szokásos metaadat-majd-hangegyeztetés folyamaton mennek át, az albumnévvel előre csatolva; a letöltés kitölti a többit (számsorszám, év), mint bármely Spotify-dalnál. A YouTube Music-dalok a saját videójukhoz vannak kötve, mint bármely más YouTube Music-hivatkozás. A Deezernek valódi, nyilvános diszkográfia-végpontja van, így a kiadványlistájához nincs szükség tartalékra; a dalai ugyanazon a metaadat-majd-hangegyeztetés folyamaton mennek át, mint a Spotifyéi, 30 másodperces előnézeti klippel, ha a Deezer kínál ilyet.

## Egy előadó oldalán a Könyvtárban

Egy olyan előadó, akit a Downtify ismer a Spotifyon (lásd: [Előadó fotója, bannere és életrajza](artist-images.md)), a Könyvtárban lévő oldalán egy **Top songs** fület is kap a Számok és A rajongók ezeket is kedvelik mellett. Kilistázza a Spotify-top daloknak az első **5**-ét minimális listaként, mint a keresési találatok, oszlopfejlécek alatt (#, Cím, Album, hossz): szám, borító, cím, előadó, album és hossz. Egy olyan dalnak, amely nincs a könyvtáradban, jobbra van egy **letöltés** gombja (a letöltés közbeni előrehaladásával); letöltés után ez a **A könyvtárban** címkévé válik, és a dal lejátszható úgy, mint egy album oldalán: a szám egérmutatásra lejátszás gombbá változik, a borító lejátszik, és a dupla kattintás vagy az érintés is lejátszik. Egy dal lejátszása a lista többi letöltött dalát sorba állítja utána, rangsorrendben, és a játszott dal ki van emelve. Egy még nem letöltött dal helyette **teljes hosszban streamelődik**: vidd az egeret a sora fölé, és ahol a szám van, megjelenik egy lejátszás gomb; nyomd meg (vagy a borítót), és a beépített lejátszóban szól, mint egy letöltött dal (lásd: [Dalok meghallgatása letöltés előtt](#playing-songs-before-downloading)). A lista alatt a **További népszerű számok** ezt az előadót a fent leírt Top Songs oldalon nyitja meg, ahol a kijelölés, a **Lejátszási lista létrehozása** kapcsoló és több dal egyszerre letöltése található. A fül csak akkor jelenik meg, ha az előadó Spotify-azonosítója ismert, ami az oldala első megnyitásakor történik; a dalokat ekkor kéri le, így a fül számlálója néhány másodperccel később magától kitöltődik, bárhol vagy is az oldalon.

Egy dal borítójának, albumának és lejátszásszámának kiolvasása néhány másodpercig tart, ezért a Downtify az öt dalt előadónként egy fájlban tartja, `<downloads>/.metadata/ArtistTopSongs/<Előadó>.topsongs.json`, amelyet az előadó oldalának első megnyitásakor a háttérben hoz létre. **7 napig** megbízható: a fül megnyitása azonnal beolvassa a fájlt, és ha régebbi, a régi lista azonnal megjelenik, miközben egy friss töltődik mögötte — az oldal néhány másodpercen belül magától kicseréli, anélkül, hogy megzavarna egy éppen letöltődő vagy játszott dalt. A fájl csak a dalokat, a borítóikat, a klip-hivatkozásokat és a lejátszásszámokat tárolja — soha a hangot vagy a képeket, és soha azt, hogy egy dal a könyvtáradban van-e, mert azt élőben számolja ki. Gyorsítótár: töröld, amikor akarod, és újra létrejön.

## Lejátszási lista létrehozása

A Top Songs oldal **Lejátszási lista létrehozása** kapcsolója **ki** van kapcsolva az első alkalommal, amikor megnyitsz egy előadót, és **be** van kapcsolva, ha a könyvtáradban már létezik egy **Top Songs of {artist}** nevű lejátszási lista, így a későbbi letöltések tovább bővítik. Állítsd át a kapcsolót, és a választásod addig marad, amíg azon az oldalon vagy. Kikapcsolva a dalok úgy töltődnek le, mint bármely más önálló dal: közvetlenül a letöltési mappádba, vagy az előadó-/albummappáidba, ha a [Fájlszervezés](file-organization.md) be van kapcsolva, saját mappa, M3U és előadófotó nélkül.

Kapcsold be, és a Downtify **Top Songs of {artist}** nevű lejátszási listaként kezeli őket. Hová kerül, az a Fájlszervezéstől függ:

| Rendezés előadó / album szerint | Dalok | M3U és borító |
|---|---|---|
| Mindkettő ki | Egy `Top Songs of {artist}` nevű mappában | Ugyanabban a mappában |
| Az egyik vagy mindkettő be | E beállítások szerint rendezve: `<Előadó>/`, `<Album>/` vagy `<Előadó>/<Album>/`. Nincs `Top Songs of {artist}` mappa. | A `Playlists/` mappában, `Top Songs of {artist}.m3u` és `.jpg` néven |

Mindkét esetben:

- az [M3U lejátszási lista](m3u-export.md) a dalokat **az előadó rangsorrendjében** sorolja fel, akkor is, ha csak néhányat jelöltél be;
- az előadó fotója az M3U mellé mentődik borítóként, ha a **Lejátszási lista borítójának mentése** engedélyezve van (lásd: [Lejátszási lista borítója](playlist-cover-art.md)). Ehhez nincs külön beállítás.

## Ismert korlátozások

::: warning A Spotify és a YouTube Music keverése ugyanahhoz az előadóhoz
A **Top Songs of {artist}** M3U-ját a [lejátszásilista-katalógus](library-catalog.md) alapján tartja szinkronban a program, amely Spotify-számazonosítók szerint van indexelve. Ha egy előadó top dalait a **Spotifyról**, később pedig a **YouTube Musicról** töltöd le (vagy fordítva), a második köteg fájljai helyesen letöltődnek, de a következő M3U-frissítés kidobja őket a lejátszási lista fájljából, mert a YouTube Music-azonosítók nem férnek bele ebbe a formátumba. További dalok hozzáadása ugyanabból a forrásból nem érinti.
:::

::: info Albumnevek a Spotify-dalokhoz
A Spotify előadóoldala nem mondja meg, melyik albumról való egy dal. A Downtify az albumneveket és a lejátszásszámokat ugyanabból a Spotify-lejátszó API-ból szerzi, amelyet a teljes lejátszási listák olvasásához használ: egy extra kérés előadónként, plusz egy minden olyan albumhoz, amelyet az a kérés nem sorol fel. Ez az API nem nyilvános, így ha a Spotify megváltoztatja, az **Album** oszlop üresen jön a Spotify-daloknál, és a lejátszásszám-jelvény eltűnik; a dalok továbbra is letöltődnek, de a Downtifynak ekkor az albumot a YouTube Music-egyezéséből kell visszaállítania, ami gyakran kudarcot vall, így a fájl album-címke nélkül marad, és bekapcsolt [Rendezés album szerint](file-organization.md) mellett egy `unknown` albummappába kerül. A YouTube Music top dalai már hozzák az albumukat. Ha a lejátszásszámok bármelyik forrásnál nem érkeznek meg, a jelvény egyszerűen nem jelenik meg.
:::

## API

Lásd a [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) végpontot az API-referenciában.
