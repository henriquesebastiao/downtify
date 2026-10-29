---
icon: lucide/users
---

# Felhasználók és bejelentkezés

Mindenki, aki a Downtifyt használja, **felhasználónévvel és jelszóval** jelentkezik be, és minden embernek lehet saját fiókja. Egy admin a **Beállítások → Felhasználók** oldalon kezeli a fiókokat, és a **Beállítások → Tevékenység** oldalon látja, mit csinál mindenki.

## Első bejelentkezés

Egy új szervernek egy fiókja van:

| Felhasználónév | Jelszó |
|----------|----------|
| `admin` | `downtify` |

Jelentkezz be vele, és **változtasd meg a jelszót** a **Beállítások → Általános → Fiók** alatt: aki ismeri a Downtifyt, ismeri az alapértelmezett jelszót. Amíg nem teszed, a Downtify bejelentkezés után emlékeztet, és figyelmeztetést mutat a Beállításokban.

::: warning Változtasd meg az alapértelmezett jelszót, mielőtt kitennéd a szervert
Az alapértelmezett jelszó semmit nem véd. Változtasd meg, mielőtt a Downtifyt az otthoni hálózatodon kívülről elérhetővé teszed — és ott használj HTTPS-t (lásd: [Fordított proxy mögött](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Frissítés régebbi verzióról

Egy fiókok nélküli verziót futtató szerver ugyanazt az `admin` fiókot kapja, és a bejelentkezési oldal ezt egyszer megmondja — amíg egy admin be nem jelentkezik — a használandó felhasználónévvel és jelszóval:

- Ha a régi **Bejelentkezés megkövetelése** opció alatt beállítottál jelszót, az a jelszó továbbra is érvényes az `admin`-ra.
- Egyébként `downtify`.

A frissítés előtt bejelentkezett böngészők újra bejelentkeznek. A frissítés előtt párosított telefonok párosítva maradnak, és mostantól az `admin`-hoz tartoznak.

## Adminok és felhasználók

| | Admin | Felhasználó |
|---|---|---|
| Hallgatás, keresés, letöltés, kedvelés, Felfedezés, Listák, Finder, podcastok | ✓ | ✓ |
| Telefonalkalmazások párosítása (a saját fiókjukhoz) | ✓ | ✓ |
| Beállítások → Általános (saját fiók és preferenciák), Alkalmazások, Névjegy | ✓ | ✓ |
| Minden más beállítás (források, fájlok, címkék, Navidrome, könyvtár, szerver), a szerver átnevezése | ✓ | |
| [Saját lejátszási listák megosztása](#sharing-playlists) (csak megtekintés), nyilvánosak követése, másolatok mentése | ✓ | ✓ (ha az admin engedi) |
| Fájlok és lejátszási listák törlése (egy felhasználó csak [amit letöltött](#deleting-songs) és a saját listáit), saját lejátszási lista-megfigyelések és podcast-előfizetések kezelése, egy szám hangjának cseréje, előadófotók szerkesztése | ✓ | ✓ (csak a sajátját) |
| [Dalok, albumok és előadók elrejtése a felhasználók elől](#hiding-from-users) | ✓ | |
| Felhasználók kezelése, a tevékenységnapló megtekintése | ✓ | |

Az a felhasználó, aki adminhoz kötött dolgot próbál, üzenetet kap erről.

## A könyvtárad

A könyvtár közös: minden fiók látja minden dalt, amelyet bárki letöltött — a Könyvtárban, a letöltöttként jelölt keresési találatokban és egy párosított telefonon. A fájlok soha nem tárolódnak kétszer: ha ketten töltik le ugyanazt a dalt, az egyszer kerül a lemezre, mindkettejüknek egy-egy tulajdonossággal.

A kedvelések, a lejátszási listák (letöltöttek és a Könyvtárban létrehozottak) és a letöltési sor a tieid maradnak, hacsak nem vagy admin — vagy nem [osztasz meg egy listát](#sharing-playlists), hogy mások is lássák. A hallgatás közös — bárki lejátszhat, előnézhet vagy streamelhet bármely számot, és bármit hozzáadhat a saját listáihoz. Egy olyan szám kérése, amelyet valaki más már letölt, csatlakozik az ő feladatához, ahelyett hogy kétszer kérné le: egy sorbeli sor, egy letöltés és egy-egy tulajdonosság — mindenki, aki vár, látja a helyét a sorban.

A podcastok, a lejátszási lista-megfigyelések és a Felfedezés története ugyanígy működnek: minden fiók a saját műsoraira iratkozik fel, a saját listáit és előadóit követi, és a saját javaslatait tanítja. Egy admin minden fiók sorait látja. Maga a hallgatás közös marad — bárki lejátszhat, előnézhet vagy streamelhet bármely számot.

### Lejátszási listák megosztása

Egy lejátszási lista a tulajdonosa (és az adminok) számára privát, amíg a tulajdonosa meg nem osztja, a lista oldalán a **Megosztás…** paranccsal vagy a **⋯** menüben. A lejátszás már most is közös a fiókok között; ez csak arról szól, ki *láthat* egy listát. Minden lista megosztható a *Kedvelt számok* kivételével, az importáltakat is beleértve.

| Láthatóság | Ki látja |
|------------|-------------|
| **Privát** | Csak a tulajdonos és az adminok — az alapértelmezés |
| **Meghatározott személyek** | A tulajdonos által választott felhasználónevek |
| **Nyilvános** | Mindenki a szerveren |

Mások listái soha nem keverednek a sajátjaiddal. A Könyvtár **Lejátszási listák** füle két szakaszban sorolja fel őket a sajátjaid alatt, minden bejegyzés a tulajdonosával címkézve:

- **Velem megosztott** — neked név szerint címzett listák, mindig megjelennek. Egy frissen megosztott **Új** jelölést visel, amíg meg nem nyitod.
- **Nyilvános listák** — mindenki nyilvános listái, tulajdonos és név szerint rendezve, a fül szűrőjével kereshetők, mutatják a tulajdonost, a dalok számát és azt, hogy követed-e. A szakasz összecsukva indul, és teljesen elrejtheted a **Beállítások › Általános › Nyilvános listák megjelenítése** lehetőséggel (alapértelmezetten be van kapcsolva; a tied, mint a téma).

Az oldalsáv is mutat néhányat azokból, amelyeket veled megosztottak, és a követett nyilvános listákból.

**Mit tehet a megtekintő:** lejátszhat, kevert sorrendben játszhat, sorba állíthat, ZIP-ként letölthet (vagy telefon- vagy asztali alkalmazásba), **Követhet** egy nyilvános listát, hogy a listái között maradjon — akkor is, ha a *Nyilvános listák megjelenítése* ki van kapcsolva — és kövesse a tulajdonosa változtatásait, és **Másolatot menthet**: egy privát, szerkeszthető saját listát azokkal a dalokkal, amelyeket láthat. A megtekintő nem szerkesztheti, nevezheti át, törölheti, oszthatja meg vagy választhatja le más listáját. A könyvtárban létrehozott lista tulajdonosa azok közül, akikkel megosztja, néhányakat szerkesztővé tehet: ők számokat is hozzáadhatnak és eltávolíthatnak – lásd [Közösen szerkesztett listák](collaborative-playlists.md).

**A megosztás megszüntetése:** amikor a tulajdonos újra privátra állít egy listát, vagy töröl valakit a listáról, az azonnal kikerül az illető listái közül (követett vagy sem); a nyilvánosságát elvesztő lista már nem követett. A már elmentett másolatok megmaradnak annál, aki mentette. Egy megosztott lista átnevezése megosztva tartja; a törlése magával viszi a megosztást. Azok a dalok, amelyeket egy admin [elrejt a felhasználók elől](#hiding-from-users), számukra kimaradnak egy megosztott lista számai közül, mint mindenhol.

Egy admin az egészet kikapcsolhatja a **Beállítások › Könyvtár › A felhasználók megoszthatnak listákat** lehetőséggel (alapértelmezetten be van kapcsolva). Amíg ki van kapcsolva, minden megosztás rejtett, és senki nem oszthat meg vagy követhet — a megosztások visszatérnek, amikor újra bekapcsolják.

A párosított alkalmazások ugyanezeket a listákat kapják: a [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) megmondja, kié melyik és csak megtekinthető-e, a WebSocketen a `playlists_changed` pedig frissítésre szólítja őket.

### Elrejtés a felhasználók elől

Az adminok döntik el, mit látnak a többi fiókok. Minden mindenki számára látható, amíg egy admin el nem rejt valamit: egy **dalt**, egy egész **albumot** vagy egy egész **előadót**. Az elrejtett elemek kikerülnek a Könyvtárból, a keresés „a könyvtárban” jelöléseiből, a lejátszási listák számlistáiból és abból, amit egy párosított telefon szinkronizál — a felhasználóknak, nem az adminoknak.

- **A Könyvtárban** nyisd meg egy dal, album vagy előadó `…` menüjét, és válaszd az **Elrejtés a felhasználók elől** lehetőséget (vagy a **Megjelenítés a felhasználóknak** lehetőséget a visszavonáshoz). A Számok fülön jelölj ki több dalt, és használd az **Elrejtés a felhasználók elől** parancsot a kijelölési sávban.
- Az adminok továbbra is mindent látnak. Ami el van rejtve, egy kis áthúzott szemet visel, és a súgóbuboréka megmondja, miért: önmagában elrejtve, az albumával vagy az előadójával együtt.
- A **Beállítások › Felhasználók › Elrejtve a felhasználók elől** felsorol minden elrejtett előadót, albumot és dalt, mindegyik mellett **Megjelenítés a felhasználóknak** paranccsal.
- Egy elrejtett dal elrejtve marad, amikor másik mappába kerül, és amikor a [Könyvtár feljavítása](library-upgrade.md) vagy a [Hang cseréje](replace-audio.md) újraírja a fájlját. A fájl törlése elfelejti a szabályt.
- Egy albumszabály az album előadójára és címére illik, egy előadószabály pedig arra az előadóra, amely alatt a Könyvtár a dalt csoportosítja — ugyanazokra a nevekre, amelyeket a Könyvtár Albumok és Előadók fülei használnak.

::: info Az elrejtés arról szól, mi szerepel a listákon
Azt szabályozza, mit látnak a fiókok az alkalmazásban, nem azt, ki kérhet le egy fájlt, amelynek a címét már ismeri. Ne használd érzékeny fájlok védelmére.
:::

Az elrejtést és a megjelenítést a [tevékenységnapló](#activity) rögzíti.

### Dalok törlése

Egy dal törlése mindenki számára eltávolítja a lemezről, ezért követi azt, aki letöltötte. Egy admin bármit törölhet. Egy felhasználó törölhet egy általa letöltött dalt; ha valaki más is letöltötte ugyanazt a dalt, a törlés csak a saját igényéről mond le, és a dal a közös könyvtárban marad. Egy olyan dalt, amelyet senki nem töltött le fiókon keresztül (egy lejátszási lista figyelő átfésülése, egy fiókok előtti letöltés, egy [extra mappa](external-library.md)), csak admin törölhet. Egy saját lista törlése soha nem visz magával más fájljait.

### Fiókonkénti használat

A **Beállítások › Felhasználók** minden fiók alatt felsorolja, mit tart: számok és a méretük, kedvelések, lejátszási listák, megrendelt letöltések és a forgalom mindkét irányban (forrásról lekért vs. kliensekhez kiszolgált), alatta mindenki összesítésével. A „Számok” a fiók által letöltött dalokat számolja, nem azt, amit láthat.

## A fiókod és a preferenciáid

A **Beállítások → Általános** a **Fiókoddal** kezdődik: változtasd meg a felhasználóneved vagy jelszavad, vagy jelentkezz ki. Az oldalsávról is kijelentkezhetsz (telefonon a **Továbbiak** alól).

Az **Általános** többi része — téma, nyelv, dalszövegek megjelenítése a lejátszóban, albumok a keresési találatokban — **a tiéd**: minden böngészőbe elkísér, amelybe bejelentkezel, és másoknak semmit nem változtat.

A **Beállítások → Alkalmazások** felsorolja a fiókodhoz párosított telefonokat (egy admin mindenkiét látja, a tulajdonosukkal). A **Kijelentkezés mindenhol** leválasztja az alkalmazásaidat, és minden böngészőből kijelentkeztet.

## Felhasználók kezelése

A **Beállítások → Felhasználók** oldalon egy admin:

- **Felhasználót adhat hozzá** — felhasználónév (3–32 betű, számjegy, `.`, `-` vagy `_`), jelszó (legalább 8 karakter) és szerepkör.
- **Szerkeszthet** egy felhasználót — átnevezheti, adminná vagy felhasználóvá teheti, vagy új jelszót adhat neki (ami kijelentkezteti a böngészőiből; az alkalmazásai párosítva maradnak).
- **Törölhet** egy felhasználót — az alkalmazásai le lesznek választva, a böngészői kijelentkeztetve. A fájljai a lemezen maradnak (az adminok továbbra is láthatják); a kedvelései, listái, podcast-előfizetései, megfigyelései, javaslat-előzményei és forgalomszámlálói vele mennek.
- **Mindenkit kijelentkeztethet** — minden felhasználó minden alkalmazása le lesz választva, és minden böngésző ki lesz léptetve, a tiéd is.

Mindig van legalább egy admin: az utolsót nem lehet törölni vagy felhasználóvá tenni, és a saját fiókodat sem törölheted.

## Tevékenység

A **Beállítások → Tevékenység** (adminoknak) a Jellyfin irányítópultjához hasonlóan mutatja:

- **Most szól** — mit játszik minden böngésző és alkalmazás, kinek a nevében, hol tart a dalban, és szünetel-e. Néhány másodpercenként frissül.
- **Előzmények** — bejelentkezések (és a sikertelenek, a címmel, ahonnan jöttek), kijelentkezések, lejátszott dalok, letöltések, kedvelések, törölt fájlok, a felhasználók elől elrejtett vagy nekik megjelenített dalok, párosított és leválasztott alkalmazások, hozzáadott, módosított vagy törölt fiókok, megváltoztatott jelszavak és beállítások. Szűrj felhasználó vagy fajta szerint. A mentett beállítások csak név szerint szerepelnek, soha az értékeikkel. A bejegyzések 90 napig maradnak meg.

Az alkalmazások is jelentik, mit játszanak — lásd a [mobilkliens-szerződést](../mobile-client-contract.md#8-report-plays).

## A fiókok kikapcsolása

Egy olyan szerver, amelyet csak te érsz el — a saját gépeden, vagy valami mögött, ami már kér jelszót —, lehet, hogy egyáltalán nem igényel fiókokat. Állítsd a `DOWNTIFY_DISABLE_AUTH=true` értéket (lásd: [Környezeti változók](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Ekkor:

- Nincs bejelentkezési oldal: aki megnyitja a Downtifyt, az első adminként használja (új szerveren `admin`).
- A kijelentkezés gombok, a **Beállítások → Felhasználók**, a **Beállítások → Általános** **Fiók** része és a **Beállítások → Alkalmazások** **Kijelentkezés mindenhol** gombja eltűnnek.
- A telefonok továbbra is párosíthatók (ahhoz az adminhoz), és a **Beállítások → Tevékenység** továbbra is mutatja, mi hol szól.
- A téma, a nyelv és az **Általános** többi preferenciája az adott admin preferenciáiként marad meg.

::: warning Bárki, aki eléri a szervert, bármit megtehet
Kikapcsolt fiókok mellett semmi nem kérdezi, ki vagy: a hálózatodon mindenki — vagy az interneten, ha a port ki van téve — megváltoztathatja a beállításokat, törölhet zenét, és párosíthat egy telefont. Ne kapcsold ki a fiókokat olyan szerveren, amelyet mások is elérnek.
:::

Állítsd `false` értékre (vagy töröld), és a bejelentkezés újra kötelező, a fiókok, jelszavak és alkalmazások pedig úgy maradtak, ahogy voltak.

## Elfelejtetted a jelszót?

Futtasd ezt a szerveren — az `admin` visszakapja a `downtify` jelszót (és adminként újra létrejön, ha átnevezték vagy törölték); a többi fiók és a párosított alkalmazások érintetlenek maradnak:

```bash
docker exec downtify python main.py auth-reset
```

Dockeren kívül futtasd a `python main.py auth-reset` (vagy `uv run python main.py auth-reset`) parancsot a Downtify mappájában. Aztán jelentkezz be, és változtasd meg a jelszót.

## Szkriptek és az API

Minden API-hívás mostantól hitelesítő adatokat igényel (lásd az [API-referenciát](../api-reference.md#server-and-sign-in)). Egy szkript bejelentkezhet a `POST /api/auth/login` hívással, és megtarthatja a `downtify_session` sütit, vagy használhatja egy párosított eszköz tokenjét.
