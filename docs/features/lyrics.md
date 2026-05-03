---
icon: lucide/mic-vocal
---

# Lyrics

Downtify can download lyrics and embed them directly into audio files at download time.

## Enabling lyrics

Lyrics are **enabled by default**. You can toggle them in **Settings → Lyrics → Download lyrics**.

## Provider

The only active provider is **[lrclib](https://lrclib.net)** — a free, open, community-maintained lyrics database. No API key is required.

lrclib is queried with the track title, primary artist, album name and duration. It returns:

- **Plain lyrics** — static text, embedded as standard lyrics tags
- **Synced lyrics** — time-coded LRC format, embedded as a separate tag and also saved as a `.lrc` sidecar file alongside the audio

## Embedding

| Format | Plain lyrics tag | Synced lyrics tag |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` with timestamps |
| FLAC | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |
| M4A | `©lyr` | `©lyr` with LRC content |
| OGG / OPUS | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |

## Sidecar .lrc file

When synced lyrics are available, Downtify also saves a `.lrc` file next to the audio file with the same base name. This lets media players that support external lyrics files (like Jellyfin or certain portable players) show the time-synced lyrics independently of the embedded tags.

## Fallback behaviour

If lrclib returns no result for a track, the download continues normally — the audio file is saved without lyrics. No error is raised.

## Legacy providers

The settings UI may show `genius`, `musixmatch` and `azlyrics` as options inherited from an earlier version of Downtify. These are **no-ops** — selecting them has no effect. Only `lrclib` fetches real lyrics.
