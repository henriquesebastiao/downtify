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

Which produces filenames like `Arctic Monkeys - Do I Wanna Know.mp3`.

Available tokens:

| Token | Description |
|-------|-------------|
| `{title}` | Track title |
| `{artists}` | Comma-separated artist names |
| `{album}` | Album name |

## Parallel downloads

Controls how many songs are downloaded simultaneously.

| Value | Behaviour |
|-------|-----------|
| **1** | Sequential — one song at a time (safest, lowest resource use) |
| **2** | Mild concurrency |
| **3** | Default. Good balance of speed and stability. |
| **5** | Faster for large playlists |
| **8** | Maximum. Best for fast connections; uses more CPU and bandwidth. |

The limit applies to every download — both individual tracks and batch playlist imports. Changing this value in Settings takes effect immediately without a restart.

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
