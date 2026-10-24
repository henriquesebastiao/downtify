---
title: Deemix
icon: lucide/music
---

# Deemix hangforrás

A Deemix opcionális hangforrás, alapértelmezetten ki van kapcsolva. Állítsd be a
**Beállítások → Hangforrások** alatt, a slskd alatt, és kapcsold be a források sorrendjében.
Szükséged van a saját, kompatibilis Deemix-szerveredre és egy Deezer-fiókra, amely jogosult
a kért minőségre. Nem biztosít előfizetést, és nem kerül meg egyet sem.

## Hitelesítő adatok és megosztott mappák

Tartsd meg a Deemix szokásos, munkamenetenkénti bejelentkezési módját. Ne kapcsold be az
egyfelhasználós módot védtelen szerveren: a csatlakozási végpontja visszaadja a megosztott ARL-t.

Csatolj a Downtifyba egy privát fájlt a Deezer ARL-eddel, amely csak a szolgáltatásfiókja
számára olvasható, és állítsd a `DOWNTIFY_DEEMIX_ARL_FILE` értékét erre az útvonalra.
Az ARL-t csak sütis munkamenet megnyitásakor olvassa be. Soha nem tárolódik a
beállításokban, nem kerül vissza a böngészőbe, és nem kerül naplóba. Kezeld jelszóként;
privátban szerezd be és cseréld, ne issue-kban vagy csevegésben. Az integráció
soha nem módosítja a Deemix szerverszintű bejelentkezési vagy letöltési beállításait.
A kapcsolatteszt nem állít sorba letöltéseket.

| Beállítás                     | Cél                                                                |
| ----------------------------- | ------------------------------------------------------------------ |
| Szerver URL-je                | A Deemix belső címe, pl. `http://deemix:6595`                      |
| Letöltési mappa a Deemixben   | Általában `/downloads`                                             |
| Ugyanaz a mappa a Downtifyban | Megosztott bind mount, pl. `/deemix`; a csak olvasható is támogatott |
| Minőség                       | MP3 128, MP3 320 vagy FLAC; a nem támogatott jogosultságok kifejezetten hibával járnak |

A megosztott mappa mentéskor külső könyvtármappaként kerül regisztrálásra.
A fájlok ott maradnak, a Deemix előadó/album szerinti szervezésében. A Downtify megőrzi
a formátumukat, címkéiket, borítóikat és `.lrc` kísérőfájljaikat, újraírás nélkül.
A beágyazott dalszövegeket és az azonos nevű `.lrc` fájlokat a lejátszó olvassa.
Ez az integráció semmilyen hangot vagy dalszöveget nem töröl, nem mozgat és nem generál.

Egy Deezer-számhivatkozás azt a felvételt választja ki. A katalógusok közötti letöltésekhez
egyértelmű, pontos előadó/cím egyezés kell, album- és hosszegyezéssel,
ha meg van adva. A kétértelmű egyezés a következő engedélyezett forrásra esik vissza.
A Deemix-sor befejezését fájl- és hossz/minőség-ellenőrzés követi.
Az integráció soha nem üríti, nem szakítja meg és nem módosítja a kézi Deemix-feladatokat.
A kifejezett YouTube-hivatkozások megtartják a jelenlegi közvetlen letöltési viselkedésüket.

Ez a forrás nem cseréli le és nem törli automatikusan a könyvtár egy meglévő
számát. A könyvtár duplikátumkezelése és a kézi hangcsere külön marad.
