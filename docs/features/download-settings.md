---
icon: lucide/sliders-horizontal
---

# Download Settings

Open the settings panel by clicking the gear icon (⚙️) in the navigation bar. Settings are saved to disk and survive container restarts.

## Format

| Format | Extension | Notes |
|--------|-----------|-------|
| MP3 | `.mp3` | Default. Universal compatibility. |
| FLAC | `.flac` | Lossless. Bitrate setting is ignored. |
| M4A | `.m4a` | AAC in an MPEG-4 container. Good for Apple devices. |
| OGG | `.ogg` | Ogg Vorbis. Open format, good quality-to-size ratio. |
| OPUS | `.opus` | Best compression at low bitrates. |

## Bitrate

Available for lossy formats (MP3, M4A, OGG, OPUS). FLAC ignores this setting.

| Option | Kbps |
|--------|------|
| Low | 128 |
| Medium | 192 |
| High | 256 |
| Best | **320** (default) |

## Output filename template

The default filename template is:

```
{artists} - {title}
```

Which produces filenames like `The Night Owls - Do I Still Recall.mp3`.

Available tokens:

| Token | Description |
|-------|-------------|
| `{title}` | Track title |
| `{artists}` | Comma-separated artist names |
| `{album}` | Album name |

## Parallel downloads

Controls how many songs are downloaded simultaneously. Pick a preset (1, 2, 3, 5, 8) or type any custom value from **1 to 30** into the number field next to the presets.

| Value | Behaviour |
|-------|-----------|
| **1** | Sequential — one song at a time (safest, lowest resource use) |
| **3** | Default. Good balance of speed and stability. |
| **8** | Faster for large playlists |
| **up to 30** | Best for very fast connections; uses more CPU and bandwidth, and increases the chance of YouTube rate-limiting you. |

The limit applies to every batch download — playlist/album downloads, the batch queue endpoint, and CSV [library imports](library-import.md). It does **not** apply to Playlist Monitor sweeps, which download new tracks one at a time. Changing this value in Settings takes effect immediately without a restart; the server clamps any value outside `1–30`.

## Delay between downloads

Makes Downtify wait a configurable number of seconds after finishing one song before starting the next one, instead of firing requests back-to-back.

| Value | Behaviour |
|-------|-----------|
| **0** | Default — off, no delay. |
| **5 / 15 / 30 / 60** | Presets, or type any custom value from **0 to 300 seconds**. |

This applies to playlist, album and batch downloads, CSV [library imports](library-import.md), and Playlist Monitor's automatic sweeps. It is skipped for a single manual track download (there's no "next" song to wait for), and skipped after the *last* track in any batch so a run doesn't trail off with a pointless wait at the end.

Combined with a lower **Parallel downloads** value, this is the main tool for avoiding YouTube rate-limiting when downloading a large playlist or an imported library unattended.

## Audio provider

Currently the only supported audio provider is **YouTube Music**. Downtify uses [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) to search for the best match by comparing track duration.

### Force a specific audio source

If Downtify picks the wrong YouTube Music video (e.g. a cover instead of the original), you can override it per track:

**Option A — paste a YouTube Music URL directly**

Paste `https://music.youtube.com/watch?v=…` (or a regular `youtube.com/watch?v=…` URL) into the search bar and hit download. Downtify fetches the audio from that exact video.

!!! note
    When downloading via YouTube URL, metadata (title, artist, cover) comes from YouTube rather than Spotify. For clean tags, use Option B.

**Option B — force audio on an already-queued track**

1. In the **Download Queue**, click the 🔗 icon on any queued or completed track.
2. Paste a YouTube or YouTube Music URL into the input that appears.
3. Press **Enter** or click **Apply**.

Downtify re-downloads the track using that exact video while keeping all Spotify metadata (title, artist, album, cover art, lyrics).

## Embedded metadata

Downtify embeds the following tags in every downloaded file, regardless of format:

| Tag | Source |
|-----|--------|
| Title | Spotify embed |
| Artist(s) | Spotify embed |
| Album | Spotify embed |
| Year | Spotify embed (track-level fetch) |
| Album art | Spotify embed (track-level cover) |
| Lyrics | lrclib (if enabled) |
