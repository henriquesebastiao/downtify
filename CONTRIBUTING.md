# Contributing to Downtify

Thanks for your interest in improving Downtify! This document describes how to set up the project locally, the coding and formatting standards every contribution must follow, and the workflow for submitting changes.

By submitting a pull request you agree that your contribution is licensed under the project's [GPL-3.0](./LICENSE) license.

---

## Table of contents

1. [Code of conduct](#code-of-conduct)
2. [Ways to contribute](#ways-to-contribute)
3. [Project overview](#project-overview)
4. [Prerequisites](#prerequisites)
5. [Local setup](#local-setup)
6. [Running the app](#running-the-app)
7. [Coding standards](#coding-standards)
8. [Formatting and linting](#formatting-and-linting)
9. [Testing](#testing)
10. [Commits](#commits)
11. [Pull requests](#pull-requests)
12. [Branching and releases](#branching-and-releases)
13. [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)
14. [Translations](#translations)
15. [Security issues](#security-issues)

---

## Code of conduct

Be respectful, constructive, and patient. Reviews focus on code, not on the contributor. Harassment, personal attacks, or discriminatory language are not tolerated in issues, PRs, discussions, or commit messages.

---

## Ways to contribute

- Fixing a bug from the [issues page](https://github.com/henriquesebastiao/downtify/issues).
- Adding a feature that has been discussed and accepted in an issue or discussion.
- Improving documentation (`README.md`, in-repo docs, or the `zensical` site under `docs/`).
- Adding or improving tests, especially around the Spotify embed scraping, yt-dlp pipeline, and tag embedding.
- Adding a UI translation (see [Translations](#translations)).
- Reviewing open pull requests.

For non-trivial changes, **open an issue first** to align on scope before writing code. This avoids wasted work if the change conflicts with the project's direction.

---

## Project overview

Downtify is a self-hosted Spotify downloader. It resolves track/album/playlist metadata from the public `open.spotify.com/embed` endpoints (no Spotify Premium / Web API key required), pulls audio from YouTube via `yt-dlp`, transcodes with `ffmpeg`, and embeds cover art plus ID3 / Vorbis / MP4 metadata via `mutagen`. The backend is FastAPI, the frontend is a Vue 3 SPA, and everything ships as a Docker image.

Repository layout:

```
main.py                # FastAPI boot, logging, CLI args, static SPA serving
downtify/
  api.py               # FastAPI router
  downloader.py        # yt-dlp wrapper, file naming, sanitization
  spotify.py           # open.spotify.com/embed scraping + playlist pagination
  providers.py         # YouTube / yt-music search and match scoring
  lyrics.py            # lrclib lookup + tag embedding + .lrc sidecar
  m3u.py               # M3U / M3U8 playlist generation
  monitor.py           # Playlist watcher (sqlite-backed)
  telemetry.py         # Optional anonymous metrics
frontend/              # Vue 3 + Vite SPA (built into frontend/dist)
tests/                 # pytest suite (Python) + Vitest under frontend/
docker/                # Compose volumes
```

See [`CLAUDE.md`](./CLAUDE.md) for the deeper architectural notes and known domain gotchas (Spotify embed schema quirks, yt-dlp anti-bot knobs, tag round-tripping across container formats, etc.).

---

## Prerequisites

You need the following installed locally:

| Tool                | Minimum version | Purpose                                       |
| ------------------- | --------------- | --------------------------------------------- |
| Python              | 3.10 (3.13 rec) | Backend runtime (Docker pins 3.13)            |
| [`uv`][uv]          | recent          | Python project + dependency manager           |
| Node.js             | 20.x +          | Frontend build (Vue 3 + Vite)                 |
| npm                 | 10.x +          | Frontend package manager                      |
| `ffmpeg`            | recent          | Audio transcoding (required at runtime)       |
| `git`               | recent          | Version control                               |
| Docker + Compose    | optional        | Only needed if you work on the container side |

[uv]: https://docs.astral.sh/uv/

The Python version is pinned in `.python-version`. `uv` will pick it up automatically.

---

## Local setup

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/downtify.git
cd downtify

# 2. Add the upstream remote so you can keep your fork up to date
git remote add upstream https://github.com/henriquesebastiao/downtify.git

# 3. Install Python dependencies (creates .venv via uv)
uv sync

# 4. Install frontend dependencies
npm --prefix frontend install

# 5. Copy the example environment file
cp .env.example .env
```

Edit `.env` to point `DOWNLOAD_DIR` at a directory you actually have on disk if you don't want downloads to land in `/downloads`.

---

## Running the app

### Backend (development)

```bash
make run
# equivalent to: uv run python main.py web
```

This starts FastAPI + Uvicorn on `DOWNTIFY_PORT` (default `8000`). In production the backend serves `frontend/dist`. During development you typically want the Vite dev server side-by-side:

### Frontend (development)

```bash
npm --prefix frontend run dev
```

Vite hot-reloads the SPA and proxies API calls to the backend.

### Docker

```bash
make up      # docker compose up --build -d
make down    # docker compose down
```

The Docker image is Alpine-based with `ffmpeg`, `tini`, and `su-exec`. UID / GID / UMASK are env-controlled — check `Dockerfile` and `entrypoint.sh`.

### Docs site

```bash
make doc     # uv run zensical serve
```

---

## Coding standards

**All contributions must follow the project's coding and formatting standards. PRs that do not pass lint or format checks will not be merged.**

### Python

- **Ruff is the single source of truth** for style and lint. Configuration lives in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.
  - `line-length = 79`
  - `quote-style = 'single'`
  - `preview = true`
  - Lint rule sets: `I, F, E, W, PL, PT`
- **Type hints are required** on all public functions and on any new code. Use `from __future__ import annotations` (existing convention across the repo).
- **Logging** uses `loguru` (`from loguru import logger`). Stdlib `logging` is intercepted in `main.py:_InterceptHandler` — do not reconfigure it.
- **Do not widen per-file `extend-ignore` rules** in `pyproject.toml` to silence lint warnings. Fix the code instead.
- **Do not bypass formatting** with inline `# ruff: noqa` / `# noqa` directives unless there is a documented, justified reason in a comment on the same line.
- Keep functions small, pure where possible, and free of premature abstraction. Three similar lines are better than a speculative helper.

### API stability

The Vue frontend depends on the exact endpoint paths and response shapes documented in `downtify/api.py`'s module docstring. **Do not rename or change existing endpoints in a breaking way.** Add new endpoints instead, and update the frontend in the same PR.

### Frontend (Vue / JS)

- Formatting handled by **Prettier**. Config is in `.prettierrc.js`. Run `make format` before committing.
- Tailwind + daisyUI are already wired. Prefer composing existing utility classes over adding new global CSS.
- Keep components small and colocate their state. New routes go through `vue-router`.
- All user-facing strings must live in the i18n locale files (`frontend/src/i18n/locales/`). Never hard-code English strings into components.

### Dependencies

- **Do not add a new top-level dependency without justification.** The existing dependencies (`fastapi`, `yt-dlp`, `mutagen`, `ytmusicapi`, `loguru`, `requests`) cover almost every use case. Open an issue if you believe a new dependency is genuinely needed.
- Python dependencies are managed via `uv`. Edit `pyproject.toml`, then run:

  ```bash
  uv lock
  make export      # regenerates requirements.txt from uv.lock
  ```

  `requirements.txt` is **generated**, not hand-edited — the Docker build consumes it.

- Frontend dependencies are managed via `npm`. Always commit the updated `package-lock.json`.

### Things to never do

- Reintroduce `spotdl` / `spotipy` / Spotify Web API credentials. They were intentionally removed.
- Commit `frontend/dist`, `downloads/`, `data/`, or any `.mp3` / `.m4a` artefacts. `.gitignore` covers these — keep it that way.
- Hand-edit `requirements.txt`. Regenerate it via `make export`.
- Skip git hooks with `--no-verify`.
- Add network calls to tests without recorded fixtures.

---

## Formatting and linting

Run these before pushing. CI runs the same checks and will fail the PR if they don't pass.

```bash
make format    # ruff format + ruff --fix + prettier --write
make lint      # ruff check + prettier --check
```

Behind the scenes:

```bash
uv run ruff format .
uv run ruff check . --fix
prettier --write frontend/src/.
```

If `make lint` fails, run `make format` and re-run `make lint`. Commit the formatting changes in the same commit as the code change, never as a separate "format" commit.

---

## Testing

Both test suites must pass before submitting a PR.

```bash
make test
```

This runs:

```bash
npm run test --prefix frontend     # Vitest (frontend)
uv run pytest -x -s -v             # pytest (backend)
```

Guidelines:

- **Add or extend tests** for any change to `spotify.py`, `providers.py`, `downloader.py`, `m3u.py`, `lyrics.py`, or `monitor.py`. The existing `tests/test_spotify_embed.py` and `tests/test_spotify_url.py` files cover the embed schema quirks — extend them rather than mocking around them.
- **Tests must run offline.** Use fixtures or `monkeypatch` to stub HTTP. Do not hit `open.spotify.com`, `api.spotify.com`, YouTube, or `lrclib` from a test.
- Keep tests focused: one behavior per test, descriptive names, no shared mutable state.
- If you cannot test a code path because it depends on a real download, say so explicitly in the PR description and describe the manual verification you performed.

---

## Commits

- One logical change per commit. Rebase / squash noisy "fix lint", "wip", "typo" commits before opening the PR.
- Write commit messages in the imperative mood: "Add playlist pagination", not "Added" or "Adds".
- Subject line ≤ 72 characters. Add a body when the *why* is non-obvious.
- Reference issues with `Fixes #123` / `Closes #123` in the body when applicable.
- **Do not** use `--no-verify` to skip hooks. If a hook fails, investigate and fix the underlying issue.
- **Do not** force-push to `main` under any circumstances. Force-pushing your own PR branch is fine when rebasing on `upstream/main`.

---

## Pull requests

Before opening a PR:

1. Rebase your branch on the latest `upstream/main`.
2. `make format` clean — no diff after running.
3. `make lint` passes.
4. `make test` passes (both pytest and Vitest).
5. New behavior is covered by a test, or the PR description explains why not.
6. If the change touches download behavior, manually run `make run`, pull one Spotify track and one playlist, and confirm metadata + cover art + lyrics embed correctly. State this verification explicitly in the PR description.
7. If the change affects the SPA, run `npm --prefix frontend run build` and confirm the resulting `frontend/dist` is served correctly by the backend.
8. If Python dependencies changed, `make export` was run and the updated `requirements.txt` is committed.
9. If the change is user-facing, the README / docs are updated in the same PR.

PR description should include:

- **What** changed and **why**.
- Link to the issue it fixes / closes, if any.
- Screenshots or short clips for UI changes.
- A test plan: what you ran, what you verified manually.
- Any follow-up work intentionally left out of this PR.

Reviews are an exchange. Expect to iterate. Keep responses to review comments focused on the code, and resolve threads only after the reviewer has agreed the change is good.

---

## Branching and releases

- All work targets the `main` branch via PR. There is no long-lived develop branch.
- Release versioning follows [Semantic Versioning](https://semver.org/). Versions live in `pyproject.toml`, `downtify/__init__.py`, `frontend/package.json`, `Makefile`, and the `Dockerfile` labels — keep them in sync.
- Maintainers bump the version with `make version X.Y.Z`, which runs `version.sh`, rebuilds the frontend, and re-formats the tree. Contributors should **not** bump the version in their PRs.
- The changelog is generated with `make changelog` (uses `github_changelog_generator`).

---

## Reporting bugs and requesting features

- Use the [issues page](https://github.com/henriquesebastiao/downtify/issues) and pick the appropriate template.
- For bugs, include: Downtify version, deployment method (Docker vs. local), OS, exact reproduction steps, expected vs. actual behavior, and relevant log output. If a specific Spotify URL triggers the bug, include it — the project deliberately uses only public endpoints, so the URL is not sensitive.
- For feature requests, describe the problem first, then the proposed solution. Features that require Spotify Premium credentials or the Spotify Web API will not be accepted.

---

## Translations

Adding a UI translation is a small, three-step change documented in the [README](./README.md#contributing-translations). In short:

1. Copy `frontend/src/i18n/locales/en.js` to a new file named after the [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) (`fr.js`, `de.js`, `ja.js`, …).
2. Translate the values; leave keys and placeholder tokens (`{count}`, `{file}`, …) unchanged.
3. Register the locale in `frontend/src/i18n/index.js`.

Missing keys fall back to English, so partial translations are welcome.

---

## Security issues

**Do not open a public GitHub issue for security vulnerabilities.** Email the maintainer privately at **contato@henriquesebastiao.com** with a description of the issue and a reproduction. You will receive an acknowledgement within a reasonable time, and a fix coordinated before public disclosure.

---

Thanks for contributing! ⭐ Stars and good PRs both keep the project alive.
