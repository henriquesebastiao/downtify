---
icon: lucide/share-2
---

# slskd és Navidrome

Két opcionális integráció saját üzemeltetésű könyvtárakhoz:

- **[slskd](https://github.com/slskd/slskd)** — tölts le számokat a Soulseek hálózatról a saját slskd szervereden keresztül, a YouTube Music és a YouTube melletti extra hangforrásként.
- **[Navidrome](https://www.navidrome.org/)** — tükrözd a letöltött lejátszási listákat a Navidrome-ba, hogy bármely Subsonic-kliensben megjelenjenek.

Mindkettő alapértelmezetten ki van kapcsolva, és a **Beállítások** között konfigurálható.

## Hangforrások és tartalék sorrend

A **Beállítások → Hangforrások** egy rendezett lista. Koppints egy forrásra a hozzáadásához vagy eltávolításához; ha egynél több van kijelölve, a nyilakkal rendezd át őket. Minden szám ebben a sorrendben próbálja a forrásokat, és az első olyannál áll meg, amely hangot ad:

| Forrás | Mit csinál |
|--------|-------------|
| **YouTube Music** | Az alapértelmezett. A YouTube Musicban keres, és a hagyományos YouTube-ra esik vissza, ha nincs elfogadható találat — lásd: [Hogyan működik](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Csak a hagyományos YouTube-on keres. |
| **SoundCloud** | Alapértelmezetten ki van kapcsolva. A SoundCloudon keres, és egy beillesztett SoundCloud link pontos számát tölti le — [SoundCloud](soundcloud.md). |
| **slskd** | A slskd-n keresztül keres a Soulseeken, és letölti a legjobban egyező fájlt. |

A slskd engedélyezése a lista elejére teszi. Ha a slskd lesz az egyetlen forrás, a YouTube Music és a YouTube akkor is ki lesz próbálva utána, így egy olyan szám is letöltődik, amelyet a slskd nem talál. A letöltési sor megmutatja, melyik forrás szolgálta ki az egyes számokat.

## slskd

### Beállítás

1. Futtasd a slskd-t, és hozz létre egy API-kulcsot a Downtifynak (lásd a slskd dokumentációját).
2. Csatold a slskd letöltési mappáját a Downtify konténerébe — ugyanazt a gazdagép-mappát, amelybe a slskd ír. Lásd: [Docker Compose → slskd-vel](../getting-started/docker-compose.md#with-slskd-soulseek).
3. A **Beállítások → slskd (Soulseek)** alatt engedélyezd a slskd-t, és töltsd ki:
    - **slskd URL** — pl. `http://slskd:5030`, ha a két konténer közös Docker-hálózaton van.
    - **API-kulcs**.
    - **Letöltési mappa** — az az útvonal *a Downtify konténerén belül*, ahová ez a mappa csatolva van (alapértelmezetten `/slskd`), nem a gazdagép útvonala.

A mentés hibaüzenettel elutasításra kerül, ha a slskd URL vagy API-kulcs nélkül van engedélyezve.

### A kapcsolat tesztelése

Nyomd meg a mezők alatti **Kapcsolat tesztelése** gombot, hogy mentés előtt ellenőrizd őket — azt használja, ami az űrlapba van írva, mentve vagy sem, és semmit nem változtat. Ezt jelzi:

| Eredmény | Mit jelent |
|--------|---------------|
| **Kapcsolódva a slskd 0.21.4-hez.** | A cím helyes, és az API-kulcsot elfogadták |
| **A slskd be van jelentkezve a Soulseekbe.** / **nincs bejelentkezve** | Hogy maga a slskd be van-e jelentkezve a Soulseek hálózatba. Ha nincs, a keresések semmit nem találnak, amíg be nem jelentkezik — figyelmeztetés, mert maguk a beállítások helyesek |
| **A Downtify olvasni tudja a `/slskd` mappát.** / **nem tudja olvasni** | Hogy a fenti letöltési mappa létezik-e *ebben* a konténerben, és olvasható-e. A figyelmeztetés szokásos oka egy nem csatolt mappa — lásd: [Beállítás](#setup) |
| **A slskd elutasította az API-kulcsot.** | A szerver válaszolt, de nem erre a kulcsra |
| **Nem érhető el … / nem válaszolt időben.** | Rossz cím vagy port, a szerver le van állva, vagy a Downtify konténerből nem érhető el |
| **Nem úgy néz ki, mint a slskd.** | Valami válaszolt, de nem a slskd — gyakran rossz port, vagy a címből hiányzó alapútvonal |
| **A HTTPS-tanúsítványban nem bíznak.** | Használj `http://`-t a saját hálózaton, vagy megbízható hatóságtól származó tanúsítványt; a Downtify nem hagyja ki a tanúsítvány-ellenőrzést |

Bármely mező szerkesztése törli az utolsó eredményt, mert az már nem azt írja le, ami az űrlapban van. A gomb le van tiltva, amíg a cím és a kulcs ki nincs töltve.

### Hogyan egyezik meg egy szám

A Downtify a szám címével és előadójával keres a slskd-ben, és a találatokat aszerint rangsorolja, mennyire illeszkedik a fájlnév és a hossz a számhoz. Egyformán jó találatok között az MP3-at, majd a FLAC-et részesíti előnyben, és kihagyja azokat a fájlokat, amelyek 256 kbps alatti bitrátát jeleznek. Legfeljebb öt jelöltet próbál ki egymás után. Amikor egy átvitel befejeződik, a Downtify a megtartás előtt ellenőrzi a fájl címkéit és hosszát a számhoz képest.

Ha nem akad semmi elfogadható, az átvitel nem fejeződik be a **Teljes időkorlát** alatt, vagy a távoli félnél sorban állva haladás nélkül tovább áll, mint a **Sorban állási időkorlát**, a Downtify a következő hangforrásra lép.

### Fájlok helyben hagyása

Ha a **slskd-fájlok helyben hagyása** be van kapcsolva (alapértelmezés), a letöltött fájl a slskd mappájában marad: a Downtify ott helyben beleírja a metaadatokat, a borítót és a dalszöveget, és `slskd/…` útvonallal regisztrálja a könyvtárban. A Könyvtár, a lejátszó és az M3U-fájlok ezt az útvonalat használják, és a `/media/slskd/…` útvonalon szolgálódik ki.

Kapcsold ki, hogy a fájl helyette a többi letöltésed mellé másolódjon, a fájlnév-sablonod és a [fájlszervezés](file-organization.md) beállításai szerint.
Maga az átvitel az slskd mappában marad; a [Tárhely és használat](storage-usage.md#the-library-not-its-working-copies) ezeket a másolatokat a könyvtártól külön, *slskd munkapéldányokként* számolja, így látod, mennyi helyet foglalnak.

::: info
A slskd-fájlok megtartják az eredeti formátumukat — nem kódolódnak át a Beállításokban választott formátumra.
:::

## Navidrome

### Beállítás

1. Győződj meg róla, hogy a Navidrome zenemappája tartalmazza a Downtify letöltési mappáját (és a slskd mappáját, ha a slskd-fájlokat helyben hagyod). A Navidrome csak azután tud számokat lejátszási listához adni, hogy átvizsgálta őket.
2. A **Beállítások → Navidrome** alatt engedélyezd a Navidrome-ot, és add meg az URL-jét, felhasználónevét és jelszavát.
3. Opcionálisan adj meg egy **admin** felhasználónevet és jelszót. A Downtify ekkor megkéri a Navidrome-ot, hogy az új számok egyeztetése előtt vizsgálja át a könyvtárat, ahelyett hogy a Navidrome saját ütemezett vizsgálatára várna.

### A kapcsolat tesztelése

Nyomd meg a mezők alatti **Kapcsolat tesztelése** gombot, hogy mentés előtt ellenőrizd őket — azt használja, ami az űrlapba van írva, mentve vagy sem, és semmit nem változtat. Ezt jelzi:

| Eredmény | Mit jelent |
|--------|---------------|
| **Kapcsolódva a navidrome 0.53.3-hoz.** | A cím helyes, és a felhasználónevet és a jelszót elfogadták |
| **Ez a fiók indíthat könyvtárvizsgálatot.** | A vizsgálatokhoz használt fiók admin. Ez az általad megadott admin felhasználónév, vagy a normál, ha üresen hagytad |
| **Ez a fiók nem indíthat könyvtárvizsgálatot.** | A Navidrome csak adminoknak engedi a vizsgálat indítását, és nem mondja meg, amikor a Downtify megpróbálja — az új dalok egyszerűen későn jelennek meg. Add meg egy admin felhasználónevét és jelszavát |
| **Az admin fiók nem admin.** | A megadott admin bejelentkezés működik, de egy normál felhasználóé |
| **A Navidrome elutasította az admin felhasználónevet vagy jelszót.** | A vizsgálati fiók bejelentkezése hibás; a fő bejelentkezés külön jelződik |
| **A Navidrome elutasította a felhasználónevet vagy jelszót.** | A szerver válaszolt, de nem erre a bejelentkezésre |
| **Nem érhető el … / nem válaszolt időben.** | Rossz cím vagy port, a szerver le van állva, vagy a Downtify konténerből nem érhető el |
| **Nem úgy néz ki, mint a Navidrome.** | Valami válaszolt, de nem a Subsonic API — gyakran rossz port, vagy a címből hiányzó alap-URL |
| **A HTTPS-tanúsítványban nem bíznak.** | Használj `http://`-t a saját hálózaton, vagy megbízható hatóságtól származó tanúsítványt; a Downtify nem hagyja ki a tanúsítvány-ellenőrzést |

A vizsgálati jogosultságokat csak lekérdezi — a teszt soha nem indít vizsgálatot. Bármely mező szerkesztése törli az utolsó eredményt, és a gomb le van tiltva, amíg a cím, a felhasználónév és a jelszó ki nincs töltve.

::: info Semmi sem megy vissza az oldalnak
A válasz csak azt hordozza, amit találtak — egy verziót, egy útvonalat, egy állapotot — soha a jelszavadat vagy a Downtify kérését.
:::

### Lejátszási lista szinkronizálása

A tükrözést adminok állítják be (Beállítások → Navidrome); a normál fiókok nem hozhatnak létre tükröket, de a letöltéseiket mindenki máséhoz hasonlóan tükrözi a program, ha az integráció be van kapcsolva.

Ha a **Listák létrehozása a Navidrome-ban** be van kapcsolva, a Downtify ugyanazon a néven létrehoz (vagy frissít) egy Navidrome-lejátszási listát, miután:

- egy Spotify-lejátszási lista letöltése befejeződik,
- a [Lejátszási lista figyelő](playlist-monitor.md) egy átfésülése számokat ad hozzá,
- számokat töröltek a Könyvtárból, vagy [kijavították a könyvtárútvonalakat](library-catalog.md#fix-library-paths).

A számokat előbb útvonal, majd címkék alapján egyezteti a Navidrome-dalokkal. A **Navidrome-listák nyilvánossá tétele** a lista láthatóságát szabályozza a Navidrome-ban.

::: warning A lejátszási listához nem illő címkéjű fájlok törlődnek
Amikor egy lejátszási lista frissül (törlések, **Könyvtárútvonalak javítása** vagy egy már teljes listán a **Hiányzók letöltése** után), egy Spotify-számhoz regisztrált könyvtárfájl **törlődik a lemezről**, ha a beágyazott címe/előadója nyilvánvalóan nem egyezik azzal a számmal — a Downtify rossz letöltésnek tekinti. Tartsd észben, ha kézzel szerkeszted a címkéket.
:::

### Lejátszási lista borítója

Nincs mit beállítani: ha a [Lejátszási lista borítójának mentése](playlist-cover-art.md) be van kapcsolva, a Navidrome felveszi a `.jpg` fájlt, amelyet a Downtify a lista M3U-ja mellé ír, **kísérőképként (sidecar)** — a saját módszere a listák képének feloldására —, amennyiben a zenemappája lefedi azt a fájlt. A Downtify ehhez nem hív API-t.

## Lejátszásilista-letöltések

A **Könyvtár** oldal a Downtifyon át letöltött Spotify-lejátszási listákat a **Lejátszásilista-letöltések** alatt sorolja fel. Bontsd ki, hogy listánként lásd, hány szám van a könyvtáradban a Spotify aktuális számlistájához képest. Innen:

- **Hiányzók letöltése** — csak a még nem a könyvtáradban lévő számokat állítja sorba.
- **Lejátszhatod** a már letöltött számokat.
- Kibonthatsz egy listát, hogy lásd és letöltsd az egyes hiányzó számokat.
- **Törölheted** a listát — lásd lent.

### Lejátszási lista törlése

Egy lejátszási lista törlése (ebből a panelből, vagy a Könyvtár listaszűrője melletti **Lista törlése** paranccsal) a lemezről eltávolít minden hozzá regisztrált számot — **azokat is, amelyeket más listák is tartalmaznak** — valamint az M3U-fájlját és a mellé mentett [borítót](playlist-cover-art.md), és megszünteti a követését. A többi lista, amely osztozott ezeken a számokon, az M3U-ját és a Navidrome-listáját a háttérben újraírja.
