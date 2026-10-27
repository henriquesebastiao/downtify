---
icon: lucide/hard-drive
---

# Storage & Usage

**Storage and usage** shows how big the library is, how fast it grows, which audio source each part came from, how downloads ended, and how much room is taken by files the library doesn't need — without opening a single folder. Admins open it from the **Storage and usage** button at the top of the Library page; other accounts don't see it.

The period buttons at the top (7, 30, 90 or 365 days) set what "in the period" means everywhere on the page, and the page remembers the last one picked.

## What the page shows

| Section | What it tells you |
|---------|-------------------|
| **Library** | Size of the library and how many songs it holds |
| **Added in N days** | Size and number of songs that came into the library during the period and are still there |
| **Net change** | How much the library grew (or shrank) over the period, and that change as a weekly rate |
| **Free space** | Free space on the disk that holds the downloads folder; once the library grows fast enough to matter, roughly how many days until it is full at the current rate |
| **Downloaded** | Downloads that finished in the period, with how many were skipped or failed |
| **Could be freed** | What [Could be cleaned up](#could-be-cleaned-up) adds up to |
| **Library size** | The library's size at the end of each day (each week for 365 days); hover the chart for a day's size and song count. Below it, what was added per day or week |
| **By source** | The library split by audio source — YouTube Music, YouTube, Soulseek (slskd), Deemix, [extra music folders](external-library.md) — and what each one added in the period |
| **Where it is stored** | The library by folder (downloads folder, slskd folder, extra music folders) and by format (MP3, FLAC, M4A…) |
| **Downloads** | Completed, skipped and failed downloads per day or week, and how much each source downloaded |
| **Could be cleaned up** | Duplicate songs, slskd working copies, leftover temporary files and orphaned sidecars, each with the files involved |
| **Folders** | Everything in the folders Downtify writes to, by kind: songs, podcasts, lyrics, images, playlists, artist photos and profiles, temporary files |

Nothing on this page deletes or changes a file: it only tells you where the room goes, so you can decide what to clean up — with the Library's delete, [Replace Audio](replace-audio.md), or by hand.

## The library, not its working copies

Every number above counts the **library**: the songs the Library page lists, minus the **slskd working copies**. With **Leave files in the slskd folder** off, Downtify copies each finished Soulseek transfer into the library and the transfer stays behind in slskd's folder; that copy is counted apart, as a working copy, so it never looks like library content of its own (see [slskd & Navidrome](slskd-navidrome.md)). A working copy is:

- a transfer Downtify copied into the library — known for every download from this version on;
- while files aren't left in place, any other audio file in slskd's folder that Downtify doesn't know as a library song.

With **Leave files in the slskd folder** on, slskd's folder *is* where those songs live, so it is part of the library.

## How the numbers are worked out

### Growth over time

Downtify notes the library's size every hour, and keeps the last reading of each day. The chart draws those readings as a solid line.

Days before the first reading — every past day, on the first visit — are **estimated** from the songs still in the library: when each was downloaded (known for the downloads made since Downtify started recording which source fetched each file), else the file's modification date. The estimate is drawn dashed: it can only show songs that are still there, so a song deleted since is missing from it. The longer Downtify runs, the more of the chart is measured.

### Downloads

Every download is counted when it ends, from the queue and from [Playlist Monitor](playlist-monitor.md) sweeps alike:

- **Completed** — a new file was downloaded and tagged; its size counts toward the source that fetched it.
- **Skipped** — the song was already in the library, so nothing was downloaded (with **Download again if the file exists** off, see [Overwrite existing files](download-settings.md#overwrite-existing-files)).
- **Failed** — no source had it, it was too long, or the source failed.

Each attempt counts: a song a watch fails to download on every check counts as a failure each time. Downloads are counted from this version on and kept for 400 days, so a period older than the first one counted says since when it is counting.

### Could be cleaned up

| Category | What it is |
|----------|-----------|
| **Duplicate songs** | Library files holding the same song. **Same file**: one name and size in two folders, typically one song downloaded into two playlist folders. **Likely the same song**: the same artist and title, lengths within 3 seconds — such as one song from YouTube Music and again from Soulseek. The size is what keeping only the largest copy of each would free |
| **slskd working copies** | See [The library, not its working copies](#the-library-not-its-working-copies) |
| **Leftover temporary files** | Partial downloads (`.part`, `.ytdl`), unfinished conversions (`.temp.mp3`), atomic-write leftovers (`.tmp`) and [Upgrade library](library-upgrade.md) working copies, older than an hour (a younger one may still be in use) |
| **Orphaned sidecars** | `.lrc` lyrics files with no song of the same name beside them (or, in a separate lyrics folder, no library song at their path), and album `cover.jpg` files in a folder with no songs and no playlist left |

Open a category to see its files, biggest first (the 50 biggest are listed).

::: tip Duplicates are a hint, not a verdict
"Likely the same song" compares tags and length, not the audio. A live version tagged with the studio title and length, or two different songs that share a title and artist, can be listed. Check before deleting.
:::

### Folders

The **Folders** section walks the downloads folder, slskd's folder and the lyrics folder (when lyrics are saved in a folder of their own, see [Lyrics](lyrics.md)) and sorts every file by kind. A folder inside another is walked once, as itself. The walk takes a while on a big library, so its result is kept for 10 minutes; **Scan again** walks the folders right away, and **Refresh** at the top reloads everything. Extra music folders aren't walked: they are yours, not Downtify's.

## API

[`GET /api/library/usage`](../api-reference.md#get-apilibraryusage) (`?days=`) returns everything but the folder walk, which is [`GET /api/library/usage/scan`](../api-reference.md#get-apilibraryusagescan) (`?refresh=`). Both are admin-only.
