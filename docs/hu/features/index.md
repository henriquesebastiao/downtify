---
icon: lucide/sparkles
---

# Funkciók

A Downtify mindent lefed, amire szükséged van egy helyi zenekönyvtár felépítéséhez és karbantartásához a Spotifyból.

## Áttekintés

| Funkció | Mit csinál |
|---------|-------------|
| [Toplisták](charts.md) | Böngészd a Deezer globális listáját, és tölts le bármit, ami éppen felkapott |
| [Hasonlók](similar.md) | Adj meg egy előadót vagy számot; a YouTube Music hasonló számokkal válaszol, amelyek teljes hosszban lejátszhatók és letölthetők, kulcs nélkül |
| [Kereső](finder.md) | Keress a Deezeren, majd böngéssz oszlopokban egy előadót, albumait és bármely album számait |
| [Letöltési beállítások](download-settings.md) | Válaszd ki a formátumot (MP3/FLAC/M4A/OGG/OPUS), a bitrátát, a párhuzamos letöltéseket és a szünetet a letöltések között |
| [Lejátszási lista figyelő](playlist-monitor.md) | Figyelj Spotify- vagy YouTube Music-lejátszási listákat és előadókat, és automatikusan töltsd le az új számokat és kiadványokat |
| [Legnépszerűbb számok](top-songs.md) | Illessz be egy előadó hivatkozását, és töltsd le a legnépszerűbb dalait, opcionálisan lejátszási listaként |
| [Könyvtár importálása (CSV)](library-import.md) | Importálj egy Soundiiz-, TuneMyMusic- vagy Exportify-exportot, és állítsd sorba az egészet |
| [Beépített lejátszó](player.md) | Játszd le a könyvtárad a böngészőben: sorkezelés, időzített dalszövegek, elalvási időzítő, billentyűzet és médiabillentyűk |
| [Kedvelt számok](liked-songs.md) | Szívvel kedvelj egy számot; a kedvelt számokból magától megjelenik egy lejátszási lista |
| [Podcastok](podcasts.md) | Iratkozz fel egy műsorra RSS-csatornával, Spotify-hivatkozással vagy névvel; az új epizódok maguktól letöltődnek és címkézést kapnak |
| [Felhasználók és bejelentkezés](users.md) | Bejelentkezés felhasználónévvel és jelszóval (`admin` / `downtify` új szerveren), adminisztrátori és normál felhasználói fiókok, felhasználónkénti beállítások és tevékenységnapló a bejelentkezésekről és arról, ki mit hallgat |
| [Explicit jelölés](explicit-marker.md) | Az „E” az explicit szövegű dalok mellett — a keresésben, a Könyvtárban és a lejátszóban — és a fájl címkéiben |
| [Hang cseréje](replace-audio.md) | Rossz dal vagy verzió? Válaszd ki a helyeset a YouTube Musicon vagy a YouTube-on; a fájl megtartja nevét, címkéit és lejátszási listáit |
| [Szerverbeállítások](server.md) | A port, amelyen a Downtify figyel, a Beállításokból módosítható (adminisztrátorok), kívánság szerint azonnali újraindítással |
| [Mobilalkalmazások](mobile-apps.md) | Párosíts telefonos alkalmazásokat QR-kóddal, és streameld nekik a könyvtárat (eredeti vagy átkódolt) |
| [Felfedezés](discover.md) | Előadók, albumok és lejátszási listák, amelyek még nincsenek meg, a könyvtárad, kedvelésid és hallgatásod alapján ajánlva; rejtsd el, amit nem akarsz |
| [slskd és Navidrome](slskd-navidrome.md) | Tölts le a Soulseekről a slskd-n át, tükrözd a lejátszási listákat a Navidrome-ba, és kövesd a lejátszási listák letöltéseit |
| [Könyvtárkatalógus és útvonal-szinkronizálás](library-catalog.md) | Hogyan követi a Downtify a könyvtár fájljait és lejátszási listáit, a Könyvtárban létrehozott lejátszási listák, és az útvonalak javítása fájlok áthelyezése után |
| [Meglévő zenemappák](external-library.md) | Irányítsd a Downtifyt a már meglévő hangfájlmappákra; a szinkronizálás beolvassa a címkéket, párosítja az előadókat, és kihagyja a könyvtárban már meglévő dalokat |
| [Könyvtár javítása](library-upgrade.md) | Szkenneld a már letöltött zenét, és javítsd a kis borítókat, a hiányzó dalszövegeket és a hiányos címkéket |
| [M3U-exportálás](m3u-export.md) | Automatikusan előállított lejátszásilista-fájlok a Jellyfinhez, Navidrome-hoz, Plexhez és bármely médiaalkalmazáshoz |
| [Lejátszási lista borítók](playlist-cover-art.md) | Mentsd el a lejátszási lista saját borítóképét az M3U fájl mellé |
| [Előadó fotója, bannere és bemutatkozása](artist-images.md) | Válassz valódi fotót és bannert egy előadóhoz a YouTube Musicból, Deezerről, Spotifyról vagy saját feltöltésből, és kérd le a bemutatkozását, származását és hivatkozásait az Apple Musicról és a Deezerről, automatikusan vagy kérésre |
| [Fájlszervezés](file-organization.md) | Lapos elrendezés vagy előadónkénti almappák |
| [Dalszövegek](lyrics.md) | Dalszövegek (egyszerű és időzített) automatikus letöltése és beágyazása; `.lrc` a fájl mellett vagy egy általad választott mappában |
| [YouTube sütik](youtube-cookies.md) | Tölts fel egy `cookies.txt` fájlt a webes felületen az explicit/korhatáros számok letöltéséhez |
| [Nemzetköziesítés](internationalization.md) | Az angol és kilenc további nyelv alapból, és a dokumentáció mindegyiken |
| [Frissítési értesítések](updates.md) | Óránkénti ellenőrzés a GitHub Releases oldalán; az oldalsávon értesítés jelenik meg, ha újabb verzió jelent meg |

## Bemenetek típusai

A Downtify a keresősávban többféle bemenetet fogad el:

| Bemenet | Példa |
|-------|---------|
| Spotify-szám, -album, -lejátszási lista vagy -előadó URL-je | `https://open.spotify.com/track/…` |
| YouTube / YouTube Music URL | `https://www.youtube.com/watch?v=…` |
| YouTube Music lejátszási lista vagy előadó URL-je | `https://music.youtube.com/playlist?list=…` |
| Deezer-szám, -album, -lejátszási lista vagy -előadó URL-je | `https://www.deezer.com/track/…` |
| Szabad szöveges keresés | `The Night Owls Do I Still Recall` |

A szabad szöveges keresések közvetlenül a YouTube Musichoz mennek — nem kell Spotify-hivatkozás.
