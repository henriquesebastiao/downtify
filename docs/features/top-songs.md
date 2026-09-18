---
icon: lucide/star
---

# Top Songs from an Artist

Some artists have huge catalogs where only a handful of tracks matter. Instead of grabbing links track by track, or downloading a 50+ track "This is &lt;Artist&gt;" playlist just for the songs you actually want, paste the artist's own URL and pick how many of their top songs to download.

## How to use it

Paste an artist link into the search bar:

- **Spotify**: `https://open.spotify.com/artist/…`
- **YouTube Music**: `https://music.youtube.com/channel/UC…` or `https://music.youtube.com/@handle`

A **Top Songs of &lt;Artist&gt;** card appears at the top of the search results, with:

- The artist's cover art
- A stepper to choose how many top songs to download (1–10, default 5)
- A **Download** button that queues the first N tracks as a batch

## Sources

| Source | What "top songs" means | Preview size |
|--------|------------------------|--------------|
| Spotify | The artist's own "Popular" shelf — the same tracks shown at the top of their Spotify home page | Up to 10 |
| YouTube Music | The artist's own "Top songs" shelf | ~5 |

For **YouTube Music**, raising the stepper past the shelf's own preview size triggers one extra request to resolve the shelf's full auto-generated playlist, so up to 10 songs are still available even when only ~5 are shown on the artist's page.

Spotify results go through the same metadata-then-YouTube-audio-match pipeline as any other Spotify link; YouTube Music results are pinned to their own video, like any other YouTube Music link.

## Downloading

Downloading writes an [M3U playlist](m3u-export.md) named **Top Songs of &lt;Artist&gt;**, exactly like a manual playlist download. If **Download playlist cover art** is enabled (see [Playlist Cover Art](playlist-cover-art.md)), the artist's own image is saved alongside the M3U as its cover — there's no separate setting for this, it reuses the same toggle.

## Known limitation: mixing Spotify and YouTube Music for the same artist

The M3U for **Top Songs of &lt;Artist&gt;** is kept in sync via the same playlist catalog used for regular Spotify playlists, which is keyed by Spotify track ids. If you download an artist's top songs from **Spotify**, then later download the *same* artist's top songs from **YouTube Music** (or the other way around), the second batch's tracks are downloaded to disk correctly, but aren't recorded in that catalog (YouTube Music track ids don't fit the Spotify-id format it expects) — so the next M3U refresh reverts to only the Spotify-sourced tracks, silently dropping the YouTube Music ones from the playlist file even though those files remain on disk.

Requesting more songs from the **same** source (e.g. 3, then later 5 more from Spotify) is unaffected — the M3U correctly grows to include everything. This limitation is specific to mixing sources for one artist's top-songs playlist; it doesn't affect single-source downloads.

## API

See [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) in the API Reference.
