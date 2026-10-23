---
icon: lucide/cookie
---

# YouTube sütik

A Downtify a hangját a YouTube-ról szerzi. Legtöbbször ez névtelenül is működik — de nem mindig:

- **Explicit / korhatáros számok.** A YouTube ezeket csak bejelentkezett felnőtt fióknak szolgáltatja ki. Sütik nélkül a letöltés sikertelen.
- **Bot-ellenőrzések.** Adatközponti IP-címeken (VPS, egyes VPN-ek) a YouTube időnként hang helyett azt válaszolja: „Jelentkezz be, hogy megerősítsd, nem vagy robot”.

Egy `cookies.txt` megadása mindkettőt megoldja: a yt-dlp ekkor úgy beszél a YouTube-bal, ahogy a bejelentkezett böngészőmunkameneted.

## cookies.txt feltöltése (ajánlott)

1. Telepíts egy sütiexportáló bővítményt: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) vagy [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Nyisd meg a `youtube.com` oldalt **a Google-fiókodba bejelentkezve**, és exportáld az oldal sütijeit — a fájlnak **Netscape** formátumúnak kell lennie
3. A Downtifyban nyisd meg a **Beállítások** (⚙️) → **YouTube sütik** → **cookies.txt feltöltése** menüpontot

A fájlt feltöltéskor ellenőrzi — az a fájl, amely nem Netscape-sütifájl, azonnal elutasításra kerül, ahelyett hogy csendben tönkretenné az összes későbbi letöltést. Ha nem tartalmaz `youtube.com` vagy `google.com` sütit, figyelmeztetést kapsz, mert ez általában azt jelenti, hogy rossz lapról exportálták.

Feltöltés után ugyanazon a képernyőn **lecserélheted** (másik fájl feltöltésével) vagy **törölheted**.

::: tip Ez a platformfüggetlen út
A webes felületen át történő feltöltéshez nem kell bind mount, fájlútvonal vagy shell — ezért működik a Windowsos Docker Desktopon is, ahol egy `cookies.txt` konténerbe csatolása közismerten bonyolult.
:::

## Hol tárolódik

A feltöltött fájl `cookies.txt` néven íródik a Downtify adatkönyvtárába (alapértelmezés: `/data`) — ugyanabba a kötetbe, amely a `settings.json` fájlt és a Lejátszási lista figyelő adatbázisát tartalmazza. Ezért **túléli a konténerfrissítéseket**: új kép lehúzása és a konténer újralétrehozása megtartja a sütiket, amíg a `/data` névvel ellátott kötet vagy bind mount marad.

## Környezeti változó használata helyette

A korábban is létező [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) változó továbbra is működik, és **elsőbbséget élvez**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Ha be van állítva, a beállítások képernyő zároltan mutatja a sütik szakaszt, és elutasítja a feltöltést és a törlést — a konfigurációt a telepítés birtokolja, és a Downtify nem írhat felül olyan fájlt, amelyet nem ő kezel. Töröld a változót (és hozd létre újra a konténert), hogy a sütiket inkább a webes felületen kezeld.

A `DOWNTIFY_COOKIES_FROM_BROWSER` közvetlenül egy böngészőprofilból olvassa a sütiket, ehhez viszont a böngésző sütitárának a konténeren *belülről* elérhetőnek kell lennie, így Dockerben ritkán használható.

## Működőképesen tartásuk

- A sütik lejárnak. Ha a korhatáros letöltések ismét hibáznak, exportálj új fájlt, és tölts fel cserének.
- Egy **privát/inkognitó ablakból** exportálva, amelyet utána bezársz, hosszabb életű munkamenetet kapsz, mert egy normál ablak bezárása érvénytelenítheti az exportált munkamenetet.
- Egyes régiók a Google-fiók teljes személyazonosság-ellenőrzését kérik, mielőtt a YouTube egyáltalán korhatáros tartalmat szolgáltatna. A bejelentkezés nem mindig elég.

::: warning Kezeld a fájlt jelszóként
A `cookies.txt` a Google-fiókod élő munkamenet-tokenjeit tartalmazza. Aki el tudja olvasni, a YouTube-on a nevedben cselekedhet. A Downtify ott, ahol a fájlrendszer támogatja, csak a tulajdonos számára hozzáférhető jogosultságokkal tárolja, és a tartalmát soha nem teszi közzé az API-n — csak azt, hogy be van-e állítva, a méretét és a módosítás idejét. Használj eldobható Google-fiókot, ha nem kockáztatnád a fő fiókodat.
:::
