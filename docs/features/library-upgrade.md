---
icon: lucide/wand-sparkles
---

# Upgrade library

A library built up over time carries whatever each Downtify version could do when a track was downloaded: the smallest cover a source offered, no lyrics, tags without an album or a year. **Upgrade library** looks at what is already on disk and repairs only what is behind — no re-downloading, and nothing to sort out by hand.

Open it from **Library → Upgrade library**.

::: info Default upgrades only rewrite tags
The default mode rewrites **artwork, lyrics and tags**. Optional [Deemix replacement](#deemix-recording-replacement) is a separate scan mode, disabled by default. Use [Replace audio](replace-audio.md) to choose a different version manually.
:::

## How it works

1. **Scan.** Downtify reads every library track and reports what is behind, per category. Nothing is written.
2. **Choose.** Each category the scan found something for is listed with its track count and a switch. Untick what you don't want.
3. **Upgrade.** The chosen tracks go into a queue that is worked through one at a time. You can pause, resume or stop it, and it survives a restart.

## What it repairs

| Category               | What it does                                                                                                               | Where it looks                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **Upgrade artwork**    | Replaces a cover smaller than your target size                                                                             | Spotify, Apple Music (iTunes), YouTube Music      |
| **Add missing lyrics** | Fills in lyrics for tracks that have none, embedded and as an `.lrc` sidecar                                               | Your [lyrics providers](lyrics.md), in your order |
| **Refresh tags**       | Fills in album, album artist, release date and track number — including the album older single-track downloads are missing | Spotify                                           |

A track counts as behind when:

- its embedded cover's short side is **smaller than the target size** (a track with no cover at all counts too);
- it has **neither** embedded lyrics **nor** an `.lrc` sidecar (next to the file or in the lyrics folder from Settings);
- any of **album**, **album artist**, **year** or **track number** is missing from its tags.

**Refresh tags** only works for tracks Downtify still has a Spotify track ID for — the ones it downloaded from a Spotify link, kept in the [track index](library-catalog.md#what-gets-stored). Other tracks are queued but come back as _Nothing to do_.

## Options

### Upgrade artwork below

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Covers at this size or larger are left alone. Downtify only writes a cover that is **strictly bigger** than the one already in the file, so running an upgrade twice never rewrites anything for nothing.

Where the sizes come from:

| Source                   | Typical size                                                                |
| ------------------------ | --------------------------------------------------------------------------- |
| **Apple Music (iTunes)** | 1200px and up                                                               |
| **Spotify**              | up to 640px                                                                 |
| **YouTube Music**        | up to the [cover resolution](download-settings.md) setting, ~1200px at most |

This is also why a library downloaded before is often stuck at 300–640px: Spotify publishes its covers in fixed sizes, and the largest one it offers is 640px.

### Artwork source

| Choice                                                                 | Behaviour                                                                                            |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Highest resolution available** (default)                             | Asks every source and keeps the biggest image                                                        |
| **Prefer Spotify** / **Prefer Apple Music** / **Prefer YouTube Music** | Uses that source when it has anything at all; the others are only a fallback for when it has nothing |

### Don't check a track again for

`Always check every track` · `7 days` · **`30 days`** · `90 days` · `365 days`

After a track has been looked at, it is skipped by the next scan for this long, so a second run over a large library doesn't ask the same sources about the same tracks again.

The memory is kept **per track and per category**, which is what makes partial runs work: repairing only the artwork of 16,000 tracks says nothing about whether anyone ever went looking for their lyrics, so a later lyrics run still considers every one of them. A scan also records the categories it examined and found nothing to do for — looking and finding nothing is a check like any other.

Downtify remembers, for each track and category: when it was checked, the Downtify version that checked it, and — for artwork — the largest cover found and where it came from. Which lyrics providers were already asked is kept separately, per song and provider (see [Lyrics](lyrics.md)).

Two things always override it:

- a **newer Downtify version** re-checks everything, since it may match or tag better than the one that ran before;
- choosing **Always check every track** ignores the memory for that scan.

When a scan finds nothing left to do _because_ everything was checked recently, it says so and offers to run again without the memory, rather than leaving you with an unexplained "nothing to upgrade".

## While it runs

The progress panel shows tracks done out of the queue, an approximate data figure (`8.4 GB of 51.3 GB`) and how many were upgraded, had nothing to do, or failed. Each track shows what it is doing — _Matching_, _Looking for artwork_, _Looking for lyrics_, _Writing the file_ — and ends with what changed, e.g. `artwork 1200px (itunes)`.

**Pause** stops after the track in flight and keeps the queue. **Stop** drops the rest of it; tracks already upgraded stay upgraded. You can leave the page — the run keeps going, and any other open tab follows along.

The queue lives in `/data/downtify_library.db`, so **restarting Downtify (or the container) mid-run picks it back up** where it stopped. A track that was in flight when the process died is put back in the queue.

## Nothing is lost if an upgrade fails

Every write goes to a working copy beside the original (`<name>.downtify-upgrade.<ext>`). The copy has to open as audio of the same length before it is moved into place; otherwise it is thrown away and the original is left untouched. That file never shows up as a track of its own, and it is gone as soon as the track finishes.

The original **modification time is kept**, so upgrading a library doesn't reshuffle _Recently added_.

### Read-only music folders

An upgrade rewrites tags in place, so tracks on a read-only filesystem are **skipped**, with an explanation, before looking up metadata, artwork or lyrics. They remain playable and in their playlists; their files and mount permissions are left unchanged. A skipped read-only track is not remembered as successfully checked, so it can be considered again if its folder becomes writable later. Unexpected permission, disk-space and I/O errors still appear as failures.

This differs from [existing-folder enrichment](external-library.md), which can keep artwork and lyrics separately in Downtify's data folder without rewriting protected audio files.

## Why audio isn't replaced

Ordinary tag upgrades do not replace audio. The separate mode below requires exact recording metadata and reference publication; uncertain versions remain for manual review.

## Deemix recording replacement

After enabling and testing the [Deemix source](deemix.md), **Upgrade library** offers two independent switches before scanning:

- **Use verified Deemix recordings**: scan original Downtify downloads, including copies hidden by a preferred external collection. Match exact artist, full title/version and album; reject ambiguous catalog results. The old clip's duration is not used to reject a correct catalog recording. Verify the downloaded tags, catalog duration, selected quality and full FFmpeg decode.
- **Remove old Downtify audio after import**: additionally remove each unchanged original after publication. This is off by default. Keeping originals still updates playlists and favorites to the Deemix recording.

This scan produces an **audio** category instead of artwork/lyrics/tag jobs. Deemix owns the output files, artwork, album layout and native lyrics. Downtify reads them in place. Existing native or embedded lyrics are preserved; only absent lyrics may be supplemented in a writable dedicated lyrics folder, without rewriting audio. A higher-quality lossless original is retained when Deemix is configured for MP3.

Publication happens once per batch. M3U comments, manual markers and track order are preserved, then catalog paths, playlist memberships, every user's likes, ownership and hidden-track rules move in one SQLite transaction. Cached Navidrome IDs for old files are invalidated for a fresh native lookup. Previously issued mobile IDs and old playback URLs keep read-only aliases to the registered replacement; mutations never use those URL aliases.

Durable receipts in the library database record source/target SHA-256 values and publication state. Sources remain until the replacement and references verify. A changed or missing mount, edited file, external read-only playlist reference, active playback or failed catalog publication stops cleanup with a visible reason. Pause/resume and restart reuse receipts. There is no general duplicate sweep or age-based cleanup: only verified originals in Downtify's download folder are eligible. Manual Deemix/slskd downloads, external originals, directories and sidecars are never deleted. Once an original is removed, rolling back the container does not restore that file; restore it from your own storage backup if needed.

For NAS consumers whose mount names differ from Docker paths, an administrator can set `DOWNTIFY_DEEMIX_M3U_ROOT` to a container alias resolving to the Deemix root. Relative M3U paths use that alias (for example `/Download` mapped to `/music/existing`). Optional `DOWNTIFY_LIBRARY_READY_MARKERS` is a JSON object of marker paths and expected text, checked before preparation and cleanup. A missing marker fails closed. Neither variable is required for the default mode.

The scan API accepts `replace_audio_deemix: true`, optional `delete_replaced_audio: true`, and optional `files: ["relative/original.mp3"]` for a bounded pilot. Starting that scan selects `categories: ["audio"]`. Run status includes replacement counts and a `finalization_error` when publication pauses. No source file is removed just because a Deemix queue item says completed.

### Review an uncertain recording

A skipped or failed audio job offers **Choose a Deezer recording**. Paste an exact track link, preview its artist, album and duration, then choose **Analyze this choice**. This only prepares a new single-track scan; confirm that scan to start replacement. The default automatic matcher never guesses a different album.

This explicit choice can correct an old album label, but the full title/version and artist must still match. A known explicit original cannot silently become a clean version. The selected recording undergoes the same duration, quality, decode, reference and deletion checks. A different choice cannot silently reuse an already prepared receipt. The advanced scan payload records the choice as `deemix_recordings: {"relative/original.mp3": "123456"}`; it is scoped to that file and saved for restart/resume.

## API

| Method | Path                          | Description                                     |
| ------ | ----------------------------- | ----------------------------------------------- |
| `GET`  | `/api/library/upgrade`        | Run state, queue counts and what the scan found |
| `GET`  | `/api/library/upgrade/jobs`   | Per-track rows (`status`, `stage`, `detail`)    |
| `POST` | `/api/library/upgrade/scan`   | Scan the library; writes nothing                |
| `POST` | `/api/library/upgrade/start`  | Start the run for the chosen `categories`       |
| `POST` | `/api/library/upgrade/pause`  | Stop after the current track, keep the queue    |
| `POST` | `/api/library/upgrade/resume` | Continue a paused run                           |
| `POST` | `/api/library/upgrade/cancel` | Drop the rest of the queue                      |

Progress is also pushed over the [WebSocket](../api-reference.md#websocket) as `{"type": "library_upgrade", "upgrade": {…}}`.

See the [API reference](../api-reference.md#library) for request and response shapes.
