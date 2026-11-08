---
icon: lucide/life-buoy
---

# Hibaelhárítás

Gyakori problémák és ami megoldja őket. A legtöbb letöltési hiba az első két bejegyzés egyikére vezethető vissza.

## Egy explicit tartalmú szám nem tölthető le

**Tünet** — a letöltés meghiúsul, és a sor üzenetet mutat arról, hogy a szám korhatáros, vagy (régebbi verzióknál) nyers hibát, például:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Ok** — a YouTube a korhatáros (explicit) számokat csak bejelentkezett felnőtt fióknak szolgáltatja ki. A Downtify alapértelmezetten névtelenül tölt le, ezért a YouTube elutasítja.

**Megoldás** — adj meg YouTube-sütiket: **Beállítások** (⚙️) → **YouTube sütik** → **cookies.txt feltöltése**. A fájl exportálásáról lásd: [YouTube sütik](features/youtube-cookies.md).

Ha sütikkel is meghiúsul, a sütik elavultak, vagy maga a fiók nem végezte el a Google korhatár-ellenőrzését. Exportálj friss fájlt egy ellenőrzött fiókba bejelentkezett böngészőből, és töltsd fel újra.

## A letöltések meghiúsulnak, időtúllépést kapnak vagy el sem indulnak

**Tünet** — a letöltések látszólag szokásos számoknál hibáznak, néha „Jelentkezz be, hogy megerősítsd, nem vagy robot” üzenettel vagy formátum-/kinyerési hibával.

**Ok** — a YouTube korlátozza és kihívás elé állítja az automatizáltnak tartott kéréseket. Ez VPS-en vagy VPN mögött sokkal gyakoribb, mint otthoni kapcsolaton.

**Megoldás**, aszerint rendezve, mennyire szokott segíteni:

1. **Tölts fel egy `cookies.txt` fájlt** ([YouTube sütik](features/youtube-cookies.md)). A hitelesített munkamenetet sokkal ritkábban állítják kihívás elé. Ez az egyetlen leghatékonyabb javítás.
2. **Adj szünetet a letöltések közé** — **Beállítások** → *Szünet a letöltések között* (próbálj 5–15 mp-et), és csökkentsd a *Párhuzamos letöltések* számát. Az egész lejátszási listával egyszerre zaklatni a YouTube-ot váltja ki a korlátozást.
3. **Kényszerítsd az IPv4-et** — állítsd be a `DOWNTIFY_FORCE_IPV4=1` értéket, ha a gazdagéped IPv6-ot hirdet, de valójában nem tudja irányítani (DNS-/`EAI_AGAIN`-hibaként jelentkezik).
4. **Frissítsd a képfájlt** — `docker compose pull && docker compose up -d`. A YouTube gyakran változtatja a védelmét, és minden kiadás újabb `yt-dlp`-t hoz.

## A Windowson / Docker Desktopon lévő cookies.txt nem érvényesül

**Tünet** — a `DOWNTIFY_COOKIES_FILE` be van állítva, de a Downtify úgy viselkedik, mintha nem lennének sütik.

**Ok** — az útvonal *konténerbeli* útvonal. Egy Windows-útvonal, például `C:\Users\me\cookies.txt`, nem jelent semmit a konténeren belül, és a fájlt csatolni kell, mielőtt a változó rámutathatna.

**Megoldás** — hagyd el egészen a változót, és töltsd fel a fájlt a **Beállítások** → **YouTube sütik** oldalon. Ehhez nem kellenek csatolások, és minden platformon ugyanúgy működik.

Ha meg akarod tartani a változót, csatold a fájlt, és a csatolás célhelyére mutass, ne a gazdagép útvonalára:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## A sütifeltöltő gomb szürke

A `DOWNTIFY_COOKIES_FILE` be van állítva, így az adott telepítés maga kezeli a sütifájlját, és a webes felület szándékosan csak olvasható marad. Töröld a változót (és hozd létre újra a konténert), hogy a sütiket a felületen kezelhesd.

## A feltöltött sütik eltűntek a konténer frissítése után

A feltöltött fájl a Downtify adatkönyvtárában (`/data`) van. Ha ez a könyvtár nem névvel ellátott kötet vagy bind mount, minden, ami benne van — a beállításokat és a Lejátszási lista figyelő adatbázisát is beleértve — elvész, amikor a konténert újra létrehozod:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← ezt tartsd meg
```

## „cookies.txt is invalid” feltöltéskor

A Downtify feltöltéskor ellenőrzi a fájlt. Netscape sütifájlnak kell lennie: soronként egy süti, a mezők tabulátorral elválasztva, opcionálisan `#` megjegyzésekkel. A JSON-exportot, a táblázatot vagy a bemásolt `Cookie:` fejlécet elutasítja.

Használj olyan böngészőbővítményt, amely Netscape formátumban exportál (lásd: [YouTube sütik](features/youtube-cookies.md)), és akkor exportálj, amikor a lap a `youtube.com` oldalon van.

## Egy lejátszási lista újra letölti a számokat, amelyek már megvannak

A Downtify az adatbázisában rögzíti minden automatikusan letöltött számot, ezért a fájlok lemezen belüli máshová helyezése nem vált ki újraletöltést. Egy számot csak akkor tölt le újra, ha egy óránkénti ellenőrzés megállapítja, hogy a fájlja ténylegesen hiányzik a letöltési könyvtárból. Lásd: [Lejátszási lista figyelő](features/playlist-monitor.md#how-it-works).

Ha a fájlok minden újraindításkor eltűnnek, a `/downloads` kötet nem tartós — ugyanaz a javítás, mint fent.

## „Could not find a YouTube match for '…'”

Sem a YouTube Music, sem a hagyományos YouTube nem adott olyan találatot, amely átment az illesztő ellenőrzésein — a forráshoz hasonló cím, legalább egy közös előadó, nem karaoke-/feldolgozás-/élő/más nyelvű verzió, és a Spotify hosszától legfeljebb 30 másodpercnyi eltérés. Lásd: [Hogyan működik](how-it-works.md#fallback-to-standard-youtube).

Ez általában azt jelenti, hogy a dal valóban nincs a YouTube-on, vagy csak egészen más címmel vagy előadói jelöléssel töltötték fel. Ha magad megtalálod a helyes videót, illeszd be a YouTube-URL-jét a keresősávba, hogy pontosan azt a videót töltsd le.

## A letöltött hang metaadatai vagy borítója rossz

A Downtify a metaadatokat a Spotifyból oldja fel, és a hangot a YouTube Musicon illeszti. Eltérés általában azt jelenti, hogy az illesztés feldolgozásra, remixre vagy élő verzióra esett. A Spotify **album** hivatkozásából letöltve a keresési találat helyett az illesztő sokkal több támpontot kap (sorszám, album, kiadás típusa).

## Még mindig elakadtál?

Nyiss egy issue-t a [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) oldalon, és add meg:

- a Downtify verzióját (az oldalsáv alján és a **Beállítások → Névjegy** oldalon látható),
- a konténernaplókat a hiba környékén (`docker compose logs downtify`),
- és hogy be vannak-e állítva sütik.
