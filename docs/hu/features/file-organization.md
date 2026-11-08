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

Ha a **Beállítások → Letöltések és fájlok → Rendezés előadó szerint** be van kapcsolva (alapértelmezés), minden szám — a lejátszási listák és albumok letöltéseit is beleértve — az album előadójának nevét viselő almappába kerül (lásd: [Több előadó és válogatások](#several-artists-and-compilations)):

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

## Több előadó és válogatások

Egy szám gyakran több előadót is feltüntet. A Downtify mindet megtartja a fájl **Előadó** címkéjében, és mindegyiket külön is beírja egy **ARTISTS** címkébe (MP3-ban `TXXX:ARTISTS`), így egy lejátszónak sosem kell egy olyan nevet, mint az `Earth, Wind & Fire`, a vesszőnél kettévágnia. A mappa viszont egyetlen előadóé: az **album előadójáé**, válogatásnál pedig a szám első előadójáé.

- Az album előadója az az előadó, akit a forrás (Spotify, YouTube Music vagy Deezer) az **albumhoz** feltüntet, minden számán ugyanaz, és az **Album előadója** címkébe kerül. Ha a forrás nem mondja meg, a szám első előadója.
- Egy duó vagy együttes egy előadó. A YouTube Music egyes formációkat a tagjaikkal tüntet fel, bejegyzésenként egyet (a `Henrique & Juliano` `Henrique` és `Juliano` formában érkezik, az albumnál és minden számnál — néha fordított sorrendben, `Mateus` és `Jorge` a `Jorge & Mateus` helyett). Minden feltüntetett név egy YouTube Music-csatornára mutat; ha egy tag linkje az egész formáció nevét viselő csatornára vezet, amely a mellette feltüntetett nevekből áll, a Downtify ezeket a neveket újra a formáció nevévé fűzi össze: a mappa és az **Album előadója**, **Előadó** és **ARTISTS** címke is `Henrique & Juliano` lesz. Egy valódi közreműködés (mindegyik előadó a saját csatornáján) minden előadót megtart. Ha a YouTube Music egyik tagot sem köti a formáció csatornájához, a nevek külön maradnak; a Könyvtár ennek ellenére nem ad oldalt olyan névnek, amely mindig csak valaki más mellett szerepel (lásd: [Könyvtárkatalógus](library-catalog.md#library-page)).
- Egy vendég sosem változtat ezen. A *The Girl Is Mine*, vendéggel Michael Jackson *Thriller* albumán, a `Michael Jackson/Thriller/` mappában marad, a *Lady Marmalade* kislemez (Christina Aguilera, Lil' Kim, Mýa, P!nk) pedig a `Christina Aguilera/` mappába kerül.
- Csak az az album válogatás, amelyet maga a forrás **Various Artists** előadónak tulajdonít (egy filmzene, egy „Now That's What I Call…”) — hacsak [magad meg nem jelölöd](#marking-an-album-as-various-artists). Egy önálló YouTube Music-szám sosem az: a YouTube Music ugyanazt a hangot több kiadás alatt is tárolja, és bármelyiket mutathatja albumként, gyakran egy válogatást, ezért csak egy teljes YouTube Music-album letöltése számít. A számai „Various Artists” album-előadót és válogatás jelzőt kapnak (MP3-ban `TCMP`, FLAC/Ogg/Opus esetén `COMPILATION`, M4A-ban `cpil`). Így az album egyben marad a Navidrome-ban és más médiaszervereken, amelyek ezek a címkék, nem pedig a mappák alapján csoportosítják az albumokat. A lemezen viszont a **Rendezés előadó szerint** sosem hoz létre `Various Artists` mappát: minden szám az első előadója mappájába kerül.
- A Downtify régebbi verziói minden több előadós számot **Various Artists** címkével láttak el, válogatás jelző nélkül. A Könyvtár az ilyen számot továbbra is az első előadója albumában mutatja, mint eddig; a **Megjelölés: Különböző előadók** valódi válogatássá teszi az albumot.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← a filmzenéről (válogatás)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← ugyanaz a filmzene
        └── David Bowie - Nature Boy.mp3
```

A kislemezes és a *Moulin Rouge* filmzenén szereplő *Lady Marmalade* két kiadás, mindegyik a saját albumával tárolva. A filmzene számai az előadóik mappái között oszlanak meg, de egyetlen „Various Artists” válogatásként vannak címkézve, így a Könyvtár és a médiaszerverek továbbra is egy albumként mutatják a *Moulin Rouge*-t.

### Album megjelölése Különböző előadókként

Egy forrás egyetlen előadónak tulajdoníthat egy kiadást akkor is, ha az egyformán több előadóé — a Deezer a *Lady Marmalade* kislemezt csak Christina Aguilera alatt tartja. Egy admin ezt az album Könyvtárbeli oldalán javíthatja ki, a **Hozzáadás a sorhoz** melletti **Megjelölés: Különböző előadók** gombbal.

- Az album minden száma „Various Artists” album-előadót és válogatás jelzőt kap. Semmi más nem változik a fájlokban, és ott maradnak, ahol vannak (egy válogatás számai amúgy is az első előadójuk mappájában vannak). Minden fájl egy munkapéldányon keresztül íródik újra, megtartja a módosítási dátumát, és érintetlen marad, ha az újraírás nem sikerül.
- A Könyvtárban az album ezután **Various Artists** alatt szerepel az **Albumok** között (minden szám a saját előadója oldalán marad), és az album oldala követi oda.
- A Downtify megjegyzi az albumot: egy később letöltött száma ugyanígy kap címkéket.
- Válogatásnál ugyanez a gomb **Különböző előadók jelölés törlése** feliratú: visszavonja a jelölést, és visszaállítja az album korábbi előadóját. Olyan albumon is működik, amelyet a forrása tett válogatássá; ekkor az album előadója az az előadó lesz, akit a számai többsége elsőként tüntet fel, és az album későbbi letöltései nem lesznek újra megjelölve.

Csak az adminok látják a gombot. A médiaszerverek a következő könyvtárvizsgálatkor veszik át a változást.

## M3U és előadómappák

Ha a *Rendezés előadó szerint* be van kapcsolva, és úgy töltesz le Spotify-lejátszási listát, hogy az M3U-generálás is be van kapcsolva, az M3U a `<downloads>/Playlists/<lejátszási-lista-neve>.m3u` útvonalra kerül, nem a lejátszási lista almappájába. Ennek oka, hogy a számok most több előadómappában szétszórva vannak. Az M3U-n belüli relatív útvonalak továbbra is helyesen oldódnak fel, bárhová csatolod is a könyvtárat.

## A beállítás módosítása

A beállítás azonnal érvényes minden **új** letöltésre. A lemezen már meglévő fájlokat nem helyezi át.

## Egy szám törlése kitakarítja az üres mappákat

Egy szám törlése a Könyvtár oldalról a lejátszási lista-, előadó- vagy albummappáját is eltávolítja, amint kiürül — és tovább halad felfelé az immár üres szülőmappákon (például az előadó mappáján, miután az utolsó albuma is eltűnt), megállva magánál a letöltési könyvtárnál, amelyet soha nem töröl. Az a mappa, amely még bármi mást tartalmaz — másik számot, `.m3u` fájlt, még használt `cover.jpg`-t —, érintetlen marad.

## Több szám kijelölése és törlése egyszerre

A Könyvtár számlistájában minden számnál van egy jelölőnégyzet, valamint egy **Összes kijelölése** négyzet, amely kijelöli az aktuális szűrőnek megfelelő összes számot (lásd: [Könyvtár oldal](library-catalog.md#library-page)). A kijelölési sáv **Törlés a könyvtárból** gombja mindet egyetlen kéréssel eltávolítja (`DELETE /delete/batch`, lásd: [API-referencia](../api-reference.md)), ugyanazzal a számonkénti takarítással (`.lrc`, árva `cover.jpg`, üres mappák), mint egy szám egyenkénti törlésekor.

Egy teljes album vagy lejátszási lista törléséhez nyisd meg, és válaszd a **Törlés** menüpontot a **⋯** menüből. Egy előadó mindenéhez írd be az előadó nevét a számlista szűrőjébe, majd válaszd az **Összes kijelölése** lehetőséget, és töröld.
