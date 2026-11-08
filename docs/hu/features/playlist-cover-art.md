---
icon: lucide/image
---

# Lejátszási lista borítók

A Downtify elmentheti a lejátszási lista saját borítóját az [M3U fájl](m3u-export.md) mellé, hogy a médiaszerverek és fájlböngészők a lejátszási lista valódi képét mutassák egy általános ikon helyett.

Alapértelmezetten be van kapcsolva. Kikapcsolása: **Beállítások → Letöltések és fájlok → Lejátszási lista borítójának mentése**.

## Hová kerül a fájl

A borító **a lejátszási lista M3U-jával azonos néven és azonos mappába** íródik, `.jpg` kiterjesztéssel:

```
<downloads>/<lejátszási-lista-neve>/<lejátszási-lista-neve>.m3u
<downloads>/<lejátszási-lista-neve>/<lejátszási-lista-neve>.jpg
```

Ha a *Rendezés előadó szerint* vagy a *Rendezés album szerint* be van kapcsolva, a számok előadómappákban oszlanak szét, az M3U pedig egy központi `Playlists/` könyvtárba kerül (lásd: [Fájlszervezés](file-organization.md)) — a borító követi:

```
<downloads>/Playlists/<lejátszási-lista-neve>.m3u
<downloads>/Playlists/<lejátszási-lista-neve>.jpg
```

::: info Kell hozzá az M3U
Ha az **M3U listák írása** ki van kapcsolva, borító sem mentődik: a Downtify a képet az M3U útvonala alapján helyezi el, enélkül nincs hova tenni. A beállítás rejtve van, amíg az M3U-írás ki van kapcsolva.
:::

## Források és felbontás

| Forrás | Felbontás |
|--------|-----------|
| **Spotify** | A legnagyobb kép, amelyet a nyilvános beágyazási oldala a lejátszási listához kínál — ugyanaz, amelyet a számok borítójához is használnak |
| **YouTube Music** | Mindig 1200×1200-ban kéri, függetlenül a [Borító felbontásától](download-settings.md#cover-art-resolution), amely csak a számonkénti borítókat érinti |

Mindkét szolgáltatás JPEG-et szolgáltat ezekhez az URL-ekhez, még ha az eredeti kép PNG volt is, ezért a fájl mindig `.jpg`-ként mentődik.

## Mikor töltődik le

**A számok előtt**, mindkét esetben — a mappa már töltés közben a lejátszási listához hasonlít, és egy letöltés közben szkennelő médiaszerver a képet találja meg, nem egy csupasz mappát:

- **Kézi lejátszásilista-letöltés** — egyszer, amint a lejátszási lista neve feloldódott, az első szám indulása előtt.
- **[Lejátszási lista figyelő](playlist-monitor.md)** — átfutásonként egyszer, amelynek van letöltenivalója, az adott átfutás első száma előtt. Az az átfutás, amely nem talál semmi újat, nem tölti le újra.

A borító feloldásának vagy letöltésének kudarca (hálózati hiba, kép nélküli lejátszási lista) naplózásra kerül, és kimarad — magát a letöltést soha nem tartja fel és nem buktatja meg.

## A Downtify felületén

Az a lejátszási lista, amelynek saját képe van (Spotify- vagy YouTube-lejátszási listával letöltve), mindenhol azt mutatja, ahol a Könyvtár lejátszási listákat sorol fel — a rácson, a lejátszási lista oldalán, az oldalsávon és a lejátszóban. Azok a listák, amelyeknek nincs, és a Könyvtárban létrehozott listák legfeljebb négy különböző számborítóból álló mozaikot mutatnak: kettőt egymás mellett, hármat egy magas bal oldali csempeként és két egymásra helyezettként jobb oldalt, négyet 2×2-es rácsban. Ugyanez a kollázs `<lejátszási-lista-neve>.jpg` néven kerül egy kézi lejátszási lista M3U-ja mellé, hogy a Navidrome is lássa, és újra elkészül, valahányszor dalt adsz hozzá vagy távolítasz el.

## Navidrome

Nincs mit beállítani: a Navidrome a lejátszási lista képét egy **kísérő képből** oldja fel — a lejátszási lista nevét viselő fájlból ugyanabban a mappában —, és a Downtify pontosan ezt írja. Amíg a Navidrome zenemappája lefedi a letöltési mappádat, a kép a következő szkennelésekor megjelenik. A Downtify részéről nincs szükség API-hívásra. Lásd: [slskd és Navidrome](slskd-navidrome.md#navidrome).

## Takarítás

Egy lejátszási lista törlése a Könyvtár oldalról a borítóját is eltávolítja az M3U-val és a számokkal együtt — lásd: [Lejátszási lista törlése](slskd-navidrome.md#deleting-a-playlist).
