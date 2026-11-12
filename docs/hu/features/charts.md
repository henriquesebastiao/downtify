---
icon: lucide/trending-up
---

# Toplisták

A **Toplisták** a Deezer saját globális listáját mutatja — műfajszűrő nélkül, azt, ami éppen világszerte felkapott — Deezer-fiók vagy API-kulcs nélkül.

## Használata

Nyisd meg a **Toplisták** oldalt az oldalsávról (telefonon a **Továbbiak** lapról). Négy fül olvas ugyanabból a listából: **Számok**, **Albumok**, **Előadók** és **Lejátszási listák**.

- **Számok** — rangsorolt lista. Nyomj meg egyet (vagy koppints a sorára), hogy letöltés előtt teljes hosszában lejátszd a YouTube-ról, közvetlenül a beépített lejátszóban. Egy sor letöltése úgy működik, mint egy keresési találaté: a Downtify a YouTube Musicban (ha ott nincs, a hagyományos YouTube-on) keresi a szám címéhez, előadójához és hosszához legjobban illő találatot, ugyanazon az [illesztési folyamaton](../how-it-works.md) keresztül, mint bármely más letöltés. Miután egy szám letöltődött, a sora a könyvtáradból játssza le, nem streameli.
- **Albumok**, **Előadók** és **Lejátszási listák** — borítórácsok. Egyre kattintva feloldja ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)), pontosan úgy, mintha te magad illesztetted volna be azt a Deezer-hivatkozást a keresőmezőbe: betöltődik a számlistája, kiválasztásra és letöltésre készen.

## Miért töltődnek le (és játszódnak le teljes hosszban) a számok közvetlenül innen, míg az albumok, előadók és lejátszási listák előbb megnyitnak egy oldalt

Egy toplistás számnak nincs szüksége feloldási lépésre a letöltéshez: a Deezer már megadja a címét, az előadóját és az album nevét, ami elég a YouTube-on való kereséshez és illesztéshez, akárcsak egy szabad szöveges keresési találatnál. Egy albumnak, előadónak vagy lejátszási listának viszont kell — a hivatkozását számlistává alakítani —, ezért a kártyája ezt a feloldott oldalt nyitja meg ahelyett, hogy közvetlenül a rácsból töltene le. Egy számsor lejátszása teljes hosszban streamel a YouTube-ról (albumoknál, előadóknál és lejátszási listáknál soha) — ugyanaz a streamelés, amelyet minden számsor használ, csak a toplista címével és előadójával táplálva.

## Toplistás lejátszási lista figyelése vagy mentése

Minden lejátszásilista-kártya borítóján van egy **⋯** menü azzal a két dologgal, amit az oldala a letöltésen kívül kínál:

- Az **Új számok figyelése** létrehoz egy figyelést a [Lejátszási lista figyelőben](playlist-monitor.md#deezer-playlists), 6 óránkénti ellenőrzéssel: az első ellenőrzés letölti, ami most a listán van, a későbbiek azt, ami hozzákerül. Az intervallumot a **Figyelő** oldalon módosíthatod, és ott szüneteltetheted vagy állíthatod le a figyelést.
- A **Hozzáadás a lejátszási listáimhoz** megnyitja a listaválasztót a lista azon számaival, amelyek **már megvannak a könyvtáradban**, hogy hozzáadd őket valamelyik saját listádhoz vagy egy új, róla elnevezett listához. Semmi sem töltődik le, és a listád utána nem követi a toplistás listát — ehhez a letöltés gombot vagy az **Új számok figyelése** pontot használd. Ha egyik száma sincs még meg a könyvtárban, ezt jelzi.

## API

Lásd a [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) részt az API-referenciában.
