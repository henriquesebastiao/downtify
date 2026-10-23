---
icon: lucide/languages
---

# Internationalisierung

Downtify wird an zwei voneinander unabhängigen Stellen übersetzt: der **App** (ihrer Oberfläche) und dieser **Dokumentation**. Die Standardsprache beider ist **Englisch**, mit neun weiteren Sprachen von Haus aus.

## Sprache wechseln

### Die App

Gehe zu **Einstellungen → Sprache** und wähle deine bevorzugte Sprache. Die Wahl wird im `localStorage` des Browsers gespeichert und sofort ohne Neuladen der Seite angewendet. Die Seite teilt sie bei jedem Laden und bei jeder Änderung auch dem Server mit (der Eintrag `ui_language` in `settings.json`, siehe [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), damit Arbeit, die ohne Browser läuft, deine Sprache kennt - die Biografie eines Künstlers, die im Hintergrund abgerufen wird, wenn einer seiner Titel fertig heruntergeladen ist, kommt darin an (siehe [Wenn ein Download fertig ist](artist-images.md#when-a-download-finishes)). Du musst nichts tun: Hast du eine Sprache gewählt, bevor es das gab, wird sie beim nächsten Öffnen von Downtify übernommen. Sind mehrere Browser auf verschiedene Sprachen eingestellt, gewinnt der, der sie zuletzt geladen oder geändert hat.

### Die Dokumentation

Die Dokumentation öffnet sich in der Sprache, die dein Browser bevorzugt, wenn sie dorthin übersetzt ist, und sonst auf Englisch. Die **Globus-Schaltfläche** rechts in der oberen Leiste wechselt die Sprache jederzeit und belässt dich auf derselben Seite (und im selben Abschnitt). Deine Wahl wird im Browser gemerkt und gilt von da an vor der Browsersprache, bis du eine andere wählst.

Eine noch nicht übersetzte Seite zeigt einen Hinweis und den englischen Text, sodass jede Sprache immer jede Seite hat.

## Verfügbare Sprachen

| Code | Sprache | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en` | English (Standard) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

Die für Entwickler gedachten Referenzseiten — die [API-Referenz](../api-reference.md), der [Vertrag für mobile Clients](../mobile-client-contract.md) und das Changelog — bleiben in jeder Sprache auf Englisch.

## Eine Übersetzung beisteuern

Du kannst die App, die Dokumentation oder beides übersetzen. Das sind getrennte Arbeiten mit getrennten Dateien, sodass ein Pull Request eines von beiden enthalten kann — oder eine Sprache zuerst zu einem von beiden und später zum anderen hinzugefügt wird.

| Du übersetzt | Wo die Dateien liegen | Fertig, wenn |
| ------------- | ------------------- | --------- |
| **Nur die App** | `frontend/src/i18n/locales/<code>.js` | die Sprache unter **Einstellungen → Sprache** erscheint |
| **Nur die Dokumentation** | `docs/.vitepress/locales/<code>.mjs` und die Markdown-Seiten in `docs/<code>/` | die Sprache im Globus-Menü der Dokumentation erscheint |
| **Beides** | alles oben Genannte | beides |

Eine Sprache muss nicht in der App existieren, um zur Dokumentation hinzugefügt zu werden, und umgekehrt.

## Die App übersetzen

Eine Übersetzung zur App hinzuzufügen, geht in drei Schritten:

### 1. Die englische Sprachdatei kopieren

Sprachdateien liegen in `frontend/src/i18n/locales/`. Jede Datei exportiert ein einzelnes Objekt, dessen Schlüssel der Struktur von `en.js` entsprechen. Nutze ein [IETF-Sprachkürzel](https://en.wikipedia.org/wiki/IETF_language_tag) als Dateinamen.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Die Werte übersetzen

Lass Schlüssel, Platzhalter-Token (z. B. `{count}`, `{name}`, `{file}`) und die Gesamtform unverändert — nur die Zeichenketten auf der rechten Seite sollen sich ändern. Setze `language.name` auf den **nativen** Namen der Sprache (`"Français"`, `"Deutsch"`, …) — das ist die Beschriftung in der Sprachauswahl.

### 3. Die Sprache registrieren

Füge einen Import und einen Eintrag zu `AVAILABLE_LOCALES` in `frontend/src/i18n/index.js` hinzu:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Baue das Frontend neu, und deine Sprache erscheint automatisch unter **Einstellungen → Sprache**:

```bash
cd frontend && npm run build
```

### Tipps zum Übersetzen der App

- Fehlende Schlüssel fallen auf Englisch zurück, Teilübersetzungen funktionieren also gut — reiche einen PR mit dem ein, was du hast.
- Zeichenketten, die von einer Zahl abhängen, sind Objekte mit Pluralformen, z. B. `tracks: { one: '{count} track', other: '{count} tracks' }`. Die Form wird mit dem [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) des Browsers für deine Sprache gewählt, also füge die Formen hinzu, die deine Sprache nutzt (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` ist Pflicht. Zahlen werden automatisch für die Sprache formatiert.
- Platzhalter-Token wie `{count}` oder `{file}` müssen unverändert bleiben; sie werden zur Laufzeit ersetzt.
- Halte Zeichenketten knapp — die Oberfläche ist eng gesetzt, und sehr lange Übersetzungen können unschön umbrechen.
- Führe nach dem Übersetzen `npm run dev` in `frontend/` aus und gehe jede Seite in deiner Sprache durch, um zu sehen, was überläuft oder im Kontext seltsam klingt.

## Die Dokumentation übersetzen

Englisch ist die Quelle: Sie liegt in `docs/`. Jede andere Sprache hat einen nach ihrem Kürzel benannten Ordner (`docs/pt-BR/`) mit **denselben Dateinamen** wie Englisch, plus eine Datei für die eigenen Texte der Seite (`docs/.vitepress/locales/pt-BR.mjs`: die Titel der Seitenleiste, das Suchfeld, die Fußzeile, die Beschriftungen der Hinweisboxen). Eine noch nicht übersetzte Seite ist ein kleiner Platzhalter, der einen Hinweis zeigt und die englische Seite einbindet.

### Eine Seite einer bestehenden Sprache übersetzen

Aus `docs/`:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start` ersetzt den Platzhalter `docs/pt-BR/features/users.md` durch eine Kopie der englischen Seite. Übersetze sie an Ort und Stelle und prüfe sie dann:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Eröffne einen Pull Request, wenn die Seite gut zu lesen ist; Teilarbeit ist ebenfalls willkommen — Seiten, die du nicht angefasst hast, bleiben einfach Englisch.

### Eine Sprache zur Dokumentation hinzufügen

1. Kopiere `docs/.vitepress/locales/en.mjs` nach `docs/.vitepress/locales/<code>.mjs` und übersetze es: den nativen `name`, die Texte der Seite (`ui`), die Beschriftungen der Hinweisboxen (`containers`) und die Titel der Seitenleiste (`nav`).
2. Registriere sie in `docs/.vitepress/locales/index.mjs`.
3. Lege die Seiten als nur englische Platzhalter an: `npm run i18n -- stubs <code>`.
4. Übersetze die Seiten nacheinander mit `npm run i18n -- start <code> <page>`.

Die Sprache erscheint im Globus-Menü und in der Erkennung der Browsersprache, sobald sie registriert ist.

### Was zu behalten und was zu übersetzen ist

- **Übersetze** den Text, die Überschriften, die Tabellenzellen, die Titel der Hinweisboxen und die `title`-/`text`-Werte im Front Matter der Startseite.
- **Behalte unverändert** Codeblöcke, Inline-`code`, URLs, Umgebungsvariablen, API-Pfade und Feldnamen, Datei- und Ordnernamen sowie die Front-Matter-Schlüssel und die Werte von `icon:` und `link:`. Einen Kommentar in einem Codeblock zu übersetzen ist in Ordnung.
- **Links**: Behalte die relativen `.md`-Links der englischen Seite (`[Songtexte](lyrics.md#sidecar-lrc-file)`) genau bei. Ein Link auf eine nur englische Seite funktioniert weiterhin. Auf der Startseite werden Links mit dem Sprachpräfix geschrieben (`/pt-BR/features/player/`).
- **Überschriften**: Behalte dieselben Überschriften in derselben Reihenfolge und auf denselben Ebenen. Links auf einen Abschnitt (`#sidecar-lrc-file`) funktionieren in jeder Sprache weiter, weil die übersetzte Seite die englischen Überschrift-IDs wiederverwendet — du schreibst oder übersetzt nie eine ID.
- **Namen von Schaltflächen und Einstellungen**: Die App hat eine eigene Übersetzung jeder Beschriftung. Nutze sie, in Fettschrift, damit die Seite zu dem passt, was der Leser auf dem Bildschirm sieht: Suche die Beschriftung in `frontend/src/i18n/locales/<code>.js`. Ist die App in dieser Sprache noch nicht übersetzt, behalte die englische Beschriftung.
- **Hinweisboxen** (`::: tip Titel`): Behalte die Art (`info`, `tip`, `warning`, `danger`) und übersetze den Titel. Eine Hinweisbox ohne Titel trägt als Beschriftung das Wort aus `containers` in der Sprachdatei.
- **Ton**: Schreibe für den Leser dieser Sprache — die Seiten sind Anleitungen, keine Wort-für-Wort-Wiedergaben.

### Übersetzungen aktuell halten

Wenn sich eine englische Seite ändert, müssen sich ihre Übersetzungen nicht im selben Pull Request ändern: Eine übersetzte Seite funktioniert weiter, und `npm run i18n -- status <code>` listet die Seiten auf, deren englische Quelle sich nach der Übersetzung geändert hat. Sie zu aktualisieren ist ein guter erster Beitrag.

Die Tests (`npm test` in `docs/`) prüfen, dass jede Sprache jede Seite und jeden Seitentext hat und dass eine übersetzte Seite noch die Überschriften, Codeblöcke, Tabellen, Hinweisboxen und Links der englischen Seite besitzt.
