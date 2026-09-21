---
icon: lucide/star
---

# Top Songs

Some artists have huge catalogs where only a handful of tracks matter. Instead of grabbing links track by track, or downloading a 50+ track "This is…" playlist for the few songs you actually want, paste the artist's own link and pick from their most popular songs.

## How to use it

1. Paste an artist link into the search box or on the Home screen:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` or `https://music.youtube.com/@handle`
2. The **artist page** opens with their photo and name. On YouTube Music it also lists every release. Next to **Watch for new releases** there is a **Top Songs** button.
3. **Top Songs** opens the list of their most popular songs, in the order the service ranks them. The first five are already ticked; tick more or untick any of them, then press **Download selected**.

## Sources

| Source | What "top songs" means | Songs listed |
|--------|------------------------|--------------|
| Spotify | The artist's own **Popular** shelf, the same tracks shown at the top of their Spotify page | Up to 10 |
| YouTube Music | The artist's **Top songs** playlist, ranked by popularity | The first 50 |

Spotify's public embed has no discography, so a Spotify artist page has no release list, only **Top Songs** and **Watch for new releases**. Spotify songs go through the usual metadata-then-audio-match pipeline, with their album name attached up front; the download fills in the rest (track number, year) as it does for any Spotify song. YouTube Music songs are pinned to their own video, like any other YouTube Music link.

## Creating a playlist

The **Create playlist** switch on the Top Songs page is **off by default**. Downloading with it off puts the songs in a folder named **Top Songs of {artist}** (or in your artist/album folders when [File organization](file-organization.md) is set that way), but writes no M3U and doesn't save the artist's photo.

Turn it on and Downtify also:

- writes an [M3U playlist](m3u-export.md) with the same name, **in the artist's ranking order**, even when you only ticked some of the songs;
- saves the artist's photo next to the M3U as its cover, if **Save playlist cover art** is enabled (see [Playlist cover art](playlist-cover-art.md)). There is no separate setting for this.

## Known limitations

::: warning Mixing Spotify and YouTube Music for the same artist
The M3U of **Top Songs of {artist}** is kept in sync from the [playlist catalog](library-catalog.md), which is keyed by Spotify track ids. If you download an artist's top songs from **Spotify** and later from **YouTube Music** (or the other way around), the second batch's files download correctly, but the next M3U refresh drops them from the playlist file, because YouTube Music ids don't fit that format. Adding more songs from the **same** source is unaffected.
:::

::: info Album names for Spotify songs
Spotify's artist page doesn't say which album a song is from. Downtify gets the album names from the same Spotify player API it uses to read full playlists, with one extra request per artist. That API isn't public, so if Spotify changes it, the **Album** column comes up empty for Spotify songs; the songs still download, but Downtify then has to recover the album from its YouTube Music match, which often fails, leaving the file without an album tag and, with [Organize by album](file-organization.md) on, in an `unknown` album folder. YouTube Music top songs carry their album already.
:::

## API

See [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) in the API Reference.
