---
icon: lucide/wand-sparkles
---

# Upgrade library

A library built up over time carries whatever each Downtify version could do when a track was downloaded: the smallest cover a source offered, no lyrics, tags without an album or a year. **Upgrade library** looks at what is already on disk and repairs only what is behind — no re-downloading, and nothing to sort out by hand.

Open it from **Library → Upgrade library**.

::: info Audio files are never replaced
An upgrade rewrites **artwork, lyrics and tags**. It does not fetch a different audio file, so a track that was matched to the wrong song, a live version or a remix stays as it is — delete it and download it again. See [Why audio isn't replaced](#why-audio-isnt-replaced).
:::

## How it works

1. **Scan.** Downtify reads every library track and reports what is behind, per category. Nothing is written.
2. **Choose.** Each category the scan found something for is listed with its track count and a switch. Untick what you don't want.
3. **Upgrade.** The chosen tracks go into a queue that is worked through one at a time. You can pause, resume or stop it, and it survives a restart.

## What it repairs

| Category | What it does | Where it looks |
|----------|--------------|----------------|
| **Upgrade artwork** | Replaces a cover smaller than your target size | Spotify, Apple Music (iTunes), YouTube Music |
| **Add missing lyrics** | Fills in lyrics for tracks that have none, embedded and as an `.lrc` sidecar | Your [lyrics providers](lyrics.md), in your order |
| **Refresh tags** | Fills in album, album artist, release date and track number | Spotify |

A track counts as behind when:

- its embedded cover's short side is **smaller than the target size** (a track with no cover at all counts too);
- it has **neither** embedded lyrics **nor** an `.lrc` sidecar next to it;
- any of **album**, **album artist**, **year** or **track number** is missing from its tags.

**Refresh tags** only works for tracks Downtify still has a Spotify track ID for — the ones it downloaded from a Spotify link, kept in the [track index](library-catalog.md#what-gets-stored). Other tracks are queued but come back as *Nothing to do*.

## Options

### Upgrade artwork below

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Covers at this size or larger are left alone. Downtify only writes a cover that is **strictly bigger** than the one already in the file, so running an upgrade twice never rewrites anything for nothing.

Where the sizes come from:

| Source | Typical size |
|--------|--------------|
| **Apple Music (iTunes)** | 1200px and up |
| **Spotify** | up to 640px |
| **YouTube Music** | up to the [cover resolution](download-settings.md) setting, ~1200px at most |

This is also why a library downloaded before is often stuck at 300–640px: Spotify publishes its covers in fixed sizes, and the largest one it offers is 640px.

### Artwork source

| Choice | Behaviour |
|--------|-----------|
| **Highest resolution available** (default) | Asks every source and keeps the biggest image |
| **Prefer Spotify** / **Prefer Apple Music** / **Prefer YouTube Music** | Uses that source when it has anything at all; the others are only a fallback for when it has nothing |

### Don't check a track again for

`Always check every track` · `7 days` · **`30 days`** · `90 days` · `365 days`

After a track has been looked at, it is skipped by the next scan for this long, so a second run over a large library doesn't ask the same sources about the same tracks again.

The memory is kept **per track and per category**, which is what makes partial runs work: repairing only the artwork of 16,000 tracks says nothing about whether anyone ever went looking for their lyrics, so a later lyrics run still considers every one of them. A scan also records the categories it examined and found nothing to do for — looking and finding nothing is a check like any other.

Downtify remembers, for each track and category: when it was checked, the Downtify version that checked it, and — for artwork — the largest cover found and where it came from. Which lyrics providers were already asked is kept separately, per song and provider (see [Lyrics](lyrics.md)).

Two things always override it:

- a **newer Downtify version** re-checks everything, since it may match or tag better than the one that ran before;
- choosing **Always check every track** ignores the memory for that scan.

When a scan finds nothing left to do *because* everything was checked recently, it says so and offers to run again without the memory, rather than leaving you with an unexplained "nothing to upgrade".

## While it runs

The progress panel shows tracks done out of the queue, an approximate data figure (`8.4 GB of 51.3 GB`) and how many were upgraded, had nothing to do, or failed. Each track shows what it is doing — *Matching*, *Looking for artwork*, *Looking for lyrics*, *Writing the file* — and ends with what changed, e.g. `artwork 1200px (itunes)`.

**Pause** stops after the track in flight and keeps the queue. **Stop** drops the rest of it; tracks already upgraded stay upgraded. You can leave the page — the run keeps going, and any other open tab follows along.

The queue lives in `/data/downtify_library.db`, so **restarting Downtify (or the container) mid-run picks it back up** where it stopped. A track that was in flight when the process died is put back in the queue.

## Nothing is lost if an upgrade fails

Every write goes to a working copy beside the original (`<name>.downtify-upgrade.<ext>`). The copy has to open as audio of the same length before it is moved into place; otherwise it is thrown away and the original is left untouched. That file never shows up as a track of its own, and it is gone as soon as the track finishes.

The original **modification time is kept**, so upgrading a library doesn't reshuffle *Recently added*.

## Why audio isn't replaced

Swapping the audio file a user already has is a different problem from rewriting its tags: it needs match confidence, a review step for uncertain matches, and every M3U, Navidrome playlist and catalog entry that points at the old filename has to follow it. Doing that half-way risks overwriting a good file with a worse one, so it is deliberately left out rather than guessed at.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/library/upgrade` | Run state, queue counts and what the scan found |
| `GET` | `/api/library/upgrade/jobs` | Per-track rows (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Scan the library; writes nothing |
| `POST` | `/api/library/upgrade/start` | Start the run for the chosen `categories` |
| `POST` | `/api/library/upgrade/pause` | Stop after the current track, keep the queue |
| `POST` | `/api/library/upgrade/resume` | Continue a paused run |
| `POST` | `/api/library/upgrade/cancel` | Drop the rest of the queue |

Progress is also pushed over the [WebSocket](../api-reference.md#websocket) as `{"type": "library_upgrade", "upgrade": {…}}`.

See the [API reference](../api-reference.md#library) for request and response shapes.
