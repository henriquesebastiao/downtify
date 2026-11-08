---
icon: lucide/shield-alert
---

# Explicit jelölés

Az explicit szöveget tartalmazó szám — gyerekeknek nem való nyelvezettel — egy apró **E** jelet visel a címe mellett, mint a Spotifyon. Mindenhol megjelenik, ahol a számmal találkozol, letöltés előtt és után is, és a fájllal marad.

## Hol látod

- **Keresési találatok, beillesztett hivatkozások, Toplisták és a Kereső** — minden olyan számnál, amelyet a szolgáltatás explicitnek jelöl. Letöltés előtt tudod.
- **A Könyvtár** — a Számok fülön, az album-, előadó- és lejátszásilista-oldalakon, valamint a „számok hozzáadása” választóban.
- **A lejátszó** — a cím mellett a lejátszósávban, a **Most szól** nézetben és a **Következik** listában.

Vidd az egeret az **E** fölé (vagy hagyd, hogy egy képernyőolvasó felolvassa), hogy lásd: „Explicit”.

## Honnan jön a jelölés

Azt a szolgáltatás dönti el, ahonnan letöltesz: a Spotify, a YouTube Music és a Deezer egyaránt jelöli az explicit számait, a Downtify pedig azt használja, amit az általad választott mond. Amikor a Downtify YouTube Music-ról tölt le egy számot, a jelölés a **ténylegesen letöltött videót** írja le: ha a szám explicit a Spotifyon, de a Downtify egy tisztított változatot illesztett, a fájl nem kap jelölést, és ha a Spotify tisztának mondja, de az illesztett változat explicit, akkor kap.

Az a szám, amelyet a szolgáltatás nem jelöl, egyáltalán nem kap jelölést — ami nem ugyanaz, mint a tanúsítottan tiszta, és a Downtify soha nem ír „tiszta” jelölést.

## A fájlban

A jelölés a fájl címkéibe íródik, ahogy az iTunes teszi, így a médiaszerverek és lejátszók, amelyek értik, szintén használhatják. A Navidrome pontosan ezeket a címkéket olvassa egy szám explicit állapotaként.

| Formátum | Címke |
|--------|-----|
| MP3 | `ITUNESADVISORY` szöveges keret (`TXXX`), értéke `1` |
| FLAC, OGG, OPUS | `ITUNESADVISORY` megjegyzés, értéke `1` |
| M4A | `rtng` atom, értéke `1` |

A már meglévő fájlokat ugyanígy olvassa: amit az iTunes, a MusicBrainz Picard vagy más címkéző `1`-gyel (vagy a régebbi `4`-gyel) jelölt, az is mutatja az **E**-t, a [további mappák](external-library.md) számait is beleértve.

::: info Ezen verzió előtt letöltött számok
Azok a fájlok, amelyeket a Downtify a jelölés megjelenése előtt írt, semmit sem tartalmaznak a címkéikben, ezért nem mutatnak **E**-t, még ha a szám explicit is. A megjelöléshez töltsd le újra a számot a [Hang cseréje](replace-audio.md) funkcióval vagy elölről. Egy fájl megtartja a jelölését, amikor a [Könyvtár javítása](library-upgrade.md) vagy a Hang cseréje újraírja: a jelölés csak hozzáadódik, soha nem törlődik.
:::

A frissítés utáni első könyvtárbetöltéskor a Downtify újra beolvassa minden fájl címkéit, hogy megkeresse a jelölést, ahogy akkor is tette, amikor megtanulta megjeleníteni a kodeket és a műfajt. Egy lassú lemezen lévő nagy könyvtárnál ez egyszer eltart egy darabig.

## Alkalmazásfejlesztőknek

A [mobilkliens-szerződés](../mobile-client-contract.md) és az [API-referencia](../api-reference.md#get-tracks) leírja az `explicit` mezőt: `true` az explicit számoknál, egyébként hiányzik.
