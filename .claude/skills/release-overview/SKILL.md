---
name: release-overview
description: Prepend a short, readable overview of the main changes to release-notes.md (the GitHub release body), written from the generated notes plus the commit messages of the release. Use when preparing a Downtify release or when asked to summarize the release notes.
argument-hint: "[version]  (default: the version at the top of release-notes.md)"
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *), Read, Edit
---

# Overview at the top of release-notes.md

`release-notes.md` (repo root, git-ignored) is the body of the GitHub release. It's generated as a list of issues and merged PRs — complete, but hard to read. Put a short overview **above** it and leave the generated content exactly as it is.

## 1. Read what's there

- Read `release-notes.md`. Its first heading (`## [3.12.0](…) (date)`) gives the version and date; `$ARGUMENTS`, when given, overrides the version. If the file is missing or empty, stop and say so — don't invent notes.
- If it already starts with an overview (between `<!-- overview:start -->` and `<!-- overview:end -->`), it will be **replaced**, not duplicated.

## 2. Read the commits of the release

- **Previous tag** = the newest tag (`git tag --sort=-v:refname`) older than the version; **end** = the version's tag if it exists, else `HEAD`.

```bash
git log --no-merges --format='--- %h %an%n%s%n%n%b' <previous-tag>..<end>
```

- Use the commit bodies to understand *why* and *what changed for the user* behind each PR title. For a PR that's still unclear, `gh pr view <n> --json title,body` is allowed — read only.
- `frontend/src/lib/releaseHighlights.js` may already have this version's highlights (`/release-highlights`); stay consistent with them.

## 3. Write the overview

Insert at the very top of the file, followed by a blank line and the untouched original content:

```markdown
<!-- overview:start -->
## ✨ Highlights

One or two sentences on what this release is about.

- 💾 **Backups** — save what your Downtify knows and restore it after a lost disk or a move to a new server.
- 🖼️ **Sharper covers** — …
- …

### 🛠️ Fixes and improvements

- …

Thanks to @contributor-a and @contributor-b for their contributions! 💜

---
<!-- overview:end -->
```

Rules:

- English, like the rest of the notes.
- **Highlights**: the 4-6 changes users care most about; one line each, bold lead-in + what they can now do. Link the PR or issue at the end of a line when there's one obvious one (`[#630](https://github.com/henriquesebastiao/downtify/pull/630)`).
- **Fixes and improvements**: optional, 3-6 short lines for notable fixes / smaller changes; skip CI, tests, refactors, dependency bumps.
- **Emojis**: one per highlight line and one per heading, at most. None in the fixes list, the intro or anywhere else.
- **Thanks line**: only for contributors other than the maintainer (`henriquesebastiao`), taken from the `(@user)` mentions in the notes. Omit the line if there are none. These handles are real people and GitHub notifies them — use only handles already in the notes.
- Mention breaking changes, migrations or new required env vars first, in a `> [!IMPORTANT]` block right under the intro, when the commits show any. Never invent one.
- Use exact UI labels from `frontend/src/i18n/locales/en.js` when naming controls.
- Keep the `<!-- overview:start -->` / `<!-- overview:end -->` markers (they're invisible on GitHub) so a rerun replaces the overview.

## 4. Check and reply

- Confirm everything after `<!-- overview:end -->` is byte-identical to the original content (`git diff` doesn't help — the file is ignored; compare against what you read).
- Reply with the overview as written and the commit range used. `release-notes.md` is git-ignored, so nothing goes in `commit-message.md`. Don't commit, don't create or edit the GitHub release.
