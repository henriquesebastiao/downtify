# CLAUDE.md

Guidance for Claude Code when working in this repository. Read before editing.

## What Downtify is

Self-hosted Spotify downloader. Resolves track/album/playlist metadata from the public `open.spotify.com/embed` endpoints (no Spotify Premium / Web API key needed), then pulls audio from YouTube via `yt-dlp`, transcodes with `ffmpeg`, and embeds cover art + ID3/Vorbis/MP4 metadata via `mutagen`. Ships a FastAPI backend + Vue 3 SPA, distributed as a Docker image.

Entry point: `main.py` (CLI flag `web` boots the FastAPI app on `DOWNTIFY_PORT`, default `8000`).

## Stack

- **Backend**: Python 3.10–3.15 (Docker image pins 3.15), FastAPI, Uvicorn, `loguru`, `yt-dlp`, `mutagen`, `requests`, `ytmusicapi`.
- **Frontend**: Vue 3 + Vue Router, Tailwind CSS v4 (design tokens in `frontend/src/styles/tokens.css`, shared with the docs site), VueUse, Vite, Vitest.
- **Packaging**: `uv` (lockfile is `uv.lock`; `requirements.txt` is exported for Docker only — do **not** hand-edit).
- **Container**: Alpine + `ffmpeg` + `tini` + `su-exec` (UID/GID/UMASK env-controlled).
- **CI**: GitHub Actions (`build.yml`, `test.yml`, `docs.yml`, `codeflash.yaml`).
- **Docs**: VitePress with a custom Tailwind theme, its own npm package in `docs/` (`make doc`, `make doc-build`).

## Layout

```
main.py                # FastAPI boot, logging, static SPA serving, cover extraction, CLI args
downtify/
  api.py               # FastAPI router (endpoints listed in its module docstring)
  downloader.py        # yt-dlp wrapper, file naming, sanitization
  spotify.py           # open.spotify.com/embed scraping + anonymous-token playlist pagination
  providers.py         # YouTube/yt-music search + match scoring
  lyrics.py            # lrclib lookup, USLT/©lyr/Vorbis embedding, .lrc sidecar
  m3u.py               # M3U/M3U8 playlist generation
  monitor.py           # Playlist watcher (sqlite-backed), incremental sync
  library_visibility.py # What admins hide from non-admin users (songs/albums/artists)
  telemetry.py         # Optional anonymous metrics
frontend/              # Vue SPA (built into frontend/dist, served by FastAPI)
docs/                  # Documentation: Markdown pages + VitePress site (docs/.vitepress)
tests/                 # pytest suite (Python) + Vitest under frontend/ and docs/.vitepress/tests
docker/                # Compose volumes (downloads/, data/, slskd/)
```

## Development workflow

```bash
make run        # uv run python main.py web   (dev backend on :8000)
make test       # frontend + docs Vitest, then pytest -x -s -v
make format     # ruff format + ruff --fix + prettier (frontend/src, docs/.vitepress)
make lint       # ruff check + prettier --check
make export     # regenerate requirements.txt from uv.lock (Docker build input)
make up / down  # docker compose
make doc        # docs dev server (VitePress, hot reload)
make doc-build  # production docs build into docs/.vitepress/dist
```

Frontend dev: `npm --prefix frontend run dev` (Vite). The backend serves `frontend/dist` in production; during dev the SPA proxies API calls.

Version bump: `make version 2.7.1` — runs `version.sh`, rebuilds the frontend, formats. Keep `pyproject.toml`, `downtify/__init__.py`, `frontend/package.json`, `Makefile`, and `Dockerfile` labels in sync (the script handles this).

## Coding standards

- Ruff is the single source of truth. `line-length = 79`, single quotes, `preview = true`, rules `I, F, E, W, PL, PT`. Per-file ignores already exist for `main.py`, `downloader.py`, `downtify/*.py`, and `tests/*.py` — **don't widen them**, fix the code instead.
- Type hints required on public functions and any new code. Use `from __future__ import annotations` (existing convention).
- Logging: use `loguru` (`from loguru import logger`). Stdlib `logging` is intercepted in `main.py:_InterceptHandler` — do not reconfigure it.
- Keep the existing API surface stable. The Vue frontend depends on the exact endpoint shapes documented in `downtify/api.py`'s module docstring. Add new endpoints rather than renaming.
- No new top-level dependencies without a clear need — `yt-dlp`, `mutagen`, `ytmusicapi`, `fastapi`, `loguru` cover the vast majority of cases.

