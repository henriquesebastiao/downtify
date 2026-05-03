---
icon: lucide/languages
---

# Internationalization

Downtify's UI is fully translatable. The default language is **English**, with **Spanish** and **Brazilian Portuguese** included out of the box.

## Switching language

Go to **Settings → Language** and pick your preferred language. The choice is saved in the browser's `localStorage` and applied instantly without a page reload.

## Available languages

| Code | Language |
|------|---------|
| `en` | English (default) |
| `es` | Español |
| `pt-BR` | Português (Brasil) |

## Adding a new language

Adding a translation is a three-step process:

### 1. Copy the English locale file

Locale files live in `frontend/src/i18n/locales/`. Each file exports a single object whose keys match the structure of `en.js`. Use an [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) for the file name.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/fr.js
```

### 2. Translate the values

Keep keys, placeholder tokens (e.g. `{count}`, `{name}`, `{file}`) and the overall shape unchanged — only the strings on the right-hand side should change. Set `language.name` to the **native** name of the language (`"Français"`, `"Deutsch"`, …) — this is the label shown in the language picker.

### 3. Register the locale

Add an import and an entry to `AVAILABLE_LOCALES` in `frontend/src/i18n/index.js`:

```js
import fr from './locales/fr.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  { code: 'pt-BR', name: 'Português (BR)', messages: ptBR },
  { code: 'fr', name: 'Français', messages: fr }, // new
]
```

Rebuild the frontend and your language will appear in **Settings → Language** automatically:

```bash
cd frontend && npm run build
```

## Tips for translators

- Missing keys fall back to English, so partial translations work fine — submit a PR with what you have.
- Placeholder tokens like `{count}` or `{file}` must be left unchanged; they are substituted at runtime.
- Keep strings concise — the UI is laid out tightly and very long translations may wrap awkwardly.
- After translating, run `npm run dev` from `frontend/` and navigate every page in your language to spot anything that overflows or reads oddly in context.

Pull requests with new translations are very welcome — open a PR against `main`.
