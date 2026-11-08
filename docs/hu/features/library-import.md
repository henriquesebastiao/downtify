---
icon: lucide/import
---

# Könyvtár importálása (CSV)

Már exportáltad a könyvtáradat egy másik szolgáltatásból? Importáld a CSV-t, és tedd sorba az összes számot letöltésre egyszerre, ahelyett hogy egyesével adnád hozzá a dalokat.

## Támogatott exportálók

| Eszköz | Megjegyzések |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

A Downtify egyetlen eszköz pontos oszlopsémáját sem kódolja be. Ehelyett a CSV fejlécsorát kis- és nagybetűk megkülönböztetése nélkül veti össze ismert aliasok halmazával (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … és `Album` / `Album Name` / `Album Title` / …), így a három bármelyikének exportja — vagy egy kézzel készített, ugyanezeket az oszlopneveket használó CSV — átnevezés nélkül működik.

A cím és az előadó kötelező. Az albumot beolvassa, ha van, és a szám albumneveként tárolja (Sor, illesztés és fájlcímkék). Egyes exportálók további oszlopait (ISRC, Spotify-számazonosító URI, hossz) figyelmen kívül hagyja. Minden sor feloldása ugyanúgy történik, mint egy szabad szöveges keresésé, a YouTube Musicon keresztül.

## Az importálás menete

1. A kezdőlapon kattints a keresőmező alatti **CSV importálása (Soundiiz, Exportify…)** gombra.
2. Válaszd ki az exportált `.csv` fájlt.

A fájlt teljes egészében a böngésződ olvassa be, és egyszerű szövegként küldi el a szervernek — máshová sosem töltődik fel. A Downtify feldolgozza, sorba állítja az összes felismert sort, te pedig a Letöltési sorra érkezel, ahol az előrehaladás WebSocketen át érkezik, pontosan úgy, mint bármely más kötegelt letöltésnél.

Az importált köteg a fájlról kapja a nevét (a neve `.csv` nélkül), és — mint bármely más lejátszási lista letöltése — [M3U fájlt](m3u-export.md) kap, ha ez a beállítás be van kapcsolva.

## Korlátok és hibakezelés

- Fájlonként legfeljebb **2000 sor**. A nagyobb exportokat oszd több fájlra.
- A cím vagy előadó nélküli sorokat szó nélkül kihagyja. A hiányzó albumoszlop vagy az üres albumcella nem gond — a YouTube Music később még kitöltheti az albumot.
- Egy cellában több előadó (`,` vagy `;` választja el őket) listává bomlik.
- Ha a fejléc nem tartalmaz felismerhető cím/előadó oszlopot, a teljes importálást eleve elutasítja egy hibával, amely megnevezi a talált oszlopokat — semmi sem kerül sorba.

## A kéréskorlátok elkerülése

Egy nagy könyvtár importálása rövid idő alatt sok YouTube Music-keresést és letöltést állít sorba, ami könnyen kéréskorláthoz vezet. Egy nagy fájl importálása előtt érdemes csökkenteni a **[Párhuzamos letöltések](download-settings.md#parallel-downloads)** számát, és bekapcsolni a **[Szünet a letöltések között](download-settings.md#delay-between-downloads)** beállítást.

## API

Az alapul szolgáló végpontot lásd a [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) résznél az API-referenciában.