## Domain gotchas (do not rediscover these)

- **Spotify embed schema**: playlist tracks expose `subtitle` (joined artist string), **not** an `artists` list, and have **no per-track cover** — fall back to the playlist cover. See `downtify/spotify.py`.
- **Playlist size cap**: the embed endpoint caps at ~50–100 tracks. Full playlists require the anonymous token + `api.spotify.com` pagination path already implemented in `spotify.py`. Don't replace it with the embed-only path.
- **yt-dlp anti-bot**: defaults use `player_client=tv,mweb` plus cookies / IPv4 env knobs. If YouTube returns "Sign in to confirm" errors, tune these in `downloader.py` rather than switching extractors.
- **Lyrics**: `lrclib` and `netease` are wired end-to-end and tried in the user's order (`lyrics_providers`), with per-song misses cached in `downtify/lyrics_cache.py`. `genius` / `musixmatch` / `azlyrics` are accepted in saved settings but never fetch anything (AZLyrics forbids third-party use, Musixmatch needs credentials, Genius' robots.txt disallows its search endpoint) — do not claim they work in docs.
- **Shared library / hiding**: every account sees every downloaded song; `track_owners` (who downloaded it) now only decides who may delete — never what is listed. Admins hide songs/albums/artists from non-admins with rules in `downtify/library_visibility.py` (a blacklist: nothing hidden = no work per request). `api.allowed_entry_keys` returns `None` for admins and while nothing is hidden, otherwise the content keys *not* hidden; every consumer (`/tracks`, `/list`, album/artist indexes, summary, mobile sync, archive) goes through it, so new listing endpoints must too. Rules match like the Library groups (artist = `album_artist_of`, album = artist + title, casefolded; track = content key *and* path) and follow a rewritten or deleted file via `api.rekey_file_owners` / `drop_file_owners` — call them from any new flow that rewrites or removes a file. Hiding/showing must `library_sync.touch` the rows whose visibility flipped (the apps learn from the feed). It is a listing control, not access control: `/downloads` and streaming by path are not gated.
- **Library upgrade**: `downtify/library_upgrade.py` scans the library and repairs artwork / lyrics / tags in place. It rewrites a verified working copy (`<name>.downtify-upgrade.<ext>`, skipped by the library scan via `library_catalog.UPGRADE_STAGING_MARKER`) and keeps the original mtime. Audio is deliberately never replaced by an upgrade — replacing it is `downtify/audio_replace.py` (the admin picks the version by hand; same path, same format, tags copied over). Don't add automatic replacement without the match-confidence and playlist-rename work the issue describes. Cover sizes come from `downtify/image_size.py` (header parsing, no Pillow) and are cached per file in `library_metadata_cache` (`cover_px`; bump `META_VERSION` when tag-derived columns change, and add the column to **both** the `CREATE TABLE` and `_ADDED_COLUMNS`).
- **Explicit mark**: songs carry `explicit` (Spotify, YouTube Music and Deezer rows all set it); `embed_metadata` writes it as `ITUNESADVISORY=1` (ID3 TXXX / Vorbis) or the MP4 `rtng` atom (`downtify/content_advisory.py`) and `library_metadata.read_explicit` reads it back into the cached `explicit` column. It is only ever **added** — a song that doesn't say never clears an existing mark, which is what keeps the library upgrade and retagging from erasing it — and it describes the audio actually downloaded, so only trust a YouTube Music hit's `isExplicit` when it is the downloaded video. Sync rows carry `explicit` only when true.
- **Tag embedding**: cover art and lyrics must round-trip across MP3 (ID3 APIC/USLT), FLAC (Picture/Vorbis), M4A (`covr`/`©lyr`), Opus/Vorbis. The cover-extraction code in `main.py:_extract_cover` is the canonical reader — mirror its container handling when adding new formats.

## Testing

- Python: `uv run pytest -x -s -v`. Tests live in `tests/` and avoid network where possible — keep new tests offline (fixtures / monkeypatched HTTP).
- Frontend: `npm --prefix frontend test` (Vitest).
- For changes touching `spotify.py`, `providers.py`, `downloader.py`, or `m3u.py`, add or extend the matching `tests/test_*.py`. The `test_spotify_embed.py` / `test_spotify_url.py` suites already cover the embed schema quirks — extend them rather than mocking around them.
- `codeflash` (CI) optimizes hot paths. Don't write code that depends on micro-optimizations Codeflash might rewrite; keep functions pure and small so its rewrites stay safe.

