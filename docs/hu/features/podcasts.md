---
icon: lucide/mic
---

# Podcastok

Iratkozz fel egy műsorra, és az új epizódjai maguktól letöltődnek — anélkül, hogy minden héten újra be kellene illesztened egy hivatkozást. A podcastokat elejétől végéig másképp kezeli a program, mint a zenét: egy epizód már kész hangfájl egy RSS `<enclosure>` URL-en, így nincs YouTube-egyeztetés vagy átkódolás, csak egy letöltés és a címkék kiírása.

Nyisd meg a **Podcastok** oldalt az oldalsávról (telefonon: **Továbbiak → Podcastok**).

Az előfizetések azokhoz tartoznak, akik feliratkoznak: minden fiók a saját műsorait követi (ugyanaz a feed kétszer előfizetve két mappába kerül), saját epizódokkal, folytatási pozíciókkal és elutasításokkal. Egy admin minden előfizetést lát.

## Feliratkozás

Illessz be egyet ezek közül a **Podcast hozzáadása** mezőbe, vagy írj be egy nevet kereséshez:

| Bevitel | Mi történik |
|-------|--------------|
| Egy podcast RSS-feed URL-je | Közvetlenül lekéri és feldolgozza |
| Egy Spotify-műsorhivatkozás (`open.spotify.com/show/…`) | A műsor nevét a Spotifyból olvassa, majd az iTunes podcastkönyvtárán keresztül a nyilvános RSS-feedjéhez rendeli |
| Egy Spotify-epizódhivatkozás (`open.spotify.com/episode/…`) | Ugyanaz, mint a műsorhivatkozásnál, és a konkrét epizód ki lesz emelve, ha a címe megtalálható a feedben |
| Egy műsor neve (szabad szöveg) | Az iTunes podcastkönyvtárában keres |

::: info A Spotify-exkluzív műsorok nem tölthetők le
Egy csak a Spotifyon létező műsort (nyilvános feed nélkül) így jelez a program — a Downtify nem találgat, és nem esik vissza másra. Keresd meg a műsort név szerint, mielőtt feltételeznéd, hogy exkluzív.
:::

A megerősítés előtt választasz:

