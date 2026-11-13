---
icon: lucide/replace
---

# Replace Audio

Downtify picks the audio for each song automatically, and sometimes it picks the wrong one: another song with the same name, a live cut, a remix, or an upload with a long intro. **Replace audio** lets you pick the right version by hand. The track keeps its place everywhere — its playlists, M3U files, likes and paired apps — and only the audio changes.

Only admins can replace audio (see [Users & Sign-in](users.md#admins-and-users)).

## Replacing a track's audio

1. In the **Library**, open the menu of the track (right-click, or the **⋯** button) and choose **Replace audio…**.
2. Downtify searches **YouTube Music** and **YouTube** for "Artist - Title" and lists what it finds. Change the search, or paste a YouTube or YouTube Music link to one video or song — or a SoundCloud track link — to get exactly the upload you want.
3. Pick a version. Each shows where it comes from and how long it is, next to the length of your file. A version within 3 seconds of your file's length is highlighted. The ↗ button opens it on YouTube, so you can listen before choosing.
4. Press **Replace audio**. The replacement runs like a download: it shows its progress in the dialog and in the **Queue**, and the dialog says when it's done.

If it fails (the video is unavailable, or YouTube asks to sign in — see [YouTube cookies](youtube-cookies.md)), your file is left exactly as it was. **Retry** in the Queue tries the same video again, and pasting another link there replaces with that one instead.

## Using a file from your device

When the right version isn't on YouTube (a CD rip, a Soulseek download, a file someone sent you), use your own file:

1. In the dialog, under **Or use a file from your device**, press **Choose a file…** and pick the audio file.
2. Press **Replace audio**. The file is uploaded, checked to be readable audio, and given the old file's tags.

A file in the track's own format (an `.mp3` for an `.mp3`) is used exactly as it is. Another format (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`, `.wav`, `.aiff`, `.aac` or `.webm`) is converted to the track's format at the bitrate chosen in [Download settings](download-settings.md), so use the same format when you have it. This works in library-only mode too, since nothing is fetched from the internet.

## Downloads leave a replaced file alone

With **Download again if the file exists** on, a later download of the same song (from another monitored playlist, an artist watch or a playlist download) would write over your replacement with whatever the automatic match finds. So Downtify remembers every file whose audio you replaced, either way, and such a download counts it as already downloaded instead. [Library upgrade](library-upgrade.md) doesn't swap its audio either; its cover, lyrics and tags can still be upgraded.

The dialog says when a track's audio was replaced by hand. **Let downloads replace it** lifts this for that file.

## What stays the same

- **The file.** The new audio is written to the same path, in the same format: an `.mp3` stays MP3 (at the bitrate chosen in [Download settings](download-settings.md)), a `.flac` stays FLAC, and so on. So every playlist, M3U file, liked song, Navidrome entry and paired app that points at the file keeps pointing at it.
- **The tags.** Title, artists, album, track number, year, cover art, embedded lyrics and every other tag are copied from the old file to the new audio as they are. The `.lrc` sidecar is left alone. Synced lyrics were timed to the old audio: if the new version starts at a different point, they may be off.
- **The date.** The file keeps its modification date, so it doesn't jump to the top of "Recently added".

Only `.mp3`, `.flac`, `.m4a`, `.ogg` and `.opus` files — the formats Downtify writes — can be replaced.

## How it works

The chosen video is downloaded next to the file under a temporary name the library ignores (`<name>.downtify-upgrade.<ext>`), converted to the file's format, checked to be readable audio, given the old file's tags, and only then moved over the old file. The API is in the [API reference](../api-reference.md#get-apilibraryreplacecandidates).
