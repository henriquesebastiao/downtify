---
icon: lucide/eye
---

# Playlist Monitor

The Playlist Monitor watches your favourite Spotify playlists and automatically downloads new tracks as they are added — hands-free.

## How it works

Downtify keeps a background task running every 60 seconds. On each sweep it checks every enabled monitored playlist to see if it is due for inspection (based on its configured interval). When a playlist is due, Downtify:

1. Fetches the full track list from Spotify
2. Compares it against the set of tracks already downloaded
3. Downloads any new tracks using the same pipeline as a manual download
4. Updates the M3U file for the playlist (if M3U generation is enabled)

Tracks that were already in the playlist when you added it are skipped — only *new* additions are downloaded. If a track's file is later deleted from disk, it will be re-downloaded on the next check.

## Adding a playlist

1. Click the eye icon (👁️) in the navigation bar
2. Paste a Spotify playlist URL
3. Choose a check interval (from 15 minutes to once a month)
4. Click **Watch**

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

Playlist embed entries are missing the release year and use the playlist cover art instead of the per-track album cover. Downtify re-fetches each new track individually to get the correct cover and year before downloading — falling back to the playlist-level data if the per-track fetch fails.

## M3U integration

After each sweep that downloads at least one new track, Downtify regenerates the playlist's M3U file to reflect the current on-disk state. See [M3U Export](m3u-export.md) for details.

## Storage

Monitor state is stored in a SQLite database at `/data/downtify_monitor.db`. The database records:

- Each monitored playlist (Spotify ID, name, URL, interval, enabled state, last check time)
- Every track successfully downloaded per playlist, including the filename on disk
