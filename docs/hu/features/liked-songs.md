---
icon: lucide/heart
---

# Kedvelt számok

Koppints egy szám szívére, hogy kedveld. Amint egy számot kedvelsz, a Downtify vezet egy **Kedvelt számok** lejátszási listát az összes kedvelt számmal, így a kedvenceid egy kattintásra vannak — a Downtifyban és minden, a könyvtáradra mutató médiaszerveren.

Nincs mit bekapcsolni.

A szívek azé, aki megérintette őket: több fiókos szerveren mindenkinek saját kedvelt számai vannak (lásd: [Felhasználók és bejelentkezés](users.md#your-library)). A lemezen lévő lejátszási listafájl az adminisztrátorok szíveit tartalmazza; mindenki másé a könyvtár adatbázisában él, és az alkalmazásokban ugyanúgy működik.


## Szám kedvelése

A szív a könyvtárad minden száma mellett ott van — letöltések és [meglévő zenemappák](external-library.md) számai:

- a számlistákban — Könyvtár, albumok, előadók és lejátszási listák;
- a [lejátszósávban](player.md#player-bar) (640 px vagy szélesebb képernyőn);
- a [Most szól](player.md#now-playing) nézetben, a szám címe mellett.

Koppints a kedveléshez, koppints újra a visszavonáshoz. Zöldre telik, és a változás azonnal a szerveren van, így a telefonon megérintett szív az asztali gépen is ott van — a megnyitott lapok és eszközök maguktól követik.

Csak a könyvtáradban lévő számok kedvelhetők. Egy még nem letöltött keresési találatnak nincs szíve; előbb töltsd le.

## A lejátszási lista

Az első kedvelés létrehozza a listát, és egy rövid értesítés felajánlja a megnyitását. Úgy szerepel, mint bármely más lejátszási lista — az oldalsávon, a Kezdőlapon és a **Könyvtár → Lejátszási listák** alatt —, de mindig **elsőként**, borító helyett szívvel. A számai úgy vannak rendezve, hogy a legutóbb kedvelt van legfelül.

Az utolsó kedvelés visszavonásakor a lista ismét eltűnik; nem marad üres **Kedvelt számok** a nyakadon.

A cím a [nyelvedet](internationalization.md) követi. A lemezen a lejátszási lista egy egyszerű [M3U fájl](m3u-export.md) rögzített névvel:

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

Ezért mutatja a Jellyfin, a Navidrome, a Plex és társaik is: ugyanazt a fájlt olvassák. A név szándékosan foglalt. A *Liked Songs* nevű Spotify-listák gyakoriak, és egy ilyen nevű letöltött lejátszási lista különben ugyanabba a fájlba írt volna.

## Az összes kedvelés eltávolítása

Nyisd meg a listát, majd **⋯ → Összes kedvelés eltávolítása**, és erősítsd meg. Minden szív törlődik, a lista pedig eltűnik.

::: info A számaid megmaradnak
A kedvelések eltávolítása soha nem töröl hangot. Csak a szívek és a lista tűnnek el — a fájlok a könyvtáradban maradnak. Ez más, mint egy letöltött lejátszási lista törlése, amely a számait is törli; a **Kedvelt számok** listát soha nem kezeljük így. A törlésének kérése (az alkalmazásban vagy az [API](../api-reference.md#delete-apilibraryplaylist) útján) csak a kedveléseket törli.
:::

## A kedvelések és a fájlok szinkronban tartása

Egy kedvelés követi azt a fájlt, amelynek adták:

| Mi történik a fájllal | Mi történik a kedveléssel |
|--------------------------|--------------------------|
| Törlöd a számot a Downtifyban | A kedvelés vele megy, és a lista újraíródik |
| Áthelyezed, és lefuttatod a [Könyvtárútvonalak javítása](library-catalog.md#fix-library-paths) funkciót | A kedvelés követi a fájlt az új helyére |
| A Downtify-on kívül eltűnik (leválasztott meghajtó, kézi törlés) | A kedvelés megmarad, de a szám kimarad a listából, amíg vissza nem kerül |

A hiányzó fájl kedvelésének megtartása azt jelenti, hogy egy kihúzott meghajtó nem veszi el a szíveidet. Ha kézzel töröltél fájlokat, és a kedvelések is menjenek, használd az **Összes kedvelés eltávolítása** funkciót, vagy a törlés előtt vond vissza a számok kedvelését.

## Jó tudni

- A kedvelések a könyvtár adatbázisában (`downtify_library.db`, a `/data` köteteden) tárolódnak, nem a hangfájlokban. A szám címkéibe semmi sem íródik.
- A listát a Downtify nem hozza létre a [Navidrome](slskd-navidrome.md)-ban. Egyszerű M3U fájl, így az, hogy egy médiaszerver mit kezd vele, azon múlik, hogyan olvassa az M3U fájlokat.
- A [lejátszási listafájl](m3u-export.md) akkor is megíródik, ha a letöltési beállításokban az *M3U lejátszási listák írása* ki van kapcsolva: a funkció lényege maga a lista.

## API

`GET /api/likes`, `PUT /api/likes` és `POST /api/likes/clear`, valamint egy `liked` jelző a [`GET /playlists`](../api-reference.md#get-playlists) válaszában. Lásd az [API-referenciát](../api-reference.md#likes).
