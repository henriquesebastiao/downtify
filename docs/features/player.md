---
icon: lucide/headphones
---

# Built-in Player

Downtify ships with a web player so you can listen to your downloaded music without a separate app. Open it by clicking the headphones icon (🎧) in the navigation bar, or hit the play button next to any file in the Library.

## What's included

- **Now-playing card** — album art pulled from the embedded tags, track title and artist
- **Progress bar** — click or drag to seek
- **Playback controls** — play, pause, previous, next
- **Shuffle** — stable random order across the whole library queue
- **Repeat modes** — off → repeat all → repeat one
- **Volume slider** — with mute toggle; your volume level is saved between sessions
- **Side queue** — all tracks in your library, each with its own thumbnail; the currently playing track is highlighted
- **Playing from** — pick **All Songs**, one specific downloaded playlist, one artist, or one album, instead of always queuing your whole library

## Playing a single playlist, artist or album

By default the player queues every downloaded track. Use the **Playing from** selector next to the page title to narrow the queue down:

- **Playlists** — picks up any playlist that has an [M3U file](m3u-export.md). Playlist and album downloads, [CSV imports](library-import.md), and [Playlist Monitor](playlist-monitor.md) all write one automatically, so this works retroactively on everything you've already downloaded. A single track or an album downloaded without an M3U (e.g. via the YouTube Music album flow) isn't a "playlist" and won't appear in this group — it's still part of **All Songs**.
- **Artists** and **Albums** — built from each file's embedded artist/album tags, so they list every artist and album you've ever downloaded regardless of how the files are organized on disk (loose in the library root, in per-playlist folders, or in `Artist/Album` folders when [*Organize by artist/album*](file-organization.md) is on). A track with no artist or album tag simply isn't a member of either group, but it's still part of **All Songs**.

Switching the selection replaces the queue and stops whatever was playing; pick a track or hit play to start the new one. Reopening the player later resumes whichever queue (all songs, a playlist, an artist, or an album) was last loaded.

The Library page (the file browser in the navigation bar) has the same **Filter by** selector, built from the same playlist/artist/album data — use it to narrow down the file list before deleting, re-downloading, or hitting play on a track, instead of scrolling through the whole library.

## How it works

The player loads every audio file found recursively inside the downloads directory. Files are served directly from the container via the `/downloads` static mount. The playlist group is built from the `.m3u` files already on disk (`GET /playlists`); the artist/album groups are built from each file's embedded tags (`GET /tracks`) — no separate playlist or library database.

Filenames in the format `Artist - Title.ext` are parsed so the now-playing card can show artist and title cleanly. Cover art is fetched on demand from the `/cover` endpoint, which reads the embedded image tags from the file itself — the same artwork Downtify wrote at download time.

Playback uses the browser's native HTML5 audio element. No plugins, no extra processes.

## Supported formats

The player can play any format your browser's HTML5 audio engine supports. This typically includes MP3, M4A/AAC, OGG and OPUS in all modern browsers. FLAC support varies — Chrome and Edge support it natively; Firefox and Safari may not.
