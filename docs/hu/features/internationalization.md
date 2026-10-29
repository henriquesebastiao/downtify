---
icon: lucide/languages
---

# Nemzetköziesítés

A Downtify két független helyen van lefordítva: az **alkalmazásban** (a felületén) és ebben a **dokumentációban**. Mindkettő alapértelmezett nyelve az **angol**, kilenc további nyelvvel készen.

## Nyelv váltása

### Az alkalmazás

Menj a **Beállítások → Nyelv** oldalra, és válaszd ki a kedvenc nyelvedet. A választás a böngésző `localStorage`-ában tárolódik, és az oldal újratöltése nélkül azonnal érvénybe lép. Az oldal minden betöltéskor és minden módosításkor a szervernek is jelzi (a `settings.json` `ui_language` bejegyzése, lásd: [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), hogy a böngésző nélkül futó munka is ismerje a nyelved - egy előadó életrajza, amelyet a háttérben kér le, amikor az egyik száma befejezi a letöltést, ezen a nyelven érkezik (lásd: [Amikor egy letöltés befejeződik](artist-images.md#when-a-download-finishes)). A te részedről nincs teendő: ha ez előtt választottál nyelvet, a Downtify következő megnyitásakor átveszi. Ha több böngésző van különböző nyelvekre állítva, az nyer, amelyik utoljára töltötte be vagy módosította.

### A dokumentáció

A dokumentáció abban a nyelvben nyílik meg, amelyet a böngésződ előnyben részesít, ha le van fordítva rá, különben angolul. A felső sáv jobb oldalán lévő **földgömb gomb** bármikor vált nyelvet, és ugyanazon az oldalon (és szakaszon) tart. A választásod megjegyződik a böngészőben, és attól kezdve felülírja a böngésző nyelvét, amíg másikat nem választasz.

Egy még le nem fordított oldal egy megjegyzést és az angol szöveget mutatja, így minden nyelvnek mindig megvan minden oldala.

## Elérhető nyelvek

| Kód | Nyelv | Alkalmazás | Dok. |
| ------- | ------------------ | --- | ---- |
| `en` | English (alapértelmezett) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

A fejlesztőknek szánt referencia-oldalak — az [API-referencia](../api-reference.md), a [mobilkliens-szerződés](../mobile-client-contract.md) és a változásnapló — minden nyelven angolul maradnak.

## Fordítás beküldése

Fordíthatod az alkalmazást, a dokumentációt, vagy mindkettőt. Ezek külön munkák külön fájlokkal, így egy pull request tartalmazhatja az egyiket vagy a másikat — vagy egy nyelv előbb az egyikhez, később a másikhoz is hozzáadható.

| Amit fordítasz | Hol vannak a fájlok | Mikor kész |
| ------------- | ------------------- | --------- |
| **Csak az alkalmazást** | `frontend/src/i18n/locales/<code>.js` | a nyelv megjelenik a **Beállítások → Nyelv** alatt |
| **Csak a dokumentációt** | `docs/.vitepress/locales/<code>.mjs` és a Markdown-oldalak a `docs/<code>/` mappában | a nyelv megjelenik a dokumentáció földgömb menüjében |
| **Mindkettőt** | mind a fenti | mindkettő |

Egy nyelvnek nem kell léteznie az alkalmazásban ahhoz, hogy a dokumentációhoz hozzá lehessen adni, és fordítva sem.

## Az alkalmazás fordítása

Egy fordítás hozzáadása az alkalmazáshoz háromlépéses folyamat:

### 1. Másold le az angol nyelvi fájlt

A nyelvi fájlok a `frontend/src/i18n/locales/` mappában vannak. Minden fájl egyetlen objektumot exportál, amelynek kulcsai az `en.js` szerkezetét követik. Fájlnévként használj egy [IETF nyelvi címkét](https://en.wikipedia.org/wiki/IETF_language_tag).

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Fordítsd le az értékeket

Hagyd változatlanul a kulcsokat, a helyőrző tokeneket (pl. `{count}`, `{name}`, `{file}`) és az általános szerkezetet — csak a jobb oldali szövegeknek kell változniuk. Állítsd a `language.name` értékét a nyelv **anyanyelvi** nevére (`"Français"`, `"Deutsch"`, …) — ez a nyelvválasztóban látható címke.

### 3. Regisztráld a nyelvet

Adj hozzá egy importot és egy bejegyzést az `AVAILABLE_LOCALES` tömbhöz a `frontend/src/i18n/index.js` fájlban:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Építsd újra a frontendet, és a nyelved automatikusan megjelenik a **Beállítások → Nyelv** alatt:

```bash
cd frontend && npm run build
```

### Tippek az alkalmazás fordításához

- A hiányzó kulcsok angolra esnek vissza, így a részleges fordítások is jól működnek — küldj PR-t azzal, amid van.
- A számtól függő szövegek többes számú alakokat tartalmazó objektumok, pl. `tracks: { one: '{count} track', other: '{count} tracks' }`. Az alakot a böngésző [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) szabálya választja a nyelvedhez, ezért add hozzá azokat az alakokat, amelyeket a nyelved használ (`zero`, `one`, `two`, `few`, `many`, `other`) — az `other` kötelező. A számokat a program automatikusan a nyelvnek megfelelően formázza.
- A helyőrző tokeneket, mint a `{count}` vagy a `{file}`, változatlanul kell hagyni; futásidőben helyettesítődnek.
- Tartsd tömören a szövegeket — a felület szűken van kialakítva, és a nagyon hosszú fordítások csúnyán törhetnek.
- Fordítás után futtasd az `npm run dev` parancsot a `frontend/` mappából, és járd végig az összes oldalt a nyelveden, hogy kiszúrd, ami kilóg vagy furcsán hat a szövegkörnyezetben.

## A dokumentáció fordítása

Az angol a forrás: a `docs/` mappában van. Minden más nyelvnek van egy a kódjáról elnevezett mappája (`docs/pt-BR/`) az angollal **azonos fájlnevekkel**, plusz egy fájl az oldal saját szövegeinek (`docs/.vitepress/locales/pt-BR.mjs`: az oldalsáv címei, a keresőmező, a lábléc, a kiemelő dobozok címkéi). Egy még le nem fordított oldal egy kis vázlat, amely megjegyzést mutat, és beilleszti az angol oldalt.

### Egy meglévő nyelv egy oldalának fordítása

A `docs/` mappából:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

A `start` a `docs/pt-BR/features/users.md` vázlatot az angol oldal másolatára cseréli. Fordítsd le a helyén, majd ellenőrizd:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Nyiss egy pull requestet, amikor az oldal jól olvasható; a részleges munka is szívesen látott — az oldalak, amelyekhez nem nyúltál, egyszerűen angolul maradnak.

### Nyelv hozzáadása a dokumentációhoz

1. Másold a `docs/.vitepress/locales/en.mjs` fájlt a `docs/.vitepress/locales/<code>.mjs` fájlba, és fordítsd le: az anyanyelvi `name` értéket, az oldal szövegeit (`ui`), a kiemelő dobozok címkéit (`containers`) és az oldalsáv címeit (`nav`).
2. Regisztráld a `docs/.vitepress/locales/index.mjs` fájlban.
3. Hozd létre az oldalakat csak angol vázlatokként: `npm run i18n -- stubs <code>`.
4. Fordítsd le az oldalakat egyenként az `npm run i18n -- start <code> <page>` paranccsal.

A nyelv a regisztrálás pillanatától megjelenik a földgömb menüben és a böngészőnyelv-felismerésben.

### Mit érdemes megtartani, és mit fordítani

- **Fordítsd** a szöveget, a címsorokat, a táblázatcellákat, a kiemelő dobozok címeit és a kezdőlap front matterében lévő `title`/`text` értékeket.
- **Hagyd változatlanul** a kódblokkokat, a soron belüli `code` részeket, az URL-eket, a környezeti változókat, az API-útvonalakat és mezőneveket, a fájl- és mappaneveket, valamint a front matter kulcsait és az `icon:` és `link:` értékeket. Egy kódblokkon belüli megjegyzés fordítása rendben van.
- **Hivatkozások**: pontosan tartsd meg az angol oldal relatív `.md` hivatkozásait (`[Dalszövegek](lyrics.md#sidecar-lrc-file)`). Egy csak angolul létező oldalra mutató hivatkozás továbbra is működik. A kezdőlapon a hivatkozások nyelvi előtaggal íródnak (`/pt-BR/features/player/`).
- **Címsorok**: tartsd meg ugyanazokat a címsorokat, ugyanabban a sorrendben és ugyanazokon a szinteken. A szakaszokra mutató hivatkozások (`#sidecar-lrc-file`) minden nyelven tovább működnek, mert a lefordított oldal az angol címsorazonosítókat használja újra — soha nem írsz vagy fordítasz azonosítót.
- **Gombok és beállítások nevei**: az alkalmazásnak megvan a saját fordítása minden címkéhez. Használd azt, félkövéren, hogy az oldal egyezzen azzal, amit az olvasó a képernyőn lát: keresd meg a címkét a `frontend/src/i18n/locales/<code>.js` fájlban. Ha az alkalmazás még nincs lefordítva az adott nyelvre, tartsd meg az angol címkét.
- **Kiemelő dobozok** (`::: tip Cím`): tartsd meg a fajtát (`info`, `tip`, `warning`, `danger`), és fordítsd le a címet. A cím nélküli doboz címkéje a `containers` szó a nyelvi fájlból.
- **Hangnem**: az adott nyelv olvasójának írj — az oldalak útmutatók, nem szó szerinti átültetések.

### A fordítások naprakészen tartása

Amikor egy angol oldal változik, a fordításainak nem kell ugyanabban a pull requestben változniuk: egy lefordított oldal tovább működik, az `npm run i18n -- status <code>` pedig felsorolja azokat az oldalakat, amelyek angol forrása a lefordításuk után változott. Frissíteni őket jó első hozzájárulás.

A tesztek (`npm test` a `docs/` mappában) ellenőrzik, hogy minden nyelvnek megvan minden oldala és minden oldalszövege, és hogy egy lefordított oldalnak még megvannak az angol oldal címsorai, kódblokkjai, táblázatai, kiemelő dobozai és hivatkozásai.
