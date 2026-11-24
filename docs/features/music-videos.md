---
icon: lucide/clapperboard
---

# Music Videos

Downtify can save each song's official music video next to it, for media servers like Plex and Jellyfin, and show that video in the built-in player while the song plays. It is off until an admin turns it on.

## Turning it on

In **Settings → Downloads & files → Music videos** (admins), turn on **Download music videos**. From then on, every song Downtify finishes downloading gets its video too:

- **Video file name** — the name of the video file, without the extension. It can use `{filename}` (the song's own file name, without extension), `{title}`, `{artist}`, `{album}` and `{track_number}` (two digits). The default, `{filename}-video`, is the name Plex links to the track as its music video: `03 - Night Drive.mp3` gets `03 - Night Drive-video.mp4` beside it, in the same album folder. Other Plex types work the same way, e.g. `{filename}-live`.
- **Video format** — **MP4** (H.264 video and AAC sound, which every browser and media server plays) or **MKV**. Pick MKV if your media server lists MP4 files as songs.

Videos are downloaded up to 1080p (YouTube offers more than 360p only to a downloader with a JavaScript runtime, which the Docker image includes), one at a time, after their song is done — they never hold up the download queue, and a song whose video can't be found or downloaded is simply left without one (the server log says why). Turning the setting on doesn't go back over songs already in the library.

::: info Which video is picked
Downtify looks the song up among YouTube Music's videos and only takes one whose title and artist match the song's. Live performances, lyric videos, covers, remixes, visualizers and "official audio" uploads are left out, unless the song itself is one (a live song can get a live video). An artist's official music video comes first, then the one whose length is closest to the song's. Downloads use the same [YouTube cookies](youtube-cookies.md) and connection settings as songs.
:::

The Library doesn't list video files as songs. Deleting a song deletes its video too.

## Watching in the player

When the song playing has a music video, **Now playing** shows it as its **background**, on wide screens and phones alike: the cover, the title and the lyrics stay where they are, over a dark veil that keeps them readable. The video fades in once it can play.

It always fills the whole screen, whatever the screen's shape: its edges are cropped like a cover image, and black bars burnt into the video itself (an old 4:3 clip inside a widescreen frame, a letterboxed "cinematic" one) are measured once and zoomed out of view.

The video plays **without sound**: you keep hearing the song itself, so the [equalizer](player.md#equalizer), volume normalization and the lyrics' timing all work as usual. The picture follows the song — pausing, seeking, skipping and the playback speed — and a song longer than its video holds the video's last frame. A video with an intro or ending of its own may not line up exactly with the song.

A video saved while the song was already playing shows up within half a minute, without reloading the page.

To keep the usual background, turn off **Play music videos** in **Settings → General → Player**. It is yours: it follows your account to every browser you sign in to, and changes nothing for anyone else.

## API

[`GET /api/music-video`](../api-reference.md#get-apimusic-video) answers `{video, url, crop}` for a library song that has a video, and `GET /api/music-video/file` streams it.