- **Megtartás** — lásd lent: [Hány epizód töltődik le](#how-many-episodes-are-downloaded).
- **Intervallum** — milyen gyakran ellenőrzi a feedet új epizódokért, 15 percenként egészen havonta egyszerig. Az előfizetéseket ugyanazon az ütemezésen és ugyanazzal a háttérátfésüléssel ellenőrzi, mint a [Lejátszási lista figyelő](playlist-monitor.md) megfigyeléseit — számára csak egy újabb fajta megfigyelés.

## Hány epizód töltődik le

A **Megtartás** beállításnak két külön viselkedése van, műsoronként egyszer választva:

- **Minden új epizód** — azonnal csak az egyetlen legújabb epizódot tölti le (a feliratkozás nem meghívás arra, hogy egy műsor teljes régi katalógusát lehúzd), majd minden ellenőrzéskor letölti a megjelenő új epizódokat. Semmi sem törlődik automatikusan.
- **Legutóbbi *N* epizód** — gördülő ablak. Minden ellenőrzés után (az elsőt is beleértve) a legutóbb megjelent *N* epizód letöltődik, és minden régebbi letöltött epizód törlődik a hely felszabadításához. Ha később megemeled az *N*-t, ezek a törölt epizódok újra letölthetők lesznek; az az epizód, amelyet te magad távolítottál el a **Letöltés eltávolítása** paranccsal, ezen az úton sosem tér vissza — lásd: [Epizódok eltávolítása](#removing-episodes).

A **Megtartás** és az intervallum bármikor módosítható a műsor oldaláról.

## Epizódok

Egy műsor oldala felsorolja az epizódjait, a legújabbal kezdve, mindegyiknél a megjelenés dátumával és hosszával. A megőrzési szabály által nem fedett epizód is megjelenik itt — koppints a **Letöltés** gombra, hogy csak azt az egyet megkapd, bármilyen régi is.

### Epizódok eltávolítása

Minden epizód **⋯** menüjében van **Letöltés eltávolítása**, amely törli a fájlt, de az epizódot a listában hagyja. Egy epizód fájlja kétféleképpen tűnhet el, eltérő következménnyel:

| Hogyan | Automatikusan visszajön? |
|-----|----|
| A megőrzés kigurította (a „legutóbbi N megtartása” ablakon kívül eső régebbi epizód) | Igen, ha újra megemeled a **Megtartás** értékét |
| Te magad választottad a **Letöltés eltávolítása** lehetőséget | Nem — bármikor töltsd le újra kézzel |

### Lejátszottnak jelölés

Az epizód **⋯** menüjével kézzel lejátszottnak vagy nem lejátszottnak jelölheted, vagy csak hagyd végigmenni — a hosszának utolsó néhány másodpercében lévő epizód magától lejátszottnak lesz jelölve.

## Epizódok lejátszása

Az epizódok ugyanabban a beépített lejátszóban szólnak, mint a zene, néhány különbséggel, amely csak egy podcast-epizódnál jelenik meg:

- **15 mp vissza / 30 mp előre** a véletlen sorrend és az ismétlés helyett, amelyek egyetlen epizódra nem vonatkoznak.
- **Lejátszási sebesség** (0,75×–2×), az elalvási időzítő mellett.
- A **folytatási pozíció** ~10 másodpercenként és szüneteltetéskor még egyszer mentődik a szerverre, így a lap bezárása — vagy a Downtify megnyitása egy másik eszközön — ott folytatja az epizódot, ahol abbahagytad. Egy műsor epizódlistája „Folytatás itt: …” tippet mutat minden félig meghallgatott epizódnál.

A szív (kedvelt dalok) és az „ugrás az albumra/előadóra” nem vonatkozik az epizódokra, és nem is jelenik meg náluk.

## Könyvtár

A podcastoknak saját helyük van — a **Könyvtár**ban sosem jelennek meg számként, albumként vagy előadóként, és a [Könyvtár feljavítása](library-upgrade.md) futása teljesen békén hagyja őket (egy epizódnak nincs Spotify-szám azonosítója, amelyből a címkéket frissíteni lehetne, és külön dalszövege sincs, amit keresni kellene).

Az epizódfájlok ugyanazon a letöltési köteten maradnak, `Podcasts/<Műsor>/<dátum> - <Epizód>.<kiterjesztés>` útvonalon, így a könyvtáradra mutató bármely médiaszerver látja őket is.

## Címkék

A Downtify azt írja ki, amit a podcast-alkalmazások és médiaszerverek egy epizódnál már olvasnak: a címet, a műsort albumként, a műsor szerzőjét előadóként, a megjelenés évét, az epizód-/évadszámokat, a műsor saját borítóját (a feed saját képének és az iTunes-énak a nagyobbika, ugyanaz az elv, mint a [zenei borítóknál](download-settings.md#cover-art-resolution)) és az epizód leírását megjegyzésként. A műsorjegyzetek egyszerű szövegként tárolódnak — a Downtify eltávolítja belőlük a HTML-t, nem jeleníti meg.

## Jó tudni

- **Nincsenek videó-podcastok.** Az az epizód, amelynek egyetlen melléklete videófájl, teljesen kimarad; csak a hang támogatott.
- **Nincsenek fejezetek.** A fejezetjelölőket tartalmazó feedek ezeket a Downtifyban még nem kapják meg.
- **Nem tükröződik a Navidrome-ban.** A lejátszási listákkal ellentétben a podcast-előfizetések nem kerülnek be egy Navidrome-könyvtárba — az epizódok egyszerű fájlok, amelyeket a médiaszervered már magától lát.
- A leiratkozás (**⋯ → Leiratkozás**) alapértelmezetten eltávolítja a letöltött epizódokat; válaszd a **Leiratkozás, letöltött epizódok megtartása** lehetőséget, hogy a fájlok a helyükön maradjanak.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` és `PUT /api/podcasts/episodes/{id}/playback`. Lásd az [API-referenciát](../api-reference.md#podcasts).
