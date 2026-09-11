---
icon: lucide/eye
---

# Playlist Monitor

The Playlist Monitor watches your favourite Spotify and YouTube Music playlists — and the artists you follow — and automatically downloads new tracks and new releases as they appear, hands-free.

Two kinds of watch live side by side on the same page:

| Watch | Paste | Downloads |
|-------|-------|-----------|
| **Playlist** | A Spotify or YouTube Music playlist URL | Every track in the playlist, then any track added later |
| **Artist** | A Spotify **artist** URL, or a YouTube Music artist URL | The artist's whole discography, then every new release |

Every watch shows a **Spotify** or **YouTube Music** badge next to its name, naming the service it was added from.

See [Artist Watch](#artist-watch) for how artist watches work.

## How it works

Downtify keeps a background task running every 60 seconds. On each sweep it checks every enabled watch to see if it is due for inspection (based on its configured interval). When a *playlist* is due, Downtify:

1. Fetches the full track list from Spotify or YouTube Music
2. Compares it against the set of tracks already downloaded
3. Downloads any new tracks using the same pipeline as a manual download
4. Updates the M3U file for the playlist (if M3U generation is enabled)

Tracks that were already in the playlist when you added it are skipped — only *new* additions are downloaded. If a track's file is later deleted from disk, it will be re-downloaded on the next check.

A watch is never checked twice at the same time. Adding a watch starts its first check immediately; if that check is still downloading when the next scheduled sweep comes around, the sweep skips the watch instead of starting a second, overlapping download of the same tracks.

## Adding a playlist

1. Click the eye icon (👁️) in the navigation bar
2. Paste a playlist URL:
    - Spotify: `https://open.spotify.com/playlist/…`
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (a `www.youtube.com/playlist?list=…` link works too)
3. Choose a check interval (from 15 minutes to once a month)
4. Click **Watch**

## YouTube Music playlists

Use a YouTube Music playlist for songs that aren't on Spotify: remixes, live sets, covers, uploads by promo channels. Each track is downloaded from **the exact video in the playlist**. Downtify doesn't search for it again, so what you get is what you added to the playlist.

- **All tracks are fetched**, however long the playlist is. Deleted or private videos are skipped.
- **Artist and title come from the video title.** Many playlist entries are uploads credited to the channel that posted them (e.g. `MrSuicideSheep`), and the real credit is in the title, like `Bronze Whale - Patterns`. For anything that isn't a catalogue release, Downtify splits `Artist - Title` into the file name and tags. It also drops suffixes like `(Official Video)` or `[Lyrics]`. A part after the dash that names a version (`Yellow - Live at Glastonbury`) stays in the title. Catalogue tracks (official audio, or anything filed under an album) keep YouTube Music's own artist and title.
- **Not every `list=` link is a playlist.** An album's `OLAK5uy_…` link is still downloaded as an album. A `watch?v=…&list=…` link is the one song that was playing. A radio mix (`list=RD…`) has no fixed track list and can't be watched.

## Artist Watch

Instead of building a playlist per artist, paste an artist link and Downtify follows their whole catalogue. Add one exactly like a playlist — paste the URL, pick an interval, click **Watch**. Artist watches show an **Artist** badge and a release count instead of a track count.

Accepted URLs:

- A Spotify artist URL (`https://open.spotify.com/artist/…`)
- A YouTube Music artist URL, by channel (`https://music.youtube.com/channel/UC…`) or by handle (`https://music.youtube.com/@HenriqueeJuliano`)

A handle is resolved to the artist's channel when you add the watch, so the same artist pasted by handle and by channel URL is recognized as one watch. A handle that doesn't belong to a YouTube Music artist is rejected.

On each sweep Downtify lists the artist's discography, compares it against the releases it has already processed, and downloads every track of anything new. A steady-state sweep costs a single request — tracklists are only fetched for releases it hasn't seen before.

!!! note "Why the discography comes from YouTube Music"
    Spotify's public embed exposes an artist's name and a top-tracks preview, but **not** their discography — reading that would need Spotify API credentials, which Downtify deliberately doesn't use. So a Spotify artist link is resolved to its name and matched to the same artist on YouTube Music, which is also where the audio is fetched from. The upside: every release Downtify can see is one it can actually download. The trade-off: for an artist whose name is ambiguous, check that the watch's resolved name is the artist you meant — paste the YouTube Music artist URL directly if it picked the wrong one.

!!! warning "The first sweep downloads the whole back catalogue"
    Adding an artist queues **every** release they have, which for a prolific artist can be hundreds of albums and singles. Set **[Delay between downloads](download-settings.md#delay-between-downloads)** before adding a batch of artists, or you're very likely to get rate-limited.

A release is only recorded as processed once every one of its tracks is accounted for, so a track that fails on a transient error is retried on the next sweep rather than being skipped forever. Tracks that already downloaded are never fetched twice.

Artist watches don't generate M3U files — the tracks are laid out by your [file organization](file-organization.md) settings rather than as a playlist.

## Check intervals

| Label | Minutes | Best for |
|-------|---------|----------|
| Every 15 min | 15 | Frequently updated playlists |
| Every 30 min | 30 | |
| Every hour | 60 (default) | Most playlists |
| Every 3 hours | 180 | |
| Every 6 hours | 360 | |
| Every 12 hours | 720 | |
| Every day | 1 440 | Slowly changing playlists |
| Every week | 10 080 | Playlists updated weekly |
| Every 2 weeks | 20 160 | |
| Every month | 43 200 | Archive or rarely updated playlists |

You can change the interval of an existing playlist at any time from the monitor card without removing and re-adding it.

## Managing monitored playlists

From the Monitor page you can:

- **Pause / Resume** — temporarily disable a playlist without removing it
- **Force check** — trigger an immediate check outside the scheduled interval
- **Remove** — stop monitoring a playlist and delete its record (downloaded files are kept)

## Sorting

When you're watching more than one playlist, a **Sort by** control appears above the list. Sort by:

| Field | Notes |
|-------|-------|
| Date added | Default — newest first |
| Title | Alphabetical |
| Refresh frequency | Most frequent (shortest interval) first |
| Number of tracks | Most tracks first |
| Days since checked | Never-checked playlists surface first |
| Paused / Active | Active playlists first |

Click the direction button next to the dropdown to flip between ascending and descending order. The sort is applied client-side only — it doesn't change check order or scheduling.

## Choosing a daily sync time

By default, a playlist checked every day (or week / 2 weeks / month) syncs at whatever time it was originally added or last checked — there's no guaranteed time of day. To pin day-or-longer syncs to a specific hour (e.g. run overnight at 3 AM instead of whenever), set the `DOWNTIFY_MONITOR_SYNC_TIME` environment variable together with `TZ`. See [Environment Variables](../getting-started/environment-variables.md#playlist-monitor) for the full reference.

- Only affects intervals of a full day or more — shorter intervals (15 min – 12 h) are unaffected, since anchoring them to a single daily time would break their cadence.
- The very first check after adding a playlist always runs immediately, regardless of this setting.

## Per-track metadata enrichment

Spotify playlist embed entries are missing the release year and use the playlist cover art instead of the per-track album cover. Downtify re-fetches each new track individually to get the correct cover and year before downloading — falling back to the playlist-level data if the per-track fetch fails. YouTube Music playlist entries skip this step: each one already carries its own video's metadata.

## M3U integration

The playlist's M3U is rewritten **after every track finishes**, so it grows as the sweep downloads rather than appearing only once everything is done. The playlist is playable from the first track onwards, and a slow or hung download further down the list never holds up the tracks that already landed. A final rewrite at the end of the sweep re-resolves everything against the filesystem.

Manual playlist/album downloads and CSV imports behave the same way. See [M3U Export](m3u-export.md#when-it-is-written) for details.

## Storage

Monitor state is stored in a SQLite database at `/data/downtify_monitor.db`. The database records:

- Each watch (kind, Spotify or YouTube Music playlist ID or YouTube Music channel ID, name, URL, interval, enabled state, last check time). Whether a watch is Spotify or YouTube Music is read from its stored URL, so no extra column is needed.
- Every track successfully downloaded per watch, including the filename on disk
- For artist watches, the releases already processed, so a sweep only fetches tracklists for genuinely new ones

Databases created before Artist Watch are migrated automatically on startup; existing rows keep working as playlist watches.
