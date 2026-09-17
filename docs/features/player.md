---
icon: lucide/headphones
---

# Built-in Player

Downtify ships with a web player so you can listen to your downloaded music without a separate app. Hit play on any track, album, artist or playlist in the Library — or on a finished download in the Queue — and the player starts.

## Player bar

While a track is loaded, a player bar floats at the bottom of every page: cover art, title and artist, shuffle, previous, play/pause, next, repeat, elapsed/total time, and shortcuts to the lyrics and up-next panels. On wide screens it also has a volume slider and a seek bar along its top edge; on phones it shrinks to the essentials and shows a thin progress line.

Click the title or cover, or the expand button, to open **Now playing**.

## Now playing

A full-screen view tinted with colours picked from the current album cover:

- **Large cover art**, title and artist (click the artist or the *Playing from* label to jump to that artist, album or playlist)
- **Seek bar** — click or drag, or use the arrow keys when it's focused. While a track plays, soft waves drift over the played part in colours picked from the album cover; they settle flat when paused, and stay still if your system asks for reduced motion
- **Playback controls** — shuffle, previous, play/pause, next, repeat (off → repeat all → repeat one)
- **Volume** with mute toggle, saved between sessions. Hidden on phones, where the hardware buttons control the level
- **Sleep timer** — stop playback in 15, 30, 45, 60 or 90 minutes, or at the end of the current track. The remaining time shows next to the timer button
- **File info** — format and size of the playing file

Three panels sit next to the cover on wide screens, or replace it on phones:

- **Lyrics** — time-synced lyrics highlight the current line and scroll with the song; click a line to jump there. Plain lyrics are shown as-is. Lyrics come from the `.lrc` file next to the track, or those embedded in its tags — see [Lyrics](lyrics.md).
- **Up next** — the play queue. Drag tracks to reorder them, remove single tracks, or clear everything after the current one.
- **Details** — title, artist, album, track number, year, length, format, size, date added and file path.

Now playing is part of the page address (`?np=1`, plus `&panel=lyrics|queue|details`), so the browser's Back button closes it and a reload keeps it open.

## Building the queue

Playing an album, artist, playlist or the track list queues those tracks in order, starting from the one you picked. **Shuffle** on a collection starts it in a random order.

Every track's menu (the **⋯** button, or right-click on desktop) has:

- **Play next** — insert right after the current track
- **Add to queue** — append to the end
- **Go to album** / **Go to artist**
- **Save to this device** — download the file through the browser
- **Delete from library**

The same actions apply to a multi-track selection in the Library.

The queue, the current track, its position, shuffle and repeat are remembered, so reopening Downtify resumes where you left off (queues of more than 2000 tracks aren't remembered). Deleted files drop out of the queue automatically.

## Keyboard and media keys

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `←` / `→` | Seek 5 seconds |
| `Shift` + `←` / `→` | Previous / next track |
| `↑` / `↓` | Volume |
| `M` | Mute |
| `S` | Shuffle |
| `R` | Repeat |
| `L` | Open lyrics |
| `Q` | Open up next |
| `Ctrl` / `⌘` + `K` or `/` | Search |
| `G` then `L` / `D` | Go to library / queue |
| `Esc` | Close now playing |
| `?` | Show all shortcuts |

Shortcuts are ignored while you type in a field or while a dialog is open.

The player also reports the current track to the operating system (Media Session), so lock-screen controls, headset buttons and keyboard media keys work, with the cover shown where the system supports it.

## How it works

Tracks come from the library listing (`GET /tracks`), which reads title, artist, album, track number, year and length from each file's tags. Files are served from the `/downloads` static mount; slskd downloads [left in place](slskd-navidrome.md#leave-files-in-place) are played through `/media/slskd/…`. Cover art comes from `/cover` and lyrics from `/lyrics` — see the [API reference](../api-reference.md#file-management).

Playback uses the browser's native HTML5 audio. No plugins, no extra processes.

## Supported formats

The player can play any format your browser's HTML5 audio engine supports. This typically includes MP3, M4A/AAC, OGG and OPUS in all modern browsers. FLAC support varies — Chrome and Edge support it natively; Firefox and Safari may not.
