---
icon: lucide/file-headphone
---

# Fájlszervezés

Egy új szerver a fájlokat előadó és album szerint szervezi (`Előadó/Album/…`): a **Rendezés előadó szerint** és a **Rendezés album szerint** alapértelmezetten is be van kapcsolva. Kapcsold ki őket az alábbi lapos elrendezéshez. Az e alapértelmezés előtt beállított szerverek megtartják korábbi választásukat.

## Lapos elrendezés (mindkettő kikapcsolva)

Az önálló számok és a YouTube-keresések közvetlenül a letöltési mappa gyökerébe kerülnek. A lejátszási listák és albumok számai lejátszási listánkénti vagy albumonkénti almappába:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← önálló szám
```

## Rendezés előadó szerint

Ha a **Beállítások → Letöltések és fájlok → Rendezés előadó szerint** be van kapcsolva (alapértelmezés), minden szám — a lejátszási listák és albumok letöltéseit is beleértve — a fő előadó nevét viselő almappába kerül:

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Ez a szerkezet kompatibilis az `Előadó/Szám.ext` mappaelrendezést váró médiaszerverekkel (Jellyfin, Navidrome, Plex) és könyvtárkezelőkkel (Beets).

## M3U és előadómappák

Ha a *Rendezés előadó szerint* be van kapcsolva, és úgy töltesz le Spotify-lejátszási listát, hogy az M3U-generálás is be van kapcsolva, az M3U a `<downloads>/Playlists/<lejátszási-lista-neve>.m3u` útvonalra kerül, nem a lejátszási lista almappájába. Ennek oka, hogy a számok most több előadómappában szétszórva vannak. Az M3U-n belüli relatív útvonalak továbbra is helyesen oldódnak fel, bárhová csatolod is a könyvtárat.

## A beállítás módosítása

A beállítás azonnal érvényes minden **új** letöltésre. A lemezen már meglévő fájlokat nem helyezi át.

## Egy szám törlése kitakarítja az üres mappákat

Egy szám törlése a Könyvtár oldalról a lejátszási lista-, előadó- vagy albummappáját is eltávolítja, amint kiürül — és tovább halad felfelé az immár üres szülőmappákon (például az előadó mappáján, miután az utolsó albuma is eltűnt), megállva magánál a letöltési könyvtárnál, amelyet soha nem töröl. Az a mappa, amely még bármi mást tartalmaz — másik számot, `.m3u` fájlt, még használt `cover.jpg`-t —, érintetlen marad.

## Több szám kijelölése és törlése egyszerre

A Könyvtár számlistájában minden számnál van egy jelölőnégyzet, valamint egy **Összes kijelölése** négyzet, amely kijelöli az aktuális szűrőnek megfelelő összes számot (lásd: [Könyvtár oldal](library-catalog.md#library-page)). A kijelölési sáv **Törlés a könyvtárból** gombja mindet egyetlen kéréssel eltávolítja (`DELETE /delete/batch`, lásd: [API-referencia](../api-reference.md)), ugyanazzal a számonkénti takarítással (`.lrc`, árva `cover.jpg`, üres mappák), mint egy szám egyenkénti törlésekor.

Egy teljes album vagy lejátszási lista törléséhez nyisd meg, és válaszd a **Törlés** menüpontot a **⋯** menüből. Egy előadó mindenéhez írd be az előadó nevét a számlista szűrőjébe, majd válaszd az **Összes kijelölése** lehetőséget, és töröld.
