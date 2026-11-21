---
name: release-highlights
description: Add the 4-5 main user-facing changes since the last tag to frontend/src/lib/releaseHighlights.js (the "What's new" dialog), in every app language. Use when preparing a Downtify release or when asked to update the What's new highlights.
argument-hint: "[version]  (default: the version in downtify/__init__.py)"
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *), Bash(npm --prefix frontend *), Bash(npx --prefix frontend *), Read, Edit
---

# Release highlights for the "What's new" dialog

Add an entry for the release being cut to `frontend/src/lib/releaseHighlights.js`. The dialog (`frontend/src/components/shell/WhatsNewDialog.vue`) shows it once, on the first visit after the update, with a link to the full changelog on GitHub — so this is **not** the changelog: it's the 4 or 5 things a user of the web app will actually notice.

## 1. Find the version and the range

- **Version** = `$ARGUMENTS` if given, else the `__version__` in `downtify/__init__.py`.
- **Previous tag** = the newest tag (`git tag --sort=-v:refname`) that is *older* than that version — not the version's own tag if it was already created.
- **End of range** = the version's tag if it exists, else `HEAD`.

```bash
git log --no-merges --format='--- %h %s%n%b' <previous-tag>..<end>
git log --merges --format='%s' <previous-tag>..<end>   # PR titles
```

Also read the version's section of `docs/changelog.md` or `release-notes.md` when present (issue and PR titles). For a PR whose title doesn't say enough, `gh pr view <n> --json title,body` is allowed — read only, never comment.

## 2. Pick 4-5 highlights

- New features and changes a user sees or feels first; then important fixes they were hitting. Skip CI, refactors, tests, docs-only, dependency bumps, performance work nobody notices, and anything admin-internal unless it's big (e.g. backups).
- Merge related commits into one line (several lyrics PRs → one "More lyrics" line).
- Each line: **one sentence**, plain language, about what the user can now do. An optional short lead-in (`Backups: …`) is fine. When it names a UI control or page, use the exact label from `frontend/src/i18n/locales/en.js` (and the translated label from each locale file in the translations), e.g. `(Settings → Server → Backups)`.
- No PR/issue numbers, no contributor names, no Markdown (the dialog renders plain text), no emojis.
- Match the tone and length of the entries already in the file.

## 3. Write the entry

- Add `'<version>': { en: [...], ... }` as the **first** key of the exported object (newest first). If the version already has an entry, replace it — say so in the reply.
- Translate into every app language listed in `AVAILABLE_LOCALES` in `frontend/src/i18n/index.js` (`pt-BR`, `es`, `fr`, `de`, `el`, `tr`, `hu`, `bg`, `ko`, `zh-CN`, `zh-TW`, …). Every language must have the **same number of lines** as `en`, in the same order. Use typographic quotes suited to each language, as the existing entries do.
- Don't touch older entries.

## 4. Check

```bash
npx --prefix frontend prettier --write frontend/src/lib/releaseHighlights.js
npm --prefix frontend test -- whatsNew
```

`whatsNew.test.js` fails on an unknown language code, an invalid version key, or a language with a different line count than `en`.

## 5. Reply

Show the English lines, the commit range used (`3.11.0..HEAD`), and what was left out and why in one line. Then add the change to `commit-message.md` (see the repo's CLAUDE.md: Conventional Commits, keep pending uncommitted messages). Don't commit.
