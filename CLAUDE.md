# CLAUDE.md

Guidance for Claude Code when working in this repository. Read before editing.

## What Downtify is

Self-hosted Spotify downloader. Resolves track/album/playlist metadata from the public `open.spotify.com/embed` endpoints (no Spotify Premium / Web API key needed), then pulls audio from YouTube via `yt-dlp`, transcodes with `ffmpeg`, and embeds cover art + ID3/Vorbis/MP4 metadata via `mutagen`. Ships a FastAPI backend + Vue 3 SPA, distributed as a Docker image.

Entry point: `main.py` (CLI flag `web` boots the FastAPI app on `DOWNTIFY_PORT`, default `8000`).

## Stack

- **Backend**: Python 3.10–3.13 (Docker image pins 3.13), FastAPI, Uvicorn, `loguru`, `yt-dlp`, `mutagen`, `requests`, `ytmusicapi`.
- **Frontend**: Vue 3 + Vue Router, Tailwind + daisyUI, Vite, Vitest.
- **Packaging**: `uv` (lockfile is `uv.lock`; `requirements.txt` is exported for Docker only — do **not** hand-edit).
- **Container**: Alpine + `ffmpeg` + `tini` + `su-exec` (UID/GID/UMASK env-controlled).
- **CI**: GitHub Actions (`build.yml`, `test.yml`, `docs.yml`, `codeflash.yaml`).
- **Docs**: `zensical` (`make doc`).

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
  telemetry.py         # Optional anonymous metrics
frontend/              # Vue SPA (built into frontend/dist, served by FastAPI)
tests/                 # pytest suite (Python) + Vitest under frontend/
docker/                # Compose volumes (downloads/, data/, slskd/)
```

## Development workflow

```bash
make run        # uv run python main.py web   (dev backend on :8000)
make test       # frontend Vitest + pytest -x -s -v
make format     # ruff format + ruff --fix + prettier
make lint       # ruff check + prettier --check
make export     # regenerate requirements.txt from uv.lock (Docker build input)
make up / down  # docker compose
make doc        # zensical serve (docs preview)
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
- **Lyrics**: only `lrclib` is wired end-to-end. `genius` / `musixmatch` / `azlyrics` exist as UI stubs — do not claim they work in docs.
- **Tag embedding**: cover art and lyrics must round-trip across MP3 (ID3 APIC/USLT), FLAC (Picture/Vorbis), M4A (`covr`/`©lyr`), Opus/Vorbis. The cover-extraction code in `main.py:_extract_cover` is the canonical reader — mirror its container handling when adding new formats.

## Testing

- Python: `uv run pytest -x -s -v`. Tests live in `tests/` and avoid network where possible — keep new tests offline (fixtures / monkeypatched HTTP).
- Frontend: `npm --prefix frontend test` (Vitest).
- For changes touching `spotify.py`, `providers.py`, `downloader.py`, or `m3u.py`, add or extend the matching `tests/test_*.py`. The `test_spotify_embed.py` / `test_spotify_url.py` suites already cover the embed schema quirks — extend them rather than mocking around them.
- `codeflash` (CI) optimizes hot paths. Don't write code that depends on micro-optimizations Codeflash might rewrite; keep functions pure and small so its rewrites stay safe.

## Quality bar before declaring a task done

1. `make lint` clean (no new ruff or prettier diff).
2. `make test` green (both pytest and Vitest).
3. New code paths covered by a test, or a clear note in the PR why not.
4. No new permissive `extend-ignore` / per-file ignore entries.
5. If the change affects download behavior: manually run `make run`, pull one Spotify track + one playlist, confirm metadata, cover art, and (when enabled) lyrics embed correctly. State the manual verification explicitly — type checks do not validate this.
6. If the change affects the SPA: `npm --prefix frontend run build` succeeds and the resulting `frontend/dist` is served correctly by the backend.
7. Docker: if Python deps changed, run `make export` so `requirements.txt` matches `uv.lock` before merging — the Docker build uses `requirements.txt`, not `uv.lock`.

## Things to never do

- Reintroduce `spotdl` / `spotipy` / Spotify Web API credentials. The project deliberately removed that dependency.
- Commit `frontend/dist`, `downloads/`, `data/`, or any `.mp3` / `.m4a` artefacts (`.gitignore` covers these — keep it that way).
- Bypass `ruff` / `prettier` with inline disables to silence a warning. Fix the cause.
- Change the public API endpoint paths or response shapes without simultaneously updating the Vue frontend.
- Add network calls to tests without a recorded fixture.
- Hand-edit `requirements.txt` — regenerate via `make export`.
- Skip hooks (`--no-verify`) on commits.

## Useful entry points when investigating

- Download lifecycle: `downtify/api.py` (`POST /api/download/url`) → `downtify/downloader.py:Downloader` → `downtify/providers.py` (search) → `mutagen` tag write → `downtify/lyrics.py`.
- Playlist sync: `downtify/monitor.py:monitor_loop` + `PlaylistMonitorDB` (sqlite under `/data`).
- WebSocket progress: `downtify/api.py:ConnectionManager` (`WS /api/ws`).
- Static SPA + cover serving: `main.py:build_app`, `main.py:SPAStaticFiles`, `main.py:_extract_cover`.
