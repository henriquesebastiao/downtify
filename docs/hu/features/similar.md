---
icon: lucide/sparkles
---

# Hasonlók

A **Hasonlók** olyan számokat keres, amelyek úgy hangzanak, mint az általad megadott szám — a YouTube Music saját rádiókeverékéből, vagyis abból, amit a YouTube a számod után játszik. API-kulcs és beállítás nélkül.

## Használata

Nyisd meg a **Hasonlók** oldalt az oldalsávról (a **Toplisták** alatt, telefonon a **Továbbiak** lapon). Írd be az **Előadót** vagy a **Számot** (elég az egyik — pusztán előadónál a legnagyobb slágeréből indul), majd kattints a **Hasonlók keresése** gombra:

Gépelned sem kell: az alkalmazás minden számsora hordoz egy **Hasonlók** gombot (a varázspálca ikon a letöltés gomb mellett, a Keresésben, a Toplistákon és a Felfedezésben ahhoz hasonlóan kitöltve — a Legnépszerűbb számoknál és a beillesztett hivatkozásoknál halvány ikon, a Könyvtár, az Album, az Előadó és a Lejátszási lista számainál pedig helyi menüelem). Ez úgy nyitja meg ezt az oldalt, hogy már az adott számot keresi. A keresési találatok közvetlenül a sorból teljes hosszban is lejátszhatók, letöltés nélkül.

- **Teljes lejátszás** — koppints a borítóra, és a szám erről a szerverről közvetlenül a beépített lejátszóba streamelődik, letöltve vagy anélkül.
- **Letöltés** — minden sor már hordozza a videóját, és azonnal letölt: a Downtify ugyanazon az [illesztési folyamaton](../how-it-works.md) keresztül sorba állítja az egyezést, mint bármely más letöltést. Ettől kezdve a sor mutatja a letöltés előrehaladását, majd egy pipát, ha a szám bekerült a könyvtáradba.
- **Végtelen lista** — a végére görgetve a következő oldal az utolsó szám saját keverékéből töltődik be, és az utolsó soron túli lejátszás ugyanígy, vég nélkül bővíti a sort.

## API

Lásd a [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) részt az API-referenciában.
