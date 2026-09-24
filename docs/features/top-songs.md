---
icon: lucide/star
---

# Top Songs

Some artists have huge catalogs where only a handful of tracks matter. Instead of grabbing links track by track, or downloading a 50+ track "This is…" playlist for the few songs you actually want, paste the artist's own link and pick from their most popular songs.

## How to use it

1. Paste an artist link into the search box or on the Home screen:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` or `https://music.youtube.com/@handle`
2. The **artist page** opens with their photo and name, and lists their releases (albums, singles, EPs and compilations, where the service has them), newest first on Spotify; click one to see its tracks or download it. Next to **Watch for new releases** there is a **Top Songs** button.
3. **Top Songs** opens the list of their most popular songs, in the order the service ranks them. A badge with an eye shows how many times each song has been played, shortened the way your language does it (`1,5 bi` in Portuguese, `1.5B` in English). Spotify's is green and YouTube Music's is red. YouTube Music only reports a rounded figure (`1.2B plays`), so its number is an approximation; Downtify reads it from the same YouTube Music request that lists the songs, plus one more request for the play counts. The first five are already ticked; tick more or untick any of them, then press **Download selected**.

## Sources

| Source | What "top songs" means | Songs listed |
|--------|------------------------|--------------|
| Spotify | The artist's own **Popular** shelf, the same tracks shown at the top of their Spotify page | Up to 10 |
| YouTube Music | The artist's **Top songs** playlist, ranked by popularity | The first 50 |

Spotify's public embed has no discography, so Downtify reads the releases from the Spotify web player's own discography query, the same non-public API it uses for the album names. If Spotify changes it, Downtify falls back to a shorter list (every album, but only the ten most recent singles) and, failing that, shows no releases. Spotify songs go through the usual metadata-then-audio-match pipeline, with their album name attached up front; the download fills in the rest (track number, year) as it does for any Spotify song. YouTube Music songs are pinned to their own video, like any other YouTube Music link.

## On an artist's Library page

An artist Downtify knows on Spotify (see [Artist photo, banner & bio](artist-images.md)) also gets a **Top songs** tab on their page in your Library, next to Tracks and Fans also like. It lists the first **5** of their Spotify top songs as a minimal list, like the search results, under column headings (#, Title, Album, length): number, cover, title, artist, album and length. A song that isn't in your library has a **download** button on the right (with its progress while it downloads); once it's downloaded that turns into the **In library** label, and the song can be played the way it is on an album page: the number turns into a play button on hover, the cover plays, and a double click or a tap plays too. Playing one queues the list's other downloaded songs after it, in ranking order, and the song being played is highlighted. Below the list, **See more popular songs** opens this artist on the Top Songs page described above, which is where the selection, the **Create playlist** switch and downloading several at once live. The tab only appears once the artist's Spotify id is known, which happens the first time their page is opened; the songs are asked for right then, so the tab's count fills in by itself a few seconds later, wherever you are on the page.

Reading a song's cover, album and play count takes a few seconds, so Downtify keeps the five songs in a file per artist, `<downloads>/Metadata/ArtistTopSongs/<Artist>.json`, made in the background the first time the artist's page is opened. It is trusted for **7 days**: opening the tab reads the file at once, and once it is older than that the old list is shown right away while a fresh one is fetched behind it - the page swaps it in by itself within a few seconds, without disturbing a song that is downloading or playing. The file only holds the songs, their cover links and play counts - never the audio or the images, and never whether a song is in your library, which is worked out live. It's a cache: delete it whenever you like and it is made again.

## Creating a playlist

The **Create playlist** switch on the Top Songs page starts **off** the first time you open an artist, and starts **on** once a playlist named **Top Songs of {artist}** already exists in your library, so later downloads keep adding to it. Flip the switch and your choice stays for as long as you are on that page. With it off, the songs download like any other individual songs: straight into your downloads folder, or into your artist/album folders when [File organization](file-organization.md) is on, with no folder of their own, no M3U and no artist photo.

Turn it on and Downtify treats them as a playlist named **Top Songs of {artist}**. Where it goes depends on File organization:

| Organize by artist / album | Songs | M3U and cover |
|---|---|---|
| Both off | In a folder named `Top Songs of {artist}` | In that same folder |
| Either or both on | Filed by those settings: `<Artist>/`, `<Album>/` or `<Artist>/<Album>/`. There is no `Top Songs of {artist}` folder. | In `Playlists/`, as `Top Songs of {artist}.m3u` and `.jpg` |

In both cases:

- the [M3U playlist](m3u-export.md) lists the songs **in the artist's ranking order**, even when you only ticked some of them;
- the artist's photo is saved next to the M3U as its cover, if **Save playlist cover art** is enabled (see [Playlist cover art](playlist-cover-art.md)). There is no separate setting for this.

## Known limitations

::: warning Mixing Spotify and YouTube Music for the same artist
The M3U of **Top Songs of {artist}** is kept in sync from the [playlist catalog](library-catalog.md), which is keyed by Spotify track ids. If you download an artist's top songs from **Spotify** and later from **YouTube Music** (or the other way around), the second batch's files download correctly, but the next M3U refresh drops them from the playlist file, because YouTube Music ids don't fit that format. Adding more songs from the **same** source is unaffected.
:::

::: info Album names for Spotify songs
Spotify's artist page doesn't say which album a song is from. Downtify gets the album names, and the play counts, from the same Spotify player API it uses to read full playlists: one extra request per artist, plus one for each album that request doesn't list. That API isn't public, so if Spotify changes it, the **Album** column comes up empty for Spotify songs and the play-count badge disappears; the songs still download, but Downtify then has to recover the album from its YouTube Music match, which often fails, leaving the file without an album tag and, with [Organize by album](file-organization.md) on, in an `unknown` album folder. YouTube Music top songs carry their album already. If the play counts stop coming through, for either source, the badge simply doesn't appear.
:::

## API

See [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) in the API Reference.
