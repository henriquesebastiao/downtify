---
icon: lucide/smartphone
---

# Mobilalkalmazások

A Downtify képes alkalmazásokat kiszolgálni a telefonodon: azok böngészik és streamelik a könyvtárat közvetlenül a szerveredről, és a telefonon tartanak dalokat offline hallgatáshoz. Minden, amire egy alkalmazásnak szüksége van, a **Beállítások → Alkalmazások** alatt állítható be: a telefonok párosítása és a szerver neve. Hogy egyáltalán ki használhatja a szervert, azt a [Felhasználók és bejelentkezés](users.md) fiókjai határozzák meg.

::: warning Az alkalmazás még fejlesztés alatt áll
A **Beállítások → Alkalmazások** *Kísérleti*nek van jelölve. Az ezen az oldalon leírt szerveroldal kész és működik, de **az Android-alkalmazásnak még nem jelent meg egyetlen verziója sem**, így egyelőre nincs mit telepíteni, és a párosítás és a streamelés részletei még változhatnak a Downtify-verziók között.

Az alkalmazás nyíltan készül a [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android) adattárban. Bármi más is építhető ugyanerre az API-ra — lásd a [mobilkliens-szerződést](../mobile-client-contract.md).
:::

## Bejelentkezés az alkalmazásból

Írd be a szerver címét (vagy válaszd ki az **Ezen a hálózaton találhatók** alatt), majd jelentkezz be **ugyanazzal a felhasználónévvel és jelszóval**, mint a weboldalon. A telefon megjelenik a **Párosított alkalmazások** között, pontosan úgy, mintha lent kóddal párosítottad volna: a te nevedben játszik, saját kulcsot őriz (a jelszót nem tárolja a telefon), és a **Párosítás bontása** leállítja.

A hibás jelszavak a weboldal bejelentkezésével együtt sebességkorlátozottak. Amíg a fiókok ki vannak kapcsolva (`DOWNTIFY_DISABLE_AUTH`), nincs mivel bejelentkezni: párosíts kóddal.

## Telefon párosítása

A párosításhoz nem kell jelszó a telefonon: kényelmes, ha a weboldal már nyitva van, vagy olyan telefonon, amelybe inkább nem írnád be a jelszavad.

1. Nyisd meg a **Beállítások → Alkalmazások** oldalt, és nyomd meg a **Telefon párosítása** gombot.
2. Az alkalmazásban válaszd a **Kód beolvasása** lehetőséget, és irányítsd a kamerát a QR-kódra — vagy írd be az alatta látható 8 karakteres kódot (`K7QM-2XPD`; a kis- és nagybetű, valamint a kötőjelek nem számítanak).
3. A párbeszédablak megerősíti, ha a telefon párosítva van, és megjelenik a **Párosított alkalmazások** alatt.

A telefon a **fiókodhoz** van párosítva: te nevedben játszik, és megjelenik a tevékenységedben. Bárki, akinek van fiókja, párosíthatja a saját telefonjait.

Egy kód **egyszer** működik, **öt percig**, és a hibás kódok próbálgatása sebességkorlátozott. A telefon saját kulcsot kap, amelyet megőriz; a szerver csak a hashét tárolja.

