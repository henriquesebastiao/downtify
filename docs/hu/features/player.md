---
icon: lucide/headphones
---

# Beépített lejátszó

A Downtify webes lejátszóval érkezik, hogy külön alkalmazás nélkül hallgathasd a letöltött zenéidet. Nyomj lejátszást a Könyvtár bármely számán, albumán, előadóján vagy lejátszási listáján — vagy a Sor egy kész letöltésén —, és a lejátszó elindul.

## Lejátszósáv

Amíg egy szám be van töltve, egy lejátszósáv lebeg minden oldal alján: borító, cím és előadó, véletlen sorrend, előző, lejátszás/szünet, következő, ismétlés, eltelt/teljes idő, valamint gyorsgombok a dalszöveg és a következő panelekhez (a dalszövegé [elrejthető](#hiding-the-lyrics)). Széles képernyőn hangerőcsúszka és a felső szélén keresősáv is van; telefonon a lényegre zsugorodik, és vékony előrehaladási vonalat mutat.

A cím mellett egy szív van a [dal kedveléséhez](liked-songs.md); a telefon kihagyja a sávból, hogy maradjon hely a címnek, és helyette a **Most szól** nézetben és a számlistákban tartja.

Kattints a címre vagy a borítóra, vagy a kibontás gombra a **Most szól** megnyitásához.

## Most szól

Teljes képernyős nézet, az aktuális albumborítóból vett színekkel színezve:

- **Nagy borító**, cím és előadó (kattints az előadóra vagy a *Lejátszás innen* címkére, hogy az előadóhoz, albumhoz vagy lejátszási listához ugorj), a cím mellett egy szívvel a [dal kedveléséhez](liked-songs.md). A borító és a dalszöveg az ablakkal együtt zsugorodik — akkor is, ha csak a magasságát változtatod —, így a fejléc alatt maradnak.
- **Keresősáv** — kattints vagy húzz, vagy használd a nyílbillentyűket, ha fókuszban van. Amíg egy szám szól, lágy hullámok sodródnak a lejátszott rész fölött az albumborítóból vett színekben; szünetnél ellaposodnak, és mozdulatlanok maradnak, ha a rendszered csökkentett mozgást kér
- **Lejátszásvezérlők** — véletlen sorrend, előző, lejátszás/szünet, következő, ismétlés (ki → összes ismétlése → egy ismétlése)
- **Hangerő** némítás kapcsolóval, munkamenetek között mentve. Telefonon rejtett, ahol a hardvergombok szabályozzák a szintet
- **Elalvási időzítő** — leállítja a lejátszást 15, 30, 45, 60 vagy 90 perc után, vagy az aktuális szám végén. A hátralévő idő az időzítő gomb mellett látszik
- **Fájlinformáció** — a lejátszott fájl formátuma és mérete

Négy panel ül a borító mellett széles képernyőn, vagy helyettesíti azt telefonon:

- **Dalszöveg** — az időzített dalszövegek kiemelik az aktuális sort, és a számmal együtt görögnek; kattints egy sorra, hogy oda ugorj. Az egyszerű dalszöveg változtatás nélkül jelenik meg. A dalszöveg a szám melletti `.lrc` fájlból vagy a címkéibe ágyazottból jön — lásd: [Dalszövegek](lyrics.md). Ezt a panelt elrejtheted — lásd: [A dalszöveg elrejtése](#hiding-the-lyrics).
- **Következik** — a lejátszási sor. Húzással átrendezheted a számokat, eltávolíthatsz egyes számokat, vagy kiürítheted az aktuális utáni mindent.
- **Részletek** — cím, előadó, album, számsorszám, év, hossz, formátum, méret, hozzáadás dátuma és fájlútvonal.
- **Hangszínszabályzó** — formáld a hangot tíz frekvenciasávval; lásd: [Hangszínszabályzó](#equalizer).

A Most szól része az oldal címének (`?np=1`, valamint `&panel=lyrics|queue|details|equalizer`), így a böngésző Vissza gombja bezárja, az újratöltés pedig nyitva tartja.

## A dalszöveg elrejtése

A borítót és a sort szavak nélkül szereted jobban? Kapcsold ki a **Beállítások → Általános → Lejátszó → Dalszövegek megjelenítése a lejátszóban** lehetőséget. Azonnal érvénybe lép, és elvesz mindent, ami a lejátszóban dalszöveghez vezet:

- a **Dalszöveg** panelt és a lapját (telefonon a gombját a Most szól láblécében);
- a dalszöveg gombot a lejátszósávon;
- az `L` gyorsgombot, amely a gyorsgomblistáról (`?`) is lekerül.

A Most szól ezután a **Következik** nézeten nyílik meg. Egy, a kikapcsolás előtti `&panel=lyrics` hivatkozás szintén ide érkezik egy üres fül helyett. A lejátszó egyáltalán nem kéri el egy szám dalszövegét, amíg el van rejtve.

::: info Az elrejtés nem törlés
Ez csak azt változtatja meg, amit a lejátszó mutat. A fájljaid megtartják a Downtify által beléjük ágyazott dalszöveget, a mellettük lévő `.lrc` fájlok pedig a helyükön maradnak, így a médiaszerverek és más lejátszók továbbra is látják őket. A letöltések is tovább szerzik be a dalszövegeket — ez a **Címkék és dalszövegek** alatti külön **Dalszövegek letöltése** beállítás (lásd: [Dalszövegek](lyrics.md)).
:::

A témához és a hangszínszabályzóhoz hasonlóan a választás a böngészőben (`localStorage`) tárolódik, tehát eszközönként és böngészőnként érvényes, nem Downtify-szerverenként — elrejtheted a dalszöveget telefonon, és megtarthatod asztali gépen.

## Hangszínszabályzó

Tízsávos grafikus hangszínszabályzó a Most szól **Hangszínszabályzó** paneljén (vagy nyomd meg az `E` billentyűt). **Kísérleti**nek van jelölve: még változhat, és egyes böngészőkben hibásan működhet (lásd: [Böngészőtámogatás](#browser-support)).

- **Sávok** 31, 62, 125, 250, 500 Hz-en és 1, 2, 4, 8, 16 kHz-en, mindegyik ±12 dB 0,5 dB-es lépésekben. A 31 Hz-es és a 16 kHz-es sáv shelf, így mindent emel vagy vág alatta / fölötte is. Húzz egy sávot, vagy fókuszáld és használd a nyílbillentyűket (`Page Up`/`Page Down` 1 dB-hez, `Home`/`End` a határokhoz); a dupla kattintás 0-ra állítja.
- **Előbeállítások** — Lineáris, Mélykiemelés, Magaskiemelés, Ének, Rock, Elektronikus és Akusztikus. Ha ezután bármelyik sávot mozdítod, az előbeállítás **Egyéni** lesz.
- **Előerősítő** — ±12 dB mindenre ráadásként.
- **Be-/kikapcsoló** és **Visszaállítás** (vissza Lineárisra, előerősítő 0, ki). Egy sáv mozdítása vagy egy előbeállítás választása a hangszínszabályzót is bekapcsolja.
- A csúszkák mögötti görbe az összes sáv együttes válasza.

A sávok kiemelése a hangos zenét a teljes kivezérlés fölé nyomná és torzítaná, ezért a Downtify automatikusan csökkenti a hangerőt a görbe legnagyobb kiemelésével — a panel megmondja, mennyivel. Ez a csúcsot 0 dB-en tartja, így egy kiemelt előbeállítás átformálja a hangot, nem csupán hangosabbá teszi. Az előerősítő 0 dB fölé emelése megszünteti ezt a biztonsági tartalékot, és a panel figyelmeztet, hogy a hangos részek torzulhatnak.

A beállítások a böngészőben (`localStorage`) tárolódnak, és mindenre vonatkoznak, amit lejátszol, minden fülön, amíg meg nem változtatod őket. Böngészőnként érvényesek, nem Downtify-szerverenként.

### Böngészőtámogatás

A hangszínszabályzó a Web Audio API-t használja, amely minden jelenlegi böngészőben elérhető. Amíg be nem kapcsolod, a lejátszás egyáltalán nem érinti a Web Audiót. Bekapcsolás után a látogatás hátralévő részében a hang rajta halad át — a kikapcsolás csak lelapítja az összes sávot.

::: warning Safari iPhone-on és iPaden
Az iOS szüneteltetheti a Web Audiót, ha a képernyő lezár vagy appot váltasz, ami bekapcsolt hangszínszabályzó mellett leállítja a lejátszást. Ha kikapcsolt képernyővel hallgatsz, kapcsold ki a hangszínszabályzót, és töltsd újra az oldalt.
:::

## A sor összeállítása

Egy album, előadó, lejátszási lista vagy a számlista lejátszása sorba állítja ezeket a számokat sorrendben, az általad választottól kezdve. A **Véletlen sorrend** egy gyűjteményen véletlen sorrendben indítja el. A le nem töltött számok közvetlenül a sorban szólnak teljes hosszban, a szerver stream-gyorsítótárából kiszolgálva: amíg az egyik szól, a következő már egy számmal előre készül, így a lejátszás megállás nélkül halad át a le nem töltött soroknál — még ott is, ahol maga a böngésző nem éri el a YouTube-ot. A streamelt számot soha nem menti, kedveli vagy jegyzi meg újratöltések között.

Minden szám menüje (a **⋯** gomb, vagy jobb kattintás asztali gépen) tartalmazza:

- **Lejátszás következőként** — beszúrás közvetlenül az aktuális szám után
- **Hozzáadás a sorhoz** — hozzáfűzés a végéhez
- **Ugrás az albumhoz** / **Ugrás az előadóhoz**
- **Mentés erre az eszközre** — a fájl letöltése a böngészőn keresztül
- **Törlés a könyvtárból**

Ugyanezek a műveletek érvényesek a Könyvtárban egy többszámos kijelölésre.

A sor, az aktuális szám, annak pozíciója, a véletlen sorrend és az ismétlés megmarad, így a Downtify újranyitása ott folytatja, ahol abbahagytad (a 2000-nél több számos sorok nem maradnak meg). A törölt fájlok automatikusan kiesnek a sorból.

## Billentyűzet és médiabillentyűk

| Billentyű | Művelet |
|-----|--------|
| `Space` | Lejátszás / szünet |
| `←` / `→` | Tekerés 5 másodperccel |
| `Shift` + `←` / `→` | Előző / következő szám |
| `↑` / `↓` | Hangerő |
| `M` | Némítás |
| `S` | Véletlen sorrend |
| `R` | Ismétlés |
| `L` | Dalszöveg megnyitása (hacsak nincs [elrejtve](#hiding-the-lyrics)) |
| `Q` | A következők megnyitása |
| `E` | A hangszínszabályzó megnyitása |
| `Ctrl` / `⌘` + `K` vagy `/` | Keresés |
| `Ctrl` / `⌘` + `F` | Keresés a listában (egy lista oldalán) |
| `G` majd `L` / `D` | Ugrás a könyvtárra / sorra |
| `Esc` | A Most szól bezárása |
| `?` | Az összes gyorsgomb megjelenítése |

A gyorsgombokat figyelmen kívül hagyja, amíg mezőbe gépelsz vagy párbeszédablak van nyitva.

A lejátszó az aktuális számot az operációs rendszernek is jelzi (Media Session), így a zárolási képernyő vezérlői, a fejhallgatógombok és a billentyűzet médiabillentyűi működnek, a borítóval, ahol a rendszer támogatja.

## Hogyan működik

A számok a könyvtárlistából (`GET /tracks`) jönnek, amely az egyes fájlok címkéiből olvassa a címet, előadót, albumot, számsorszámot, évet és hosszt. A fájlokat a `/downloads` statikus csatolásból szolgálja ki; a [helyben hagyott](slskd-navidrome.md#leave-files-in-place) slskd-letöltések a `/media/slskd/…` útvonalon szólnak. A borító a `/cover`, a dalszöveg a `/lyrics` végpontból jön — lásd az [API-referenciát](../api-reference.md#file-management).

A lejátszás a böngésző natív HTML5-hangját használja. Nincsenek bővítmények, nincsenek extra folyamatok.

## Támogatott formátumok

A lejátszó bármilyen formátumot le tud játszani, amelyet a böngésződ HTML5-hangmotorja támogat. Ez jellemzően magában foglalja az MP3-at, M4A/AAC-t, OGG-t és OPUS-t minden modern böngészőben. A FLAC-támogatás változó — a Chrome és az Edge natívan támogatja; a Firefox és a Safari esetleg nem.
