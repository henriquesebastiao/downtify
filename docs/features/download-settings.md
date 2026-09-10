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
| `{tracknumber}` | Track's position on its album, zero-padded to 2 digits (e.g. `01`, `12`). Empty when the source has no track number (e.g. a free-text/YouTube search result). |

The template can also include `/` to build subfolders. For example, to lay out a library as `Artist/Album/01 - Title.mp3`:

```
{artists}/{album}/{tracknumber} - {title}
```

!!! note
    This is independent of the **Organize by artist** / **Organize by album** toggles below — those route playlist/album downloads into shared per-artist or per-album folders across your whole library. `{tracknumber}` just lets a template like the one above build that same layout manually, track by track, without turning those toggles on.

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

## Download cover art

Controls whether Downtify embeds album art at all. On by default. Turn it off to skip fetching cover art entirely — every other tag (title, artist, album, year, lyrics) still embeds normally, but files end up smaller and download slightly faster since the cover image is never requested or written.

Turning this off also skips writing the standalone `cover.jpg` that the *Organize by album* option (see [File Organization](file-organization.md)) produces, and the [player](player.md)/library will show no artwork for tracks downloaded this way (the fallback music-note icon instead).

## Cover art resolution

Only relevant when **Download cover art** (above) is on. Sets the target size (width and height, in pixels) Downtify requests for embedded cover art sourced from **YouTube Music**. Pick a preset (300, 600, 800, 1000, 1200) or drag the slider anywhere from **300 to 1200**; the current value in pixels is shown next to it. Default is 600.

This is useful when feeding your library into a media server like Plex that displays cover art at higher resolution than Downtify embedded by default — verified against the live YouTube CDN, the higher sizes return genuinely more detail (not just upscaling) for most album art, up to the source image's own resolution.

!!! note "Spotify-sourced covers aren't affected"
    Downtify already embeds the **largest** cover Spotify's public embed API offers for Spotify-resolved tracks/albums/playlists — there's no larger size to request. This setting only raises the ceiling for tracks resolved through YouTube Music (free-text search, YouTube URLs, and any Spotify track re-matched to YouTube Music for the actual audio).

Changing this value in Settings takes effect immediately, including for the currently-open search page — it does not require re-downloading anything already on disk.

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
| Album art | Spotify embed (track-level cover) for Spotify-resolved tracks; YouTube Music thumbnail otherwise. Optional — see [Download cover art](#download-cover-art) and [Cover art resolution](#cover-art-resolution) |
| Lyrics | lrclib (if enabled) |
