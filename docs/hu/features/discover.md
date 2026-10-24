---
icon: lucide/compass
---

# Felfedezés

Előadók, akik még nincsenek meg neked, azok alapján javasolva, akik igen. Nyisd meg a **Felfedezés** oldalt az oldalsávról (telefonon: **Továbbiak → Felfedezés**). A felül lévő keresőmező a [Finder](finder.md), amely csak a Deezeren keres: a keresés az eredményeit a javaslatok helyén mutatja, a mező törlése pedig visszahozza a javaslatokat.

Nem kell hozzá fiók vagy API-kulcs: a javaslatok a [Deezer](https://www.deezer.com/) nyilvános „hasonló előadók” listájából jönnek, amely bejelentkezés nélkül is működik.

## Hogyan választódnak ki a javaslatok

1. **Az előadóid súlyozva vannak.** A könyvtárad minden előadója számít valamennyit, és az alábbiak mindegyikéért többet, a legfontosabbtól a legkevésbé fontosig:
    - milyen gyakran **hallgatod** őket a Downtify lejátszójában (a közelmúltbeli hallgatás többet számít, mint a hónapokkal ezelőtti),
    - hány dalukat **kedvelted meg**,
    - hány daluk van **a könyvtáradban**.

    A súly az idővel ellaposodik, így egy 400 dalos diszkográfiájú előadó nem nyomja el azt, akit minden nap játszol.
2. **A legjobb 15-öt megkeresi a Deezeren**, amely mindegyikhez visszaadja azokat az előadókat, akiket a hallgatói is szeretnek.
3. **Minden javasolt előadó pontokat kap** minden olyan előadódtól, aki javasolja — többet egy nagyobb súlyú előadótól, és többet, minél előrébb áll a Deezer listáján. Az az előadó, akire több kedvenced mutat, előrébb kerül annál, akit csak egyikük említ. Minden javaslat alatt a *Mert szereted …* megnevezi azokat az előadókat, akiktől származik.

A könyvtáradban már meglévő előadókat és az általad [elrejtett](#hiding-artists) előadókat soha nem javasolja.

Kattints egy javaslat fotójára, hogy megnyisd az előadót a [Finder](finder.md) oszlopaiban — a profilját, a teljes diszkográfiáját és bármelyik album számait, mind a Deezerről. A javaslat **⋯** menüjében van még **Dalok keresése** (az előadó dalai [Finder](finder.md)-keresésként megjelenítve), **Megnyitás a Deezeren** és **Nem érdekel**. Az oldal a legjobb 12 előadót mutatja; a **Mind megjelenítése** minden javaslatot listáz (legfeljebb 48-at).

## Albumok és lejátszási listák

Az előadók alatt, rájuk építve:

| Szakasz | Mi van benne |
|---------|--------------|
| **Albumok neked** | A 12 legjobb javasolt előadó mindegyikének legismertebb albuma |
| **Még több az előadóidtól** | A 6 legnagyobb súlyú előadód mindegyikétől legfeljebb két népszerű album, amely még nincs a könyvtáradban |
| **Lejátszási listák neked** | Minden javasolt előadó legfontosabbjai: a Deezer saját **`100% <előadó>`** listája (a Deezer szerkesztői állítják össze), majd a Spotify saját **`This Is <előadó>`** listája |

Két lépésben érkeznek:

1. **Először a Deezer.** Minden előadó diszkográfiáját a Deezerről olvassa be: egy teljes album megelőz egy kislemezt vagy EP-t, és ezek között az megy előre, amelyiknek a legtöbb rajongója van. Ez a válasz gyors, és megtölti a polcokat.
2. **Aztán a Spotify.** Néhány másodperccel később a Spotify saját választásai ugyanezekhez az előadókhoz (a saját keresőjéből) hozzáadódnak minden polc **végére** — helyfoglalók mutatják, hová kerülnek betöltés közben, és semmi, ami már az oldalon van, nem mozdul el. Az az album, amelyet mindkét szolgáltatás választ, egyszer jelenik meg. Minden Spotify-albumot előadó és cím alapján keres meg a Deezeren; ha a Deezer megvan, a többihez hasonlóan a Finderben nyílik meg.

Minden album- és lejátszásilista-borító bal alsó sarkában egy kis ikon mutatja, melyik szolgáltatásból jön:

- **Deezer** — egy album a [Finder](finder.md) oszlopaiban nyílik meg, a számai teljes hosszban lejátszásra és letöltésre készen.
- **Spotify** — a Deezeren nincs meg az az album, ezért ugyanazt az oldalt nyitja meg, mint egy beillesztett Spotify-hivatkozás.

A lejátszási listák — a Deezer és a Spotify listái is — mindig ezt az oldalt nyitják meg, ahol **teljes hosszban meghallgathatod a daljaikat**, mielőtt bármelyiket letöltenéd (lásd: [Dalok meghallgatása letöltés előtt](top-songs.md#playing-songs-before-downloading)), majd letöltheted az egészet, csak az új dalokat vagy egy kijelölést.

Minden egy hétig megmarad, mint a hasonló előadók, a Spotify-album Deezer-egyezése pedig egy hónapig (egy hétig, ha a Deezeren nem volt meg, arra az esetre, ha később felkerül). A könyvtáradban már meglévő album (előadó és cím alapján egyeztetve, így a `Dummy (Deluxe Edition)` a `Dummy`-nak számít) és egy már letöltött lejátszási lista kimarad; egy előadó elrejtése az albumait és lejátszási listáit is eltávolítja.

## Mi számít hallgatásnak

Egy dal lejátszásonként egyszer számít, miután **a fele** (vagy hosszú daloknál **négy perc**) ténylegesen lejátszódott — a közepére ugrás nem számít, és a 30 másodpercnél rövidebb dalok soha. A podcast-epizódok nem számítanak.

A hallgatások a szerveren tárolódnak, így amit a telefonodon játszol, az az asztali gépeden is formálja a javaslatokat. Az újrakezdéshez nyisd meg az **Elrejtett előadók → Hallgatási előzmények törlése** lehetőséget; a könyvtárad és a kedvelt dalaid változatlanul maradnak.

## Előadók elrejtése

A javaslat **⋯ → Nem érdekel** lehetősége véglegesen elrejti az adott előadót a Felfedezésből (a megjelenő értesítésen van **Visszavonás**). Ha egy előadót még azelőtt el akarsz rejteni, hogy javasolnák — olyat, akiről egyszerűen nem akarsz hallani —, nyisd meg az **Elrejtett előadók** oldalt, és írd be a nevet.

Ugyanez a lista minden elrejtett előadót mutat, a **Megjelenítés újra** gombbal visszavehetsz egyet. A neveket a kis- és nagybetűk, valamint a fájlnévben nem szereplő karakterek figyelmen kívül hagyásával egyezteti, így az `AC/DC` elrejtése az `ACDC`-t is elrejti.

## Jó tudni

- **A javaslatok egy hétig gyorsítótárban maradnak.** A Deezer és a Spotify válaszai minden előadódhoz 7 napig megmaradnak, így a Felfedezés újbóli megnyitása azonnali, és nem kerül egy kör kérésbe. A **Frissítés** a legfrissebb könyvtáraddal, kedveléseiddel és hallgatásaiddal újrarangsorol; az az előadó, akinek letelt a hete, újra le lesz kérdezve.
- **Ha a Deezer nem érhető el** (vagy korlátozza a kéréseket) néhány előadódnál, az oldal így is megmutatja, amit fel tudott építeni, és jelzi, hogy a lista a szokásosnál rövidebb — próbáld később újra. Egy sikertelen lekérdezést soha nem jegyez meg „nincs hasonló előadó”-ként.
- **Egy előadó, akit a Deezer nem ismer**, egyszerűen nem ad hozzá semmit; addig nem keresi meg újra, amíg le nem telik a hete.
- A szerveredről csak az előadók és albumok *nevei* kerülnek ki (Deezer- és Spotify-keresésként). Semmi sem kerül sehová arról, mit játszol.

## API

Lásd a [Felfedezés](../api-reference.md#discover) részt az API-referenciában.
