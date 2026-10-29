---
icon: lucide/languages
---

# Internationalization

Downtify is translated in two independent places: the **app** (its interface) and this **documentation**. The default language of both is **English**, with nine other languages included out of the box.

## Switching language

### The app

Go to **Settings → Language** and pick your preferred language. The choice is saved in the browser's `localStorage` and applied instantly without a page reload. The page also tells the server (the `ui_language` entry of `settings.json`, see [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), on every load and whenever you change it, so work that runs without a browser knows your language - an artist's bio, fetched in the background when one of their tracks finishes downloading, comes in it (see [When a download finishes](artist-images.md#when-a-download-finishes)). Nothing to do on your side: if you chose a language before this existed, it is picked up the next time you open Downtify. With several browsers set to different languages, the last one that loaded or changed it wins.

### The documentation

The documentation opens in the language your browser prefers, when it is translated into it, and in English otherwise. The **globe button** at the right of the top bar switches language at any time and keeps you on the same page (and section). Your pick is remembered in the browser, and from then on wins over the browser's language until you pick another one.

A page that has not been translated yet shows a note and the English text, so every language always has every page.

## Available languages

| Code    | Language           | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en`    | English (default)  | ✓   | ✓    |
| `es`    | Español            | ✓   | ✓    |
| `pt-BR` | Português (Brasil) | ✓   | ✓    |
| `fr`    | Français           | ✓   | ✓    |
| `tr`    | Türkçe             | ✓   | ✓    |
| `el`    | Ελληνικά           | ✓   | ✓    |
| `hu`    | Magyar             | ✓   | ✓    |
| `bg`    | Български          | ✓   | ✓    |
| `de`    | Deutsch            | ✓   | ✓    |
| `ko`    | 한국어             | ✓   | ✓    |

The reference pages meant for developers — the [API reference](../api-reference.md), the [mobile client contract](../mobile-client-contract.md) and the changelog — stay in English in every language.

## Contributing a translation

You can translate the app, the documentation, or both. They are separate pieces of work with separate files, so a pull request can contain either one — or a language can be added to one of them first and to the other later.

| You translate | Where the files are | Done when |
| ------------- | ------------------- | --------- |
| **The app only** | `frontend/src/i18n/locales/<code>.js` | the language appears in **Settings → Language** |
| **The documentation only** | `docs/.vitepress/locales/<code>.mjs` and the Markdown pages in `docs/<code>/` | the language appears in the docs' globe menu |
| **Both** | all of the above | both |

A language doesn't have to exist in the app to be added to the documentation, or the other way round.

## Translating the app

Adding a translation to the app is a three-step process:

### 1. Copy the English locale file

Locale files live in `frontend/src/i18n/locales/`. Each file exports a single object whose keys match the structure of `en.js`. Use an [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) for the file name.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Translate the values

Keep keys, placeholder tokens (e.g. `{count}`, `{name}`, `{file}`) and the overall shape unchanged — only the strings on the right-hand side should change. Set `language.name` to the **native** name of the language (`"Français"`, `"Deutsch"`, …) — this is the label shown in the language picker.

### 3. Register the locale

Add an import and an entry to `AVAILABLE_LOCALES` in `frontend/src/i18n/index.js`:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Rebuild the frontend and your language will appear in **Settings → Language** automatically:

```bash
cd frontend && npm run build
```

### Tips for translating the app

- Missing keys fall back to English, so partial translations work fine — submit a PR with what you have.
- Strings that depend on a number are objects with plural forms, e.g. `tracks: { one: '{count} track', other: '{count} tracks' }`. The form is chosen with the browser's [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) for your language, so add the forms your language uses (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` is required. Numbers are formatted for the language automatically.
- Placeholder tokens like `{count}` or `{file}` must be left unchanged; they are substituted at runtime.
- Keep strings concise — the UI is laid out tightly and very long translations may wrap awkwardly.
- After translating, run `npm run dev` from `frontend/` and navigate every page in your language to spot anything that overflows or reads oddly in context.

## Translating the documentation

English is the source: it lives in `docs/`. Every other language has a folder named after its code (`docs/pt-BR/`) with **the same file names** as English, plus one file for the site's own text (`docs/.vitepress/locales/pt-BR.mjs`: the sidebar titles, the search box, the footer, the labels of callouts). A page that is not translated yet is a small stub that shows a note and includes the English page.

### Translating a page of an existing language

From `docs/`:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start` replaces the stub `docs/pt-BR/features/users.md` with a copy of the English page. Translate it in place, then check it:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Open a pull request when the page reads well; partial work is welcome too — pages you haven't touched simply stay in English.

### Adding a language to the documentation

1. Copy `docs/.vitepress/locales/en.mjs` to `docs/.vitepress/locales/<code>.mjs` and translate it: the native `name`, the site's text (`ui`), the callout labels (`containers`) and the sidebar titles (`nav`).
2. Register it in `docs/.vitepress/locales/index.mjs`.
3. Create the pages, as English-only stubs: `npm run i18n -- stubs <code>`.
4. Translate pages one at a time with `npm run i18n -- start <code> <page>`.

The language shows up in the globe menu and in the browser-language detection as soon as it is registered.

### What to keep, and what to translate

- **Translate** the text, the headings, the table cells, the callout titles and the `title`/`text` values in the front matter of the home page.
- **Keep as they are** code blocks, inline `code`, URLs, environment variables, API paths and field names, file and folder names, and the front matter keys, `icon:` and `link:` values. Translating a comment inside a code block is fine.
- **Links**: keep the relative `.md` links of the English page (`[Lyrics](lyrics.md#sidecar-lrc-file)`) exactly. A link to a page that is only in English still works. On the home page, links are written with the language prefix (`/pt-BR/features/player/`).
- **Headings**: keep the same headings, in the same order and at the same levels. Links to a section (`#sidecar-lrc-file`) keep working in every language because the translated page reuses the English heading ids — you never write or translate an id.
- **Names of buttons and settings**: the app has its own translation of every label. Use it, in bold, so the page matches what the reader sees on screen: look the label up in `frontend/src/i18n/locales/<code>.js`. If the app isn't translated into that language yet, keep the English label.
- **Callouts** (`::: tip Title`): keep the kind (`info`, `tip`, `warning`, `danger`) and translate the title. A callout without a title is labelled with the word from `containers` in the locale file.
- **Tone**: write for the reader of that language — the pages are guides, not word-for-word renderings.

### Keeping translations up to date

When an English page changes, its translations don't have to change in the same pull request: a translated page keeps working, and `npm run i18n -- status <code>` lists the pages whose English source changed after they were translated. Updating them is a good first contribution.

The tests (`npm test` in `docs/`) check that every language has every page and every piece of site text, and that a translated page still has the English page's headings, code blocks, tables, callouts and links.
