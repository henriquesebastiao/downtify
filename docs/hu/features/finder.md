---
icon: lucide/columns-3
---

# Finder

A **Finder** egy módja annak, hogy letöltés előtt felfedezd a Deezer katalógusát. Keresel a Deezeren, megnyitsz egy előadót, és három egymás melletti oszlopban böngészed, mint a macOS Finder oszlopnézetét: az előadót, a diszkográfiáját és egy album számait. Nem kell hozzá Deezer-fiók vagy API-kulcs.

## Keresés

Nyisd meg a **Felfedezés** oldalt az oldalsávról (telefonon: **Továbbiak → Felfedezés**): a Finder keresőmezője az oldal tetején van, mellette a legutóbbi Finder-kereséseid. A keresés a Felfedezés javaslatait a találatokra cseréli — dalok, albumok és előadók a **Mind / Dalok / Albumok / Előadók** szűrőkkel, mint a megszokott Keresés oldalon, de csak a Deezerről. Töröld a mezőt (a **×**) vagy lépj vissza, hogy újra lásd a javaslatokat; egy legutóbbi keresés egy kattintással újra lefut, a **Törlés** pedig mindet elfelejti. A legutóbbi keresések csak ebben a böngészőben maradnak meg.

A **Dalok keresése** egy, a Felfedezés által javasolt előadó **⋯** menüjében az adott előadó dalait mutatja itt keresésként: a Deezeren az előadó nevére keres, és csak pontosan annak az előadónak a dalait listázza — a Deezer-azonosítójuk alapján egyeztetve, így egy névrokon vagy egy csak így nevezett dal kimarad — legfeljebb az első néhány százat.

- A **dalok** teljes hosszban streamelődnek, és mint bármely keresési találat, letölthetők. A Downtify a címük, előadójuk és hosszuk alapján találja meg a dalt a YouTube Musicon (tartaléknak a YouTube-on). A dal címére kattintva megnyílik az albuma az oszlopnézetben, a dal kiemelve.
- Az **albumok** az előadójukon nyílnak meg, az adott album kijelölve. A borítón lévő letöltés gomb az egész albumot sorba állítja.
- Az **előadók** az oszlopnézetet az adott előadón nyitják meg.

## Az oszlopnézet

| Oszlop | Mit mutat |
| --- | --- |
| **Előadó** | Az előadó fotója és az albumok száma, a felület nyelvén írt életrajza (kibontható), a 10 legnépszerűbb száma és a „A rajongók ezeket is kedvelik” (kapcsolódó előadók). |
| **Diszkográfia** | Minden album, kislemez, EP és válogatás, a legfrissebbtől kezdve, borítóval, címmel, kiadási típussal, évvel és a számok számával. A szűrők kiadási típus szerint szűrnek. |
| **Számok** | A kijelölt album borítója és címe, az előadója, éve, a számok száma és hossza. Egy információs panel felsorolja a megjelenés dátumát, a kiadót, a műfajokat, a közreműködőket és az UPC-t. Alatta az album számai vannak: mindegyik teljes hosszban streamelődik, amíg le nem töltöd, utána a könyvtáradból szól, és a **Album letöltése** gomb mindet sorba állítja. |

Egy népszerű számra kattintva kijelölődik az albuma és kiemelődik a szám; mindkét oszlop finoman odagörget (azonnal, ha a rendszer csökkentett mozgásra van állítva), és amint az album számai megjelennek a képernyőn, a szám teljes hosszban elindul — streamelve, vagy maga a dal, ha már a könyvtáradban van. Újra rákattintva lejátszás közben nem szünetel; ha az oldalt egy számra mutató hivatkozásból nyitod meg, semmi sem indul el. Egy kapcsolódó előadóra kattintva az az előadó nyílik meg, a böngésző vissza gombja pedig az előzőre visz. Az oszlopok feletti útvonalsáv (**Felfedezés › előadó › album**) visszavisz a kereséshez (vagy a Felfedezéshez, ha az oszlopokat nem keresésből nyitottad), vagy csak az előadóhoz. Ami nyitva van, az az URL-ben tárolódik, így túléli az újratöltést, és könyvjelzőzhető.

Széles képernyőn húzd az oszlopok közti szélt, hogy egyiket szélesebbé vagy keskenyebbé tedd, vagy fókuszáld, és használd a nyílbillentyűket. Dupla kattintás visszaállítja az alapértelmezett szélességeket. Az előadó- és diszkográfiaoszlop tetején lévő nyílgomb az oszlopot csak a képeire csukja össze: az előadó fotójára, a népszerű számok borítóira és a kapcsolódó előadók fotóira, vagy az albumborítókra. Minden kép továbbra is úgy működik, mint a teljes sora, és a neve egérmutatáskor látszik. A szélességek és az összecsukott oszlopok csak addig tartanak, amíg az oldalon vagy: soha nem mentődnek, így az újratöltés vagy a Finderből való kilépés visszaállítja őket.

Telefonon az oszlopok egymás mellett vannak, és közöttük húzással lépsz. Egy album kiválasztása a számaihoz csúsztat.

::: info Miért jelenik meg a számok száma egy pillanattal később
A Deezer diszkográfialistája nem tartalmazza a számok számát, ezért a Downtify minden album számát külön kéri le, egyszerre néhány albumét, a Deezer 5 másodpercenkénti 50 kérésének korlátja alatt maradva. A számok nézelődés közben jelennek meg, és a Downtify újraindulásáig megmaradnak. Az az album, amelynek számát nem sikerült lekérni, `…`-t mutat.
:::

## API

Lásd a [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) végpontot és az utána következőket az API-referenciában.
