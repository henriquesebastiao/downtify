---
icon: lucide/hand-heart
---

# Contribuer

Les contributions sont les bienvenues — rapports de bugs, demandes de fonctionnalités, code et traductions aident tous. Les traductions peuvent concerner l’application, cette documentation, ou les deux : voir [Traduire](#translating).

## Issues et demandes de fonctionnalités

Utilisez le [suivi d’issues GitHub](https://github.com/henriquesebastiao/downtify/issues). Avant d’ouvrir une nouvelle issue, cherchez parmi les existantes pour éviter les doublons.

Pour les rapports de bugs, indiquez :

- La version de Downtify
- Comment vous l’avez installé (Docker run, Docker Compose, Umbrel, …)
- Les étapes pour reproduire
- Ce que vous attendiez et ce qui s’est passé
- Tout journal pertinent

## Environnement de développement

### Prérequis

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets Python)
- ffmpeg (doit être dans le `PATH`)

### Cloner et installer

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Lancer en mode développement

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Le serveur de développement du frontend redirige les requêtes d’API vers le backend ; il suffit donc d’ouvrir l’URL de Vite (généralement `http://localhost:5173`).

### Lancer les tests

```bash
uv run pytest
```

### Compiler le frontend pour la production

```bash
cd frontend && npm run build
```

Les fichiers compilés atterrissent dans `frontend/dist/` et sont servis par le backend.

### Travailler sur la documentation

La documentation est composée de fichiers Markdown dans `docs/`, transformés en site statique avec [VitePress](https://vitepress.dev/) et un thème personnalisé (dans `docs/.vitepress/`) qui partage ses jetons de design avec l’application web.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Liez les autres pages avec des chemins `.md` relatifs (`[Paroles](lyrics.md)`) et utilisez `::: tip Titre` … `:::` pour les encadrés (`info`, `tip`, `warning`, `danger`). Les nouvelles pages vont dans la barre latérale dans `docs/.vitepress/nav.mjs` (avec leur titre dans le fichier de chaque langue dans `docs/.vitepress/locales/`). La compilation échoue sur les liens morts et sur les liens vers des titres qui n’existent pas.

Les pages en anglais de `docs/` sont la source ; chaque autre langue les reflète dans un dossier à elle (`docs/pt-BR/…`). Vous n’avez pas à mettre à jour les traductions en modifiant une page anglaise — les traducteurs suivent —, mais lancez `npm test` dans `docs/` : une nouvelle page a besoin d’une ébauche en anglais seulement dans chaque langue (`npm run i18n -- stubs`), et les tests le signalent si elle manque.

## Structure du projet

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Traduire

Downtify a deux choses à traduire, et vous pouvez prendre l’une — ou les deux :

| Vous traduisez | Où | Guide |
|---------------|-------|-------|
| **L’application** (son interface) | `frontend/src/i18n/locales/<code>.js` | [Traduire l’application](features/internationalization.md#translating-the-app) |
| **La documentation** (ces pages) | `docs/<code>/` et `docs/.vitepress/locales/<code>.mjs` | [Traduire la documentation](features/internationalization.md#translating-the-documentation) |

Elles sont indépendantes : une langue peut être dans l’une et pas encore dans l’autre, et une pull request peut ne contenir que la traduction de l’application, que la documentation, ou les deux. Le travail partiel est bienvenu — les textes non traduits retombent sur l’anglais dans l’application, et les pages non traduites restent en anglais dans la documentation.

Démarrage rapide pour la documentation, depuis `docs/` :

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Voir [Internationalisation](features/internationalization.md) pour les détails : ce qu’il faut garder tel quel, comment ajouter une langue entière et comment traduire les noms de boutons pour qu’ils correspondent à ceux de l’application.

## Pull requests

- Faites un fork du dépôt et créez une branche à partir de `main`
- Gardez les changements ciblés — une fonctionnalité ou un correctif par PR
- Ajoutez ou mettez à jour des tests en touchant à la logique du backend
- Lancez `uv run pytest` avant de soumettre
- Ouvrez la PR vers `main`

Si Downtify vous a été utile, pensez à laisser une étoile sur GitHub — cela aide le projet à grandir.
