---
icon: lucide/replace
---

# Hang cseréje

A Downtify automatikusan kiválasztja az egyes dalok hangját, és néha rosszat választ: egy másik, azonos nevű dalt, élő felvételt, remixet vagy hosszú intróval feltöltött verziót. A **Hang cseréje** lehetővé teszi, hogy kézzel válaszd ki a helyes verziót. A szám mindenhol megtartja a helyét — a lejátszási listáiban, az M3U fájlokban, a kedvelésekben és a párosított alkalmazásokban —, és csak a hang változik.

Hangot csak adminisztrátorok cserélhetnek (lásd: [Felhasználók és bejelentkezés](users.md#admins-and-users)).

## Egy szám hangjának cseréje

1. A **Könyvtárban** nyisd meg a szám menüjét (jobb gombbal, vagy a **⋯** gombbal), és válaszd a **Hang cseréje…** lehetőséget.
2. A Downtify megkeresi az „Előadó - Cím” kifejezést a **YouTube Musicban** és a **YouTube-on**, és felsorolja a találatokat. Módosítsd a keresést, vagy illessz be egy YouTube- vagy YouTube Music-hivatkozást egy videóhoz vagy dalhoz, hogy pontosan a kívánt feltöltést kapd.
3. Válassz egy verziót. Mindegyik megmutatja, honnan származik és milyen hosszú, a fájlod hossza mellett. A fájlod hosszától legfeljebb 3 másodpercre eltérő verzió ki van emelve. A ↗ gomb megnyitja a YouTube-on, hogy választás előtt meghallgathasd.
4. Nyomd meg a **Hang cseréje** gombot. A csere letöltésként fut: a párbeszédablakban és a **Sorban** mutatja az előrehaladását, a párbeszédablak pedig jelzi, mikor végzett.

Ha meghiúsul (a videó nem érhető el, vagy a YouTube bejelentkezést kér — lásd: [YouTube sütik](youtube-cookies.md)), a fájlod pontosan úgy marad, ahogy volt. A Sor **Újra** gombja ugyanazt a videót próbálja meg újra, a Sorban egy másik hivatkozást beillesztve pedig azzal cserél.

## Ami változatlan marad

- **A fájl.** Az új hang ugyanarra az útvonalra, ugyanabban a formátumban íródik: az `.mp3` MP3 marad (a [Letöltési beállításokban](download-settings.md) választott bitrátával), a `.flac` FLAC, és így tovább. Így minden lejátszási lista, M3U fájl, kedvelt szám, Navidrome-bejegyzés és párosított alkalmazás, amely a fájlra mutat, tovább mutat rá.
- **A címkék.** A cím, az előadók, az album, a sorszám, az év, a borító, a beágyazott dalszöveg és minden más címke változatlanul másolódik a régi fájlból az új hangra. A `.lrc` kísérőfájlhoz nem nyúl. Az időzített dalszöveg a régi hanghoz volt időzítve: ha az új verzió máshol kezdődik, elcsúszhat.
- **A dátum.** A fájl megtartja a módosítási dátumát, így nem ugrik a „Nemrég hozzáadva” elejére.

Csak `.mp3`, `.flac`, `.m4a`, `.ogg` és `.opus` fájlok — a Downtify által írt formátumok — cserélhetők.

## Hogyan működik

A kiválasztott videót a fájl mellé tölti le a könyvtár által figyelmen kívül hagyott ideiglenes néven (`<név>.downtify-upgrade.<kiterjesztés>`), átalakítja a fájl formátumára, ellenőrzi, hogy olvasható hang-e, ráteszi a régi fájl címkéit, és csak ezután mozgatja a régi fájl fölé. Az API az [API-referenciában](../api-reference.md#get-apilibraryreplacecandidates) található.
