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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Írhatóan csatold (`:ro` nélkül), hogy az életben tartás el tudja menteni bele a lecserélt sütiket; a csak olvasható fájlt továbbra is használja, de az a korábbiakhoz hasonlóan elavul.

Ha be van állítva, a beállítások képernyő zároltan mutatja a sütik szakaszt, és elutasítja a feltöltést és a törlést — a konfigurációt a telepítés birtokolja, és a Downtify nem írhat felül olyan fájlt, amelyet nem ő kezel. Töröld a változót (és hozd létre újra a konténert), hogy a sütiket inkább a webes felületen kezeld.

A `DOWNTIFY_COOKIES_FROM_BROWSER` közvetlenül egy böngészőprofilból olvassa a sütiket, ehhez viszont a böngésző sütitárának a konténeren *belülről* elérhetőnek kell lennie, így Dockerben ritkán használható.

## Működőképesen tartásuk

Az exportált sütik nem egy adott napon járnak le. A Google-munkamenet folyamatosan változó sütikből áll: a lap, ahonnan származnak, néhány percenként lecseréli a `__Secure-1PSIDTS`, `SIDCC` és hasonló sütiket, és az a másolat, amely sosem kapja meg az új értékeket, előbb-utóbb elutasításra kerül. A yt-dlp ilyenkor ezt naplózza: „The provided YouTube account cookies are no longer valid”. VPN-en vagy adatközponti IP-ről a YouTube szigorúbb, így ez akár néhány óra alatt bekövetkezhet.

A Downtify magától bejelentkezve tartja a feltöltött fájlt:

- **Minden letöltés elmenti az új értékeket.** A yt-dlp minden letöltéshez saját másolatot kap a fájlról; a végén a YouTube által közben módosított sütik visszakerülnek a tárolt `cookies.txt` fájlba, anélkül hogy felülírnának egy újabb értéket, amelyet közben egy másik letöltés mentett el.
- **Időzített életben tartás frissíti őket.** 15 percenként (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, a `0` kikapcsolja) a Downtify megkéri a Google-t a munkamenet-sütik cseréjére – ugyanazzal a kéréssel, amelyet a böngésző küld –, megnyitja velük a `youtube.com` oldalt, és elmenti, ami változott. Még a napokig semmit sem letöltő szerver munkamenete is élő marad.
- **A beállítások képernyője mutatja az eredményt.** A **Beállítások → YouTube sütik** ezt mutatja: *Bejelentkezve*, *Kijelentkezve*, *Nincs fiók* (a fájlban nincs Google-munkamenet, csak látogatói sütik) vagy *Az ellenőrzés sikertelen*, valamint hogy mikor volt az utolsó ellenőrzés, és mikor kért utoljára robotellenőrzést a YouTube. Az *Ellenőrzés most* azonnal lefuttatja az életben tartást. Az új feltöltést a mentés után néhány másodperccel ellenőrzi.

Ami továbbra is rád marad:

- **Privát ablakból exportálj, majd zárd be.** Jelentkezz be a YouTube-ra egy privát ablakban, ugyanabban a lapon nyisd meg a `youtube.com/robots.txt` oldalt, exportáld a sütiket, majd zárd be az ablakot. Egy tovább használt lap magától lecseréli a munkamenetet, és a Downtify másolata percek alatt kijelentkezik. Ha teheted, ne használd ugyanazt a fiókot egyszerre egy normál ablakban.
- **Tölts fel új fájlt, ha a képernyő *Kijelentkezve* állapotot mutat.** A Google ettől még megszakíthatja a munkamenetet (jelszócsere, „kijelentkezés minden eszközről”, biztonsági ellenőrzés). A napló is jelzi: `YouTube cookies are signed out`.
- Egyes régiókban a Google-fiók teljes személyazonosság-ellenőrzése szükséges, mielőtt a YouTube bármilyen korhatáros tartalmat kiszolgálna. A bejelentkezés nem mindig elég.

::: info Miért nincs „Bejelentkezés Google-fiókkal” gomb
A Downtify nem tud helyetted bejelentkezni a Google-be. A Google letiltja a szkriptelt és headless böngészős bejelentkezéseket („Előfordulhat, hogy ez a böngésző vagy alkalmazás nem biztonságos”), kétlépcsős azonosítást és eszközön történő megerősítést kér, a YouTube pedig már nem fogad el OAuth-ot olyan külső kliensektől, mint a yt-dlp. Egy bejelentkezési űrlap a Downtifyban azt is jelentené, hogy átadod neki a Google-jelszavadat. Egy exportált munkamenet életben tartása az a rész, amely automatizálható.
:::

::: tip Robotellenőrzés fiók nélkül
A „Sign in to confirm you're not a bot” az IP-címtől függ, nem a hiányzó sütiktől. Ha VPN-en folyton megjelenik, a VPN-szerver vagy a kilépési ország cseréje gyakran többet segít, mint az új sütik. A sok letöltéshez használt sütik növelik annak esélyét is, hogy a YouTube korlátozza a fiókot, ezért egy eldobható fiók a biztonságosabb választás.
:::

::: warning Kezeld a fájlt jelszóként
A `cookies.txt` a Google-fiókod élő munkamenet-tokenjeit tartalmazza. Aki el tudja olvasni, a YouTube-on a nevedben cselekedhet. A Downtify ott, ahol a fájlrendszer támogatja, csak a tulajdonos számára hozzáférhető jogosultságokkal tárolja, és a tartalmát soha nem teszi közzé az API-n — csak azt, hogy be van-e állítva, a méretét és a módosítás idejét. Használj eldobható Google-fiókot, ha nem kockáztatnád a fő fiókodat.
:::