## Documentation

There are two documentation surfaces, with different jobs — don't blur them:

- **`README.md`** — a short overview for someone landing on the GitHub repo for the first time: what Downtify is, quick start, a features table, and brief pointers. Keep sections to a few lines each. When a feature needs more than that (full option tables, edge cases, env var reference, API shapes), the README gets a one-paragraph summary plus a link into `docs/` — the detail itself belongs in `docs/`, not duplicated in both places.
- **`docs/`** (built by VitePress, served by GitHub Pages from the custom domain `downtify.henriquesebastiao.com`, at its root — the `henriquesebastiao.github.io/downtify/` URL only redirects there. See `SITE_URL` and `BASE` in `docs/.vitepress/config.mjs`; keep `BASE` at `/`, since a `/downtify/` prefix points every asset at a 404 and the site renders unstyled) — the complete reference. This is where full option tables, every environment variable, the full API reference (`docs/api-reference.md`), and per-feature deep-dives (`docs/features/*.md`) live. New user-facing features get a page here (add it to `NAV` in `docs/.vitepress/nav.mjs` too, and give it an `icon: lucide/<name>` front matter), not just a README blurb.

Docs site gotchas:

- Page URLs are directory-style (`features/player.md` → `/features/player/`) and heading ids follow Python-Markdown's rules (`GET /api/url/resolve` → `#get-apiurlresolve`, repeats get `_1`) — both kept from the old zensical site because README and issues link to them. Don't change `docs/.vitepress/lib/routes.mjs` or `slug.mjs` without checking existing links.
- Write Markdown links relative to the source file (`[Lyrics](../features/lyrics.md#x)`); the build rewrites them. Callouts use `::: info|tip|warning Title` … `:::`.
- The build fails on dead links **and** broken `#anchors`; run `make doc-build` after editing docs.
- **The docs are translated** (the same languages as the app, plus any added later). English pages in `docs/` are the source; each language mirrors them in `docs/<code>/` with the same file names, and its site text and sidebar titles live in `docs/.vitepress/locales/<code>.mjs` (`en.mjs` is the template). A page without a translation is a stub (`<EnglishOnly />` plus an `@include` of the English page), so every language has every page: a **new page needs `npm run i18n -- stubs`** (in `docs/`) and a title in each locale file's `nav.pages`, and `npm test` fails until it has. Translated pages must keep the English page's headings, code blocks, tables, callouts and link targets (`.vitepress/lib/page-structure.mjs` checks it); their heading ids are copied from the English headings by position, so anchors written against the English ids work everywhere — never hand-write ids. Changing an English page doesn't require touching its translations in the same change (`npm run i18n -- status <code>` lists the stale ones), but don't rename or reorder its headings without saying so, and keep new UI labels in the text identical to the app's `en.js` so translators can look them up. The API reference, mobile client contract and changelog stay English-only (stubs).
- The docs open in the browser's language through a script in every page's `<head>` (`lib/locale-redirect.mjs`), and the language button in the top bar remembers the pick in `localStorage` (`downtify-docs-locale`). Don't turn it into a server redirect: the site is static.
- Pages are Vue templates: a literal `{{` or an unknown `<Tag>` outside code breaks the build.

Cross-check both against the code, not against each other — a stale doc citing another stale doc just launders the error.

## Quality bar before declaring a task done

