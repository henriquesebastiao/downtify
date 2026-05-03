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

## Audio provider

Currently the only supported audio provider is **YouTube Music**. Downtify uses [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) to search for the best match by comparing track duration.

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