A **Párosított alkalmazások** listázza a telefonjaidat (egy admin mindenkiét látja, az egyes telefonok tulajdonosával), a platformjukkal, hogy mikor látták utoljára, és melyik címről. A **Párosítás bontása** azonnal leállít egy telefont — a következő kérése meghiúsul, a nyitott kapcsolat bezárul, és az általa megosztott hivatkozások (lásd: [Casting](#casting)) megszűnnek működni. Az újbóli használathoz párosítsd újra.

## Mit tehet egy párosított alkalmazás

A párosított alkalmazások böngészhetnek, lejátszhatnak, kedvelhetnek, dalokat tarthatnak offline, és megkérhetik a szervert zene letöltésére — de nem módosíthatnak beállításokat vagy hitelesítő adatokat, és nem törölhetnek fájlokat; ahhoz a weboldal kell, adminként bejelentkezve.

A **Beállítások → Alkalmazások → Kijelentkezés mindenhol** az összes alkalmazásodat leválasztja, és minden böngészőből kijelentkeztet, ebből is. A bejelentkezés, a fiókok és az elfelejtett jelszó a [Felhasználók és bejelentkezés](users.md) oldalon van.

## A szerver megtalálása a hálózaton

A szerver bejelentkezik a helyi hálózaton (mDNS / Bonjour, `_downtify._tcp` néven), így egy alkalmazás begépelés nélkül listázza a **Ezen a hálózaton található** alatt — névvel, címmel és verzióval. A név az, amit a **Beállítások → Alkalmazások → Szerver neve** alatt adtál meg (a gép hosztneve, amíg meg nem változtatod).

::: info A Docker alapértelmezett hálózata elrejti a hirdetést
A Docker alapértelmezett *bridge* hálózatában a hirdetés a Dockeren belül marad, és a telefonok nem látják. Vagy futtasd a konténert `network_mode: host` móddal (lásd: [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), vagy írd be a szerver címét az alkalmazásba — minden más ugyanúgy működik.
:::

Állítsd a `DOWNTIFY_DISCOVERY=false` értéket, hogy ne hirdesse magát.

## Streamelési minőség

Az alkalmazások a fájlokat úgy játsszák le, ahogy vannak (**Eredeti**), vagy kisebb másolatot kérnek a szervertől: Opus, AAC vagy MP3 96–320 kbps-en — hasznos mobiladatnál. A szerver ezt a másolatot ffmpeggel készíti el, amikor egy dalt először így játszanak le (egy átlagos dalnál néhány másodperc), és megtartja, így a tekerés úgy működik, mint bármely fájlnál, a következő lejátszás pedig azonnali.

- Az a fájl, amely már elég kicsi (egy veszteséges fájl a kért bitrátán vagy az alatt), változatlanul streamelődik, soha nem kódolódik újra.
- A másolatok a `/data/transcode_cache` mappában vannak, alapértelmezetten legfeljebb 2 GB; a legrégebben lejátszottak mennek előbb. Egyszerre legfeljebb kettő készül. Mindkét korlát [környezeti változó](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Ha a telefon feladja, miközben egy másolat készül, a szerver abbahagyja a készítését.

## Hangerő-normalizálás

Az Android-alkalmazás a webes lejátszóval azonos mérések alapján hasonló hangerővel játszhatja le a dalokat: kapcsold be a **Hangerő normalizálása** beállítást a **Beállítások → Lejátszás** alatt. A következő dalnál lép életbe, a mérés nélküli dalok pedig eredeti hangerővel szólnak. Egy offline másolat csak akkor használ mérést, ha teljes egészében töltődött le, és egyezik a szerver által mért fájllal. Lásd: [Hangerő-normalizálás](playback-normalization.md).

## Casting

Az alkalmazások egy dalt Chromecastnak vagy más lejátszónak küldhetnek, amely maga kéri le a hangot. Az alkalmazás a szervertől egy hivatkozást kap, amely az adott dalra korlátozott ideig (alapértelmezetten egy óráig) és csak addig működik, amíg a telefon párosítva marad; a telefon egyetlen kulcsa sem kerül bele.

## Fordított proxy mögött

Ha a Downtify nginx, Caddy, Traefik vagy hasonló mögött áll (HTTPS-hez, vagy hogy kívülről elérd):

- **Engedd át a WebSocketet.** A `/api/ws` megköveteli az `Upgrade`/`Connection` fejlécek továbbítását (a Caddy és a Traefik alapból megteszi; az nginxhez `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` kell).
- **Engedd át a Range-kéréseket** változatlanul, és ne pufferelj hangválaszokat (nginx: `proxy_buffering off;` a `/api/v1/` és a `/downloads/` útvonalra), különben a tekerés és a nagy fájlok szenvednek.
- **Mondd meg a Downtifynak, melyik proxynak higgyen.** Állítsd a `DOWNTIFY_TRUSTED_PROXIES` értékét a proxy címére (pl. `172.18.0.0/16`). Csak ekkor használja a Downtify az `X-Forwarded-For` fejlécet a kliens címéhez (sebességkorlátok, „utoljára látva” a Párosított alkalmazásoknál), és az `X-Forwarded-Proto`/`X-Forwarded-Host` fejlécet a bejelentkezési süti biztonságossá jelöléséhez és annak ellenőrzéséhez, honnan jönnek a kérések. Nélküle e fejléceket figyelmen kívül hagyja — bárki küldhetné őket.
- **Használj HTTPS-t**, ha a szerver kívülről elérhető: a jelszó és az alkalmazások kulcsai minden kéréssel utaznak.

## Alkalmazásfejlesztőknek

Az egész folyamat, amelyet egy alkalmazás követ — felfedezés, párosítás, a könyvtár szinkronizálása, streamelés, lejátszások jelentése — a [mobilkliens-szerződésben](../mobile-client-contract.md) van, és minden végpont az [API-referenciában](../api-reference.md#server-and-sign-in).