1. `make lint` clean (no new ruff or prettier diff).
2. `make test` green (both pytest and Vitest).
3. New code paths covered by a test, or a clear note in the PR why not.
4. No new permissive `extend-ignore` / per-file ignore entries.
5. If the change affects download behavior: manually run `make run`, pull one Spotify track + one playlist, confirm metadata, cover art, and (when enabled) lyrics embed correctly. State the manual verification explicitly — type checks do not validate this.
6. If the change affects the SPA: `npm --prefix frontend run build` succeeds and the resulting `frontend/dist` is served correctly by the backend.
7. Docker: if Python deps changed, run `make export` so `requirements.txt` matches `uv.lock` before merging — the Docker build uses `requirements.txt`, not `uv.lock`.
8. **Before calling any task finished**, check whether it changed user-facing behavior (new/changed setting, env var, endpoint, UI control, supported input type, language, limit). If it did, update `README.md` (brief overview + link) and the matching `docs/` page(s) in the same change — see [Documentation](#documentation). If nothing user-facing changed (internal refactor, test-only change, CI config), say so explicitly instead of silently skipping this.
9. Every change is described in `commit-message.md` — this repo's, and `~/git/downtify-android`'s if the task touched the app. See [Server and Android client together](#server-and-android-client-together).
10. The final reply says how to test the change and where it shows in the interface — see [Final reply](#final-reply).

## Final reply

Every task ends with a reply that lets the maintainer check the change by hand, in this order:

- **How to test it.** Concrete steps, not "run the tests": the commands (`make test`, a single `uv run pytest tests/test_x.py -k name`, `make run`, `make doc`, `npm --prefix frontend run dev`), any setup they need (an env var, a setting to turn on, an admin account, a scratch `DOWNLOAD_DIR`), the input to use (a Spotify track/playlist link, an endpoint with an example `curl`), and what they should see when it works. Say which of these you already ran and which are left to them.
- **Where it shows in the interface.** When the web SPA changed, name the page and its route, then the section or control: e.g. "Library → Trash (`/library/trash`), the *Restore* button on each row" or "Settings → Tags & lyrics (`/settings/tags`), the *Providers* list under lyrics". Say who sees it (admins only, only with `DOWNTIFY_TRASH=true`, only while a song plays). For the docs site, give the page path (e.g. `/features/music-trash/`). When the Android app changed too, say where in the app (tab or side menu entry, screen, menu or sheet). If nothing visible changed, say so in one line.
- Then name every repo changed and its `commit-message.md`.

## Server and Android client together

The server lives in `~/git/downtify` (this repo), the Android client in `~/git/downtify-android`. They evolve as one product: when a task here needs a change on the other side — the app has to use a new or changed `/api/v1` endpoint or field, a WebSocket frame, the pairing flow, or it breaks on something this change does — make that change in `~/git/downtify-android` in the same task, without stopping to ask. A session opened in the Android repo may change this one the same way.

- Before editing the other repo, read its `CLAUDE.md` and follow it there (architecture, translations, tests, its own checks: `./gradlew build detekt spotlessCheck` for the app).
- The app reads the contract in `docs/mobile-client-contract.md` and the "Server and sign-in", "Mobile API (v1)" and "WebSocket" parts of `docs/api-reference.md`: change them with the code. Installed apps keep calling the old shape, so add fields and endpoints rather than renaming or removing.
- **Don't commit, stage or push, in either repo.** The maintainer commits by hand.
- **No change goes undescribed.** Every edit to tracked files (code, tests, docs, config) is described in `commit-message.md` at the root of the repo it touched (git-ignored in both). A task that touched both repos leaves a message in each, and each mentions the other side ("Needs the server's …" / "Used by the Android app's …").
- Write it before the final reply, as Conventional Commits: imperative subject ≤ 72 characters, a body saying why, then what changed per file or area.
- The file may hold an older message. If `git log` already has its subject, it was committed: replace it. If it describes changes still uncommitted, keep them: extend the message to cover everything pending, or add a separate message for unrelated work, separated by a `---` line and each naming the files it covers.
- End the reply by naming every repo changed and its `commit-message.md`.

## Things to never do

- Reintroduce `spotdl` / `spotipy` / Spotify Web API credentials. The project deliberately removed that dependency.
- Commit `frontend/dist`, `downloads/`, `data/`, or any `.mp3` / `.m4a` artefacts (`.gitignore` covers these — keep it that way).
- Bypass `ruff` / `prettier` with inline disables to silence a warning. Fix the cause.
- Change the public API endpoint paths or response shapes without simultaneously updating the Vue frontend (and the Android client, when it uses them).
- Commit or push, here or in `~/git/downtify-android` — describe the change in `commit-message.md` instead.
- Add network calls to tests without a recorded fixture.
- Hand-edit `requirements.txt` — regenerate via `make export`.
- Skip hooks (`--no-verify`) on commits.

## Useful entry points when investigating

- Download lifecycle: `downtify/api.py` (`POST /api/download/url`) → `downtify/downloader.py:Downloader` → `downtify/providers.py` (search) → `mutagen` tag write → `downtify/lyrics.py`.
- Playlist sync: `downtify/monitor.py:monitor_loop` + `PlaylistMonitorDB` (sqlite under `/data`).
- WebSocket progress: `downtify/api.py:ConnectionManager` (`WS /api/ws`).
- Static SPA + cover serving: `main.py:build_app`, `main.py:SPAStaticFiles`, `main.py:_extract_cover`.
