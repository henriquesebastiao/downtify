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

## How it works

The player loads every audio file found recursively inside the downloads directory. Files are served directly from the container via the `/downloads` static mount.

Filenames in the format `Artist - Title.ext` are parsed so the now-playing card can show artist and title cleanly. Cover art is fetched on demand from the `/cover` endpoint, which reads the embedded image tags from the file itself — the same artwork Downtify wrote at download time.

Playback uses the browser's native HTML5 audio element. No plugins, no extra processes.

## Supported formats

The player can play any format your browser's HTML5 audio engine supports. This typically includes MP3, M4A/AAC, OGG and OPUS in all modern browsers. FLAC support varies — Chrome and Edge support it natively; Firefox and Safari may not.
