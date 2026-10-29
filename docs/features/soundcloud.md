---
title: SoundCloud
icon: lucide/cloud
---

# SoundCloud

SoundCloud works in Downtify two ways: you can paste a **SoundCloud track link** to download that track, and you can turn **SoundCloud** on as an audio source, so songs from Spotify, YouTube Music or Deezer links that can't be found elsewhere are looked for there too. Both use [yt-dlp](https://github.com/yt-dlp/yt-dlp)'s SoundCloud support; no SoundCloud account is needed.

## Turning it on

SoundCloud is off by default. In **Settings → Audio sources**, tap **SoundCloud** to add it to the source order, then move it where you want it with the arrows. Each song tries the enabled sources in that order and stops at the first one that has it — see [slskd & Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order) for how the order works.

Most people put it last: SoundCloud is good for remixes, DJ edits and uploads that never made it to the big catalogues, while YouTube Music usually has the cleaner copy of everything else.

## SoundCloud links

Paste a track link into the search bar and press **Get it**:

| Link | Example |
|------|---------|
| Track | `soundcloud.com/artist/track-name` |
| Private track (shared with its secret link) | `soundcloud.com/artist/track-name/s-AbC123` |

`www.` and `m.` links work too, and the `?si=…` part that share buttons add is dropped. Sets (albums and playlists), a user's own pages and short `on.soundcloud.com` links aren't supported: open a short link in the browser first and paste the full link it leads to.

The track's details come from SoundCloud:

- **Title** and **cover** (the 500 px artwork) are the upload's own.
- **Artist** is the artist SoundCloud credits, else the account that uploaded it — so a label's upload is credited to the artist when SoundCloud says who it is.
- **Album** is the track's own name, like a single, unless SoundCloud names one.
- **Year** and **genre** come from the release date (or the upload date) and the genre tag.

### Where the audio comes from

A SoundCloud link names one exact track, and the **SoundCloud** source downloads that track without searching. It follows the source order like a pasted YouTube link does: sources above SoundCloud (slskd, Deemix) are still tried first, and with SoundCloud off the song is searched on the sources you have enabled instead. When none of them has it, the queue says so: *Could not find … — turn SoundCloud on in Settings > Audio sources to download SoundCloud tracks*.

## Finding songs on SoundCloud

For a song from any other link, the **SoundCloud** source searches SoundCloud for "artist title" and only takes a result when:

- the artist appears in the uploader's name or in the title (`Artist - Title` uploads count);
- the title is close to the song's;
- its length is within 30 seconds (or 20 %) of the song's;
- it isn't a remix, live recording, bootleg, mashup, cover, karaoke, sped-up or slowed version, a preview or a snippet — unless the song is itself that version.

When nothing qualifies, the song moves on to the next source.

## Using a SoundCloud link for a failed song

In the **Queue**, **Force audio source** under a failed song also takes a SoundCloud track link: the song keeps its title, artist, album, cover and lyrics, and the audio comes from that track. The link is used at SoundCloud's place in the source order, so SoundCloud has to be on.

[Replace audio](replace-audio.md) takes SoundCloud track links too, to swap a library file's audio for a SoundCloud upload.

## Limits

- **Sound quality.** SoundCloud streams lossy audio (usually 128–160 kbps). Choosing FLAC or a higher bitrate in [Download settings](download-settings.md) converts it, but can't add back what the stream doesn't have.
- **SoundCloud Go+ tracks.** Without a Go+ subscription, SoundCloud only plays a 30-second preview of these. Downtify refuses the preview instead of saving it as the song: the download fails with *only streams a 30-second preview on SoundCloud*.
- **Region blocks.** A track the uploader blocked in your server's country fails like an unavailable video.
- **No watching.** A SoundCloud link is one track, so there's nothing for the [Playlist Monitor](playlist-monitor.md) to watch.
