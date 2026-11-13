---
icon: lucide/headphones
---

# Built-in Player

Downtify ships with a web player so you can listen to your downloaded music without a separate app. Hit play on any track, album, artist or playlist in the Library — or on a finished download in the Queue — and the player starts.

## Player bar

While a track is loaded, a player bar floats at the bottom of every page: cover art, title and artist, shuffle, previous, play/pause, next, repeat, elapsed/total time, and shortcuts to the lyrics and up-next panels (the lyrics one can be [hidden](#hiding-the-lyrics)). On wide screens it also has a volume slider and a seek bar along its top edge; on phones it shrinks to the essentials and shows a thin progress line.

Next to the title there is a heart to [like the song](liked-songs.md); phones leave it out of the bar to keep room for the title, and have it in **Now playing** and in the track lists instead.

Click the title or cover, or the expand button, to open **Now playing**.

When you're done listening, the **Close** button at the right end of the bar stops playback, clears the queue and puts the bar away. It stays closed after a reload, until you play something again.

## Now playing

A full-screen view tinted with colours picked from the current album cover:

- **Large cover art**, title and artist (click the artist or the *Playing from* label to jump to that artist, album or playlist), with a heart beside the title to [like the song](liked-songs.md). The cover and the lyrics shrink with the window — including when you only change its height — so they stay below the header.
- **Seek bar** — click or drag, or use the arrow keys when it's focused. While a track plays, soft waves drift over the played part in colours picked from the album cover; they settle flat when paused, and stay still if your system asks for reduced motion
- **Playback controls** — shuffle, previous, play/pause, next, repeat (off → repeat all → repeat one)
- **Volume** with mute toggle, saved between sessions. Hidden on phones, where the hardware buttons control the level
- **Sleep timer** — stop playback in 15, 30, 45, 60 or 90 minutes, or at the end of the current track. The remaining time shows next to the timer button
- **File info** — format and size of the playing file

Five panels sit next to the cover on wide screens, or replace it on phones:

- **Lyrics** — time-synced lyrics highlight the current line and scroll with the song; click a line to jump there. Plain lyrics are shown as-is. Lyrics come from the `.lrc` file next to the track, or those embedded in its tags — see [Lyrics](lyrics.md). You can hide this panel — see [Hiding the lyrics](#hiding-the-lyrics).
- **Karaoke** — the same lyrics, made to be sung along to. The words take over the screen in very large, centred lines: the cover, title and artist move into the header next to the button that closes the view, in place of the *Playing from* label, the next song is named in that header on wide screens, the Up next column goes away, and the playback controls shrink — to a single row with the seek bar on wide screens — while all staying available. The current line fills in from left to right, and three dots count you in during the intro and instrumental gaps. Behind the words, stage smoke in the colours of the album cover rolls in from the top-right corner of the screen and reaches only the middle. The line being sung stays on a clear background. The smoke stops while the track is paused and is left out if your system asks for reduced motion. LRC files only time the start of each line, so the fill follows an estimate of how long the line lasts. Click a line to jump there. Plain lyrics are shown large, without the timing.
- **Up next** — the play queue. Drag tracks to reorder them, remove single tracks, or clear everything after the current one.
- **Details** — title, artist, album, track number, year, length, format, size, date added and file path.
- **Equalizer** — shape the sound with ten frequency bands; see [Equalizer](#equalizer).

Now playing is part of the page address (`?np=1`, plus `&panel=lyrics|karaoke|queue|details|equalizer`), so the browser's Back button closes it and a reload keeps it open.

To project the karaoke, use the **Open in a new window** button in the Karaoke header, on wide screens. It opens the lyrics in a window of their own for a projector or second screen, and closes Now playing on the main screen so you can browse Downtify while people sing.

The new window shows only the song, its cover, the next song and the karaoke lyrics, with no playback controls. Everything is controlled from the main window, and the projected one follows it at once: pressing play on a song replaces the one being sung immediately, while **Play next** and **Add to queue** line up the following ones without interrupting it.

To set it up, drag the window to the projector and use the **Full screen** button in its bottom-right corner. The button and the mouse pointer disappear after a few seconds without moving the mouse. Your system has to extend the desktop to the projector rather than duplicate it. If the browser blocks the window, allow pop-ups for Downtify and press the button again.

Keep the main window open, because the audio plays there. Moving between pages doesn't affect it. Reloading it pauses the music until you press play, and the projected window picks it up again by itself. Closing it stops the music and leaves the projected window waiting: close that one too and open a new one. Both windows must be in the same browser on the same computer.

## Hiding the lyrics

Prefer the artwork and the queue without the words? Turn off **Settings → General → Player → Show lyrics in the player**. It applies at once, and takes away everything that leads to lyrics in the player:

- the **Lyrics** and **Karaoke** panels and their tabs (on phones, their buttons in the Now playing footer);
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

Playing an album, artist, playlist or the track list queues those tracks in order, starting from the one you picked. **Shuffle** on a collection starts it in a random order. Tracks you haven't downloaded play in full right in the queue, served from the server's stream cache: while one plays, the next one is already being prepared one track ahead, so playback runs through undownloaded rows without stopping — even where the browser itself can't reach YouTube. When matching an undownloaded track, the player skips search results more than 10 seconds away from its known duration. A streamed track is never saved, liked or remembered across reloads.

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
| `Ctrl` / `⌘` + `F` | Search the playlist (on a playlist page) |
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
