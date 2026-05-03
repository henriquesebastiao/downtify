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
3. Choose a check interval (from 15 minutes to 24 hours)
4. Click **Watch**

## Check intervals

| Label | Minutes |
|-------|---------|
| Every 15 min | 15 |
| Every 30 min | 30 |
| Every hour | 60 (default) |
| Every 6 hours | 360 |
| Every 12 hours | 720 |
| Every 24 hours | 1 440 |

## Managing monitored playlists

From the Monitor page you can:

- **Pause / Resume** — temporarily disable a playlist without removing it
- **Force check** — trigger an immediate check outside the scheduled interval
- **Remove** — stop monitoring a playlist and delete its record (downloaded files are kept)

## Per-track metadata enrichment

Playlist embed entries are missing the release year and use the playlist cover art instead of the per-track album cover. Downtify re-fetches each new track individually to get the correct cover and year before downloading — falling back to the playlist-level data if the per-track fetch fails.

## M3U integration

After each sweep that downloads at least one new track, Downtify regenerates the playlist's M3U file to reflect the current on-disk state. See [M3U Export](m3u-export.md) for details.

## Storage

Monitor state is stored in a SQLite database at `/data/downtify_monitor.db`. The database records:

- Each monitored playlist (Spotify ID, name, URL, interval, enabled state, last check time)
- Every track successfully downloaded per playlist, including the filename on disk
