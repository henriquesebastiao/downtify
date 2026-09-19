---
icon: lucide/headphones
---

# Built-in Player

Downtify ships with a web player so you can listen to your downloaded music without a separate app. Hit play on any track, album, artist or playlist in the Library — or on a finished download in the Queue — and the player starts.

## Player bar

While a track is loaded, a player bar floats at the bottom of every page: cover art, title and artist, shuffle, previous, play/pause, next, repeat, elapsed/total time, and shortcuts to the lyrics and up-next panels (the lyrics one can be [hidden](#hiding-the-lyrics)). On wide screens it also has a volume slider and a seek bar along its top edge; on phones it shrinks to the essentials and shows a thin progress line.

Next to the title there is a heart to [like the song](liked-songs.md); phones leave it out of the bar to keep room for the title, and have it in **Now playing** and in the track lists instead.

Click the title or cover, or the expand button, to open **Now playing**.

## Now playing

A full-screen view tinted with colours picked from the current album cover:

- **Large cover art**, title and artist (click the artist or the *Playing from* label to jump to that artist, album or playlist), with a heart beside the title to [like the song](liked-songs.md)
- **Seek bar** — click or drag, or use the arrow keys when it's focused. While a track plays, soft waves drift over the played part in colours picked from the album cover; they settle flat when paused, and stay still if your system asks for reduced motion
- **Playback controls** — shuffle, previous, play/pause, next, repeat (off → repeat all → repeat one)
- **Volume** with mute toggle, saved between sessions. Hidden on phones, where the hardware buttons control the level
- **Sleep timer** — stop playback in 15, 30, 45, 60 or 90 minutes, or at the end of the current track. The remaining time shows next to the timer button
- **File info** — format and size of the playing file

Four panels sit next to the cover on wide screens, or replace it on phones:

- **Lyrics** — time-synced lyrics highlight the current line and scroll with the song; click a line to jump there. Plain lyrics are shown as-is. Lyrics come from the `.lrc` file next to the track, or those embedded in its tags — see [Lyrics](lyrics.md). You can hide this panel — see [Hiding the lyrics](#hiding-the-lyrics).
- **Up next** — the play queue. Drag tracks to reorder them, remove single tracks, or clear everything after the current one.
- **Details** — title, artist, album, track number, year, length, format, size, date added and file path.
- **Equalizer** — shape the sound with ten frequency bands; see [Equalizer](#equalizer).

Now playing is part of the page address (`?np=1`, plus `&panel=lyrics|queue|details|equalizer`), so the browser's Back button closes it and a reload keeps it open.

## Hiding the lyrics

Prefer the artwork and the queue without the words? Turn off **Settings → General → Player → Show lyrics in the player**. It applies at once, and takes away everything that leads to lyrics in the player:

- the **Lyrics** panel and its tab (on phones, its button in the Now playing footer);
- the lyrics button on the player bar;
- the `L` shortcut, which is also dropped from the shortcut list (`?`).

Now playing then opens on **Up next** instead. A link to `&panel=lyrics` from before you turned it off lands there too, rather than on an empty tab. The player doesn't ask for a track's lyrics at all while they're hidden.

::: info Hiding is not deleting
This only changes what the player shows. Your files keep the lyrics Downtify embedded in them, and the `.lrc` files next to them stay in place, so media servers and other players still see them. Downloads keep fetching lyrics too — that's the separate **Download lyrics** setting under **Tags & lyrics** (see [Lyrics](lyrics.md)).
:::

Like the theme and the equalizer, the choice is saved in the browser (`localStorage`), so it is per device and per browser, not per Downtify server — you can hide the lyrics on a phone and keep them on a desktop.

## Equalizer

A ten-band graphic equalizer, in the **Equalizer** panel of Now playing (or press `E`). It's marked **Experimental**: it may still change, and it may misbehave in some browsers (see [Browser support](#browser-support)).

- **Bands** at 31, 62, 125, 250, 500 Hz and 1, 2, 4, 8, 16 kHz, each ±12 dB in 0.5 dB steps. The 31 Hz and 16 kHz bands are shelves, so they also lift or cut everything below / above them. Drag a band, or focus it and use the arrow keys (`Page Up`/`Page Down` for 1 dB, `Home`/`End` for the limits); double-click resets it to 0.
- **Presets** — Flat, Bass boost, Treble boost, Vocal, Rock, Electronic and Acoustic. Moving any band afterwards turns the preset into **Custom**.
- **Preamp** — ±12 dB on top of everything.
- **On/off switch** and **Reset** (back to Flat, preamp 0, off). Moving a band or picking a preset also switches the equalizer on.
- The curve behind the sliders is the combined response of all bands.

Boosting bands would push loud music past full scale and distort it, so Downtify automatically lowers the volume by the curve's highest boost — the panel says by how much. That keeps the peak at 0 dB, so a boosted preset reshapes the sound rather than just making it louder. Raising the preamp above 0 dB removes that safety margin, and the panel warns that loud passages may distort.

The settings are saved in the browser (`localStorage`) and apply to everything you play, in every tab, until you change them. They're per browser, not per Downtify server.

### Browser support

The equalizer uses the Web Audio API, available in all current browsers. Until you switch it on, playback doesn't touch Web Audio at all. Once it's on, audio for the rest of the visit runs through it — switching off just flattens every band.

::: warning Safari on iPhone and iPad
iOS may pause Web Audio when the screen locks or you switch apps, which stops playback while the equalizer is on. If you listen with the screen off, turn the equalizer off and reload the page.
:::

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
| `L` | Open lyrics (unless [hidden](#hiding-the-lyrics)) |
| `Q` | Open up next |
| `E` | Open the equalizer |
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
