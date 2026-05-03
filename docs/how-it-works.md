---
icon: lucide/cog
---

# How It Works

Downtify's download pipeline has three stages:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Metadata — Spotify embed scraping

When you paste a Spotify URL, Downtify fetches the public `open.spotify.com/embed` page for that track, album or playlist. No Spotify account, API key or Premium subscription is needed — the embed page is publicly accessible.

For **tracks**, the embed returns: title, artist(s), album name, release year, duration and the cover image URL.

For **albums and playlists**, the embed returns the track list. Playlist embeds are capped at roughly 50–100 entries, so Downtify also requests the full list from Spotify's anonymous `api.spotify.com` endpoint with pagination to handle playlists with hundreds of songs.

!!! note "Per-track metadata enrichment"
    Playlist embed entries are missing the release year and use the playlist cover instead of each track's own album cover. For the [Playlist Monitor](features/playlist-monitor.md), Downtify re-fetches every new track individually to get the correct cover and year before downloading.

## 2. Audio match — YouTube Music search

Downtify uses [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) to search YouTube Music for the best audio match. The search query is built from the track title and artist name.

Results are ranked by comparing the duration reported by YouTube Music against the duration from Spotify. The closest match within a 10-second window is selected. If no result matches the window, the top search result is used as a fallback.

For YouTube URLs entered directly, this step is skipped — Downtify downloads that specific video.

## 3. Download & tag — yt-dlp + ffmpeg + mutagen

### Download

[yt-dlp](https://github.com/yt-dlp/yt-dlp) downloads the audio from YouTube. Downtify configures it to try several player clients in order (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`) to work around YouTube's bot-detection challenges. See [Environment Variables](getting-started/environment-variables.md) for advanced anti-bot options.

### Conversion

[ffmpeg](https://ffmpeg.org/) converts the raw audio to the selected format (MP3, FLAC, M4A, OGG or OPUS) at the selected bitrate.

### Tagging

[mutagen](https://mutagen.readthedocs.io/) writes the metadata into the converted file:

| Tag | Written |
|-----|---------|
| Title | Yes |
| Artist(s) | Yes |
| Album | Yes |
| Year | Yes |
| Album art (JPEG) | Yes |
| Lyrics (plain + synced) | Yes, if lrclib returns a result |

The exact ID3/Vorbis/MP4 tags used depend on the output format. See [Lyrics](features/lyrics.md) for details on how lyrics are embedded.

## Real-time progress

Downtify streams download progress to the browser over a **WebSocket** connection (`/api/ws`). As yt-dlp reports progress, the server broadcasts percentage and status updates to all connected clients. This means you see the progress bar move in real time — no polling, no page reload needed.

## File naming and organisation

The output filename is built from the template configured in Settings (default: `{artists} - {title}`). Characters that are invalid in filenames are stripped.

When *Organize by artist* is enabled, the file is placed inside a subfolder named after the primary artist. Otherwise, single tracks go into the root of the downloads directory and playlist/album tracks go into a per-playlist or per-album subfolder.
