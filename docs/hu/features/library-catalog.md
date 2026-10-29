---
icon: lucide/library
---

# Könyvtárkatalógus és útvonal-szinkronizálás

A Downtify egy kis **katalógust** vezet a `/downloads` alatti fájlokról (a slskd mappájáról, ha a [slskd-fájlok helyben maradnak](slskd-navidrome.md#leave-files-in-place), és a Beállításokban hozzáadott [extra mappákról](external-library.md)), hogy a Könyvtár oldal, a lejátszó, az M3U-exportálás, a Navidrome-szinkronizálás és a duplikátumészlelés következetes maradjon, amikor fájlok mozognak vagy a lejátszási listák bővülnek.

## Mi tárolódik

| Tároló | Hely | Cél |
|-------|----------|---------|
| **Számindex** | `/data/downtify_library.db` | Spotify-számazonosítókat rendel könyvtárútvonalakhoz, hogy a már lemezen lévő számot fel lehessen ismerni |
| **Lejátszásilista-katalógus** | `/data/downtify_library.db` | Mely számok tartoznak az egyes letöltött Spotify-lejátszási listákhoz |
| **Lejátszásilista-letöltések** | `/data/downtify_library.db` | Követett Spotify-lejátszásilista-letöltések és a Spotify-számlistáik gyorsítótára |
| **Navidrome-index** | `/data/downtify_library.db` | Navidrome-dalazonosítók fájlonként |
| **Könyvtár-metaadat-gyorsítótár** | `/data/downtify_library.db` | Cím, előadó, album, albumelőadó, számsorszám, év, hossz és borítóméret fájlonként a `GET /tracks` számára, csak akkor olvassa újra, ha egy fájl módosítási ideje vagy mérete változik |
| **Feljavítási futások** | `/data/downtify_library.db` | A [Könyvtár feljavítása](library-upgrade.md) sora és hogy mikor ellenőrizték utoljára az egyes számokat, hogy egy futás túlélje az újraindítást |
| **Útvonal-beolvasási gyorsítótár** | RAM, plusz egy pillanatkép a `/data/downtify_library.db` fájlban | A `GET /tracks` összevont sorai, a lejátszásilista-listák és az útvonalpárok. A felületi útvonalak ezt a pillanatképet szolgálják ki a lemez bejárása nélkül. Minden befejezett letöltés **azonnal beleolvad a pillanatképbe** (hogy egy új előadó várakozás nélkül megjelenjen). Egy törlés **azonnal kiveszi ezeket a fájlokat a pillanatképből** (hogy egy album várakozás nélkül eltűnjön a rácsból). A teljes fabejárás a háttérben fut néhány másodperccel azután, hogy a letöltési sor tétlenné válik — nem rögzített időzítőn. A `GET /list?refresh=true` eldobja a pillanatképet, és most újra beolvas. |
| **Elrejtett elemek** | `/data/downtify_library.db` | Azok a dalok, albumok és előadók, amelyeket egy admin [elrejtett a felhasználók elől](users.md#hiding-from-users) |
| **Borító-gyorsítótár** | `/data/cover_cache` (opcionális) | Kinyert borítóképek a `GET /cover` számára |

A fájlokat mozgatások során egy **tartalomkulcs** egyezteti — a fájl nevének és méretének hash-e. Egy fájl másik mappába mozgatása megtartja a kulcsát; egy másik fájllal való lecserélése újat ad neki.

## Beállítások → Könyvtár

### Borítók gyorsítótárazása lemezen

Bekapcsolva a Downtify a kinyert borítóképeket a `/data/cover_cache` alatt tartja, hogy a Könyvtár és a lejátszó ne olvassa újra a címkéket minden bélyegképhez. Bármikor biztonságosan kikapcsolható; csak lemezterületbe kerül.

### Könyvtárútvonalak javítása

Használd, miután a Downtifyon kívül **fájlokat mozgattál vagy neveztél át a lemezen**, vagy kézzel töröltél.

1. Nyisd meg a **Beállítások → Könyvtár → Könyvtárútvonalak javítása** oldalt.
2. A Downtify beolvassa a könyvtármappákat, és:
    - **frissíti az útvonalakat** a számindexben és a lejátszásilista-katalógusban, ha egy fájl már nem ott van, ahol volt, de ugyanaz a fájl (azonos tartalomkulcs) máshol megtalálható;
    - **eltávolítja az elavult bejegyzéseket** a már nem létező fájlokról;
    - **indexeli** a tartalomkulcsok megjelenése előtt tárolt régebbi bejegyzéseket;
    - **követi a [kedvelt dalokat](liked-songs.md#keeping-likes-in-step-with-the-files)** az új helyükre.
3. Ha az **M3U létrehozása** és/vagy a **Listák létrehozása a Navidrome-ban** be van kapcsolva, az érintett lejátszási listák újraíródnak.

Csak akkor fut, amikor megnyomod a gombot (vagy meghívod a `POST /api/library/reconcile` végpontot) — soha nem ütemezetten.

### Meglévő zenei mappák

Egy olyan gyűjtemény lejátszásához, amelyet a Downtify nem töltött le, add hozzá a mappákat a **Beállítások → Könyvtár** alatt, és nyomd meg a **Mappák szinkronizálása** gombot. A fájlok a lemezen maradnak; a címkék beolvasódnak, az előadók pedig egyeztetődnek. Lásd: [Meglévő zenei mappák](external-library.md).

::: warning
Egy lejátszási lista újraírása törli azokat a könyvtárfájlokat, amelyek címkéi nyilvánvalóan nem egyeznek azzal a Spotify-számmal, amelyhez regisztrálva vannak — lásd: [slskd és Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Törlések és mozgatások
A számok törlése a **Könyvtár** oldalról már megtisztítja a katalógust, és a háttérben újraírja az érintett M3U-fájlokat és Navidrome-listákat, így utána nincs mit javítani.
:::

## Könyvtár oldal

A Könyvtár oldalnak négy füle van — **Albumok**, **Előadók**, **Lejátszási listák** és **Számok**:

- Az **albumok, előadók és lejátszási listák** borítórácsként vagy tömör listaként jelennek meg (a váltó megjegyződik), szövegszűrővel és rendezéssel a legutóbb hozzáadott, név, előadó, év vagy a számok száma szerint. Az albumok és előadók az egyes fájlok címkéiből épülnek fel (albumelőadó, album, év), így nem függenek attól, hogyan vannak a fájlok a lemezen szervezve. Az a szám, amelynek albumelőadója `Various Artists`, az előadócímke szerint csoportosul, így az olyan duónevek, mint a `Zé Neto & Cristiano`, ezen a néven jelennek meg. Az album-címke nélküli szám a Számok között és az előadója alatt jelenik meg, nem az Albumok között.
- A **lejátszási listák** a letöltött, [M3U-fájllal](m3u-export.md) rendelkező listák, a **Új lista** paranccsal létrehozott (szerkeszthető) listáid, plusz a követett [lejátszásilista-letöltések](slskd-navidrome.md#playlist-downloads), amelyeknek még nincs M3U-juk. Az importált Spotify-/YouTube-lejátszási listák csak olvashatók maradnak, amíg [le nem választod](#detach-an-imported-playlist) őket. A listák, amelyeket mások [megosztanak veled](users.md#sharing-playlists), a rács alatt szerepelnek, a sajátjaidtól elkülönítve. Miután [kedveltél](liked-songs.md) egy dalt, a *Kedvelt számok* kerül elsőként a listára. Az általad létrehozott lejátszási lista legfeljebb négy számborítóból álló mozaikot használ; az importáltak megtartják az M3U-val mentett képet.
- A **Számok** egy rendezhető táblázat (cím, album, formátum, hozzáadás dátuma, hossz) szövegszűrővel, formátumszűrővel és jelölőnégyzetekkel — kattints egyre, majd Shift+kattintás egy másikra egy tartomány kijelöléséhez. Rendezd oszlopfejlécre kattintva, vagy a táblázat feletti **Rendezés** menüvel (telefonon ez az egyetlen mód, ahol a fejlécek rejtettek): legutóbb hozzáadott vagy legrégebbi elöl, cím, előadó vagy album A–Z vagy Z–A, leghosszabb vagy legrövidebb elöl. A választás megjegyződik.

Egy lejátszási lista daljainak ugyanaz a **Rendezés** menüje van, a választékhoz hozzáadott **Lejátszási lista sorrendje** (a lista saját sorrendje, amellyel indul) lehetőséggel; az oszlopfejlécre kattintás is működik. A **Lejátszás** és a dallista az általad választott sorrendet követi, és a választás minden lejátszási listánál megjegyződik.

Egy album, előadó vagy lejátszási lista megnyitása a számait mutatja **Lejátszás**, **Keverés**, **Hozzáadás a sorhoz** és **Letöltés ZIP-ként** gombokkal. Az általad létrehozott lejátszási listának van még **Számok hozzáadása**, **Átnevezés** és **Megosztás…** parancsa is (lásd: [lejátszási listák megosztása](users.md#sharing-playlists)); az importáltnak **Megosztás…** és **Leválasztás a forrásról** (lent); egy letöltött lejátszási lista oldala megmutatja, hány száma van letöltve, a hiányzókat a **Hiányzók letöltése** gombbal sorolja fel, és felkínálja az **Új számok figyelése** lehetőséget. A **Lista törlése** a **⋯** menüben van: az importált listák a hangot törlik; az általad létrehozott lista csak a listát távolítja el.

### Keresés egy listában

Egy hosszú lista csak a képernyőn látható számokat rajzolja ki, ezért a böngésző saját keresése (`Ctrl` + `F`) nem látja a többit. A számok fölötti **Keresés ebben a listában** mező mindegyikben keres – cím, előadó, album és fájlnév alapján, kis- és nagybetűtől és ékezetektől függetlenül. Egy lista oldalán a `Ctrl` / `⌘` + `F` ebbe a mezőbe teszi a kurzort (a mezőben újra megnyomva a böngésző keresése jön), az `Esc` pedig kiüríti.

Mellette szűrők szűkítik a listát. Mindegyik mutatja, hány szám tartozik hozzá, és csak akkor jelenik meg, ha van ilyen:

| Szűrő | Mit mutat |
|-------|-----------|
| **Mind** | A lista összes letöltött számát |
| **Hiányzó** | A forráslista azon számait, amelyek még nincsenek a könyvtárban (Spotify-listák letöltésénél), a letöltésük állapotával – a szűrő kiválasztásakor a Spotify-on néz utána |
| **Sikertelen** | Azokat a hiányzó számokat, amelyek letöltése nem sikerült, mindegyiket újrapróbálás gombbal – miután a **Hiányzó** lekérdezése megtörtént |
| **YouTube Music**, **Soulseek (slskd)**, **Deemix**… | Az adott forrásból letöltött számokat. A Downtify ezt mostantól megjegyzi a letöltött számoknál; a régebbiek **Ismeretlen forrás** alá kerülnek, kivéve a helyükön hagyott slskd-fájlokat és a saját mappáidból származó számokat |
| **Nincs a Navidrome-ban** | Bekapcsolt [Navidrome-szinkronizálásnál](slskd-navidrome.md) azokat a számokat, amelyeket a Downtify még nem párosított Navidrome-számmal |

A keresés és egy szűrő együtt működik, alattuk pedig látszik, hány szám jelenik meg. Minden szám megtartja a sorszámát a listában, a rendezés, a lejátszás és a számok menüje pedig a megjelenített számokra vonatkozik.

### Importált lejátszási lista leválasztása

A Spotify- vagy YouTube Music-hivatkozásból importált lejátszási lista nem szerkeszthető, mert a Downtify szinkronban tartja a forrásával. Egy rendbetételéhez — kivenni egy dalt, ami nem oda tartozik, hozzáadni egyet, ami igen — nyisd meg, és válaszd a **Leválasztás a forrásról** lehetőséget. Olyan lejátszási listává válik, mint amilyeneket te hozol létre: a dalai és a tulajdonosa változatlanok maradnak, és megkapod a **Számok hozzáadása**, **Átnevezés** és a dalok eltávolításának lehetőségét. Cserébe a forrásához fűző kapocs megszakad: többé nem frissül a Spotifyból vagy a YouTube Musicból, a [Lejátszási lista figyelő](playlist-monitor.md)-megfigyelése (ha volt) megszűnik, és a „hiányzó dalok” követése is megszűnik. A már letöltött dalokhoz soha nem nyúl hozzá, a képe pedig az első szerkesztésedig megmarad, amikor a daljaiból készült mozaik váltja fel. A leválasztás az alkalmazásból nem vonható vissza; a hivatkozás újbóli letöltése új importált lejátszási listát hoz létre.

Minden fiók ugyanazt a könyvtárat látja: amit egy admin [elrejt a felhasználók elől](users.md#hiding-from-users), az számukra kimarad, az admin pedig mindent lát, az elrejtetteken áthúzott szemmel. Az adminok egy dal, album vagy előadó `…` menüjéből, vagy a **Számok** kijelölési sávjából rejtenek el és jelenítenek meg.

A **Letöltés ZIP-ként** a kijelölt számokat egyetlen ZIP-ként menti arra az eszközre, amelyről böngészel, megtartva a mappaszerkezetüket — hasznos, ha a Downtify otthoni szerveren fut, és egy köteg számot helyben szeretnél. Kombináld a **Összes kijelölése** gombbal, hogy mindent elvigyél, amit az aktuális szűrő mutat. Az archívum a letöltés közben épül, így semmi nem íródik a szerver lemezére, és letöltésenként 2000 számra korlátozott.

## API

| Metódus | Útvonal | Leírás |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Könyvtárútvonalak, az útvonal-beolvasási gyorsítótár megkerülésével |
| `GET` | `/api/library/summary` | A kezdőlap számai és a legutóbbi albumok, a teljes számlista nélkül |
| `GET` | `/api/library/albums` | Albumcsempék (számok + borítófájl), minden szám nélkül |
| `GET` | `/api/library/artists` | Előadócsempék (számok + borítófájl) a Könyvtárhoz és a Felfedezéshez |
| `GET` `POST` | `/api/library/visibility` | Adminok: mi van elrejtve a felhasználók elől, és elemek elrejtése / megjelenítése |
| `POST` | `/api/library/lookup` | Könyvtársorok a már letöltött keresési/hivatkozás-dalokhoz |
| `GET` | `/tracks` | Könyvtári számok címkékkel. A `?playlist=`, `?artist=`, `?album=`, `?q=` és `?limit=` részhalmazt ad vissza |
| `GET` | `/media/{path}` | Egy könyvtárfájlt szolgál ki, a `slskd/…` és `ext/…` útvonalakat is beleértve |
| `GET` | `/playlist-cover?file=…` | Egy lejátszási lista saját [borítóját](playlist-cover-art.md) szolgálja ki, amelyet a `/playlists` `cover`-ként jelez |
| `POST` | `/api/library/archive` | ZIP-et készít elő a kijelölt számokból (egyszer használatos jegyet ad vissza) |
| `GET` | `/api/library/archive/{token}` | Streameli azt a ZIP-et a böngészőnek |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Törli egy importált lejátszási lista számait, M3U-ját és katalógusát — vagy csak egy általad létrehozott lista M3U-ját |
| `POST` | `/api/library/playlists` | Üres, szerkeszthető lejátszási listát hoz létre |
| `POST` | `/api/library/playlists/tracks` | Könyvtárfájlokat ad hozzá vagy távolít el egy általad létrehozott listán |
| `POST` | `/api/library/playlists/rename` | Átnevez egy általad létrehozott listát |
| `PUT` | `/api/library/playlists/visibility` | [Megoszt egy lejátszási listát](users.md#sharing-playlists), amelynek te vagy a tulajdonosa, csak megtekintésre |
| `POST` | `/api/library/playlists/copy` | Elmenti egy megnyitható lejátszási lista másolatát szerkeszthető saját listaként |
| `POST` | `/api/library/playlists/detach` | Egy importált lejátszási listát szerkeszthetővé alakít |
| `POST` | `/api/library/reconcile` | Kijavítja a könyvtárútvonalakat, majd frissíti az M3U-/Navidrome-listákat |
| `POST` | `/api/library/external/sync` | Elindítja az extra zenei mappák háttérbeli beolvasását |
| `GET` | `/api/library/external/sync` | Futó extra mappa-szinkronizálás, vagy az utolsó befejezett napló |
| `POST` | `/api/library/external/unmap` | Kivesz egy extra mappát a könyvtárból a hang törlése nélkül |
| `GET`/`POST` | `/api/library/upgrade…` | Beolvassa és javítja a már letöltöttet — lásd: [Könyvtár feljavítása](library-upgrade.md#api) |

A kérések és válaszok alakjáért lásd az [API-referenciát](../api-reference.md#library).
