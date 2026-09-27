---
icon: lucide/trending-up
---

# Charts

**Charts** shows Deezer's own global chart — no genre filter, whatever is trending worldwide right now — without needing a Deezer account or API key.

## How to use it

Open **Charts** from the sidebar (or the **More** sheet on phones). Four tabs read from the same chart: **Tracks**, **Albums**, **Artists** and **Playlists**.

- **Tracks** — a ranked list. Deezer streams a 30-second preview of most tracks; press one (or tap its row) to hear it before it's downloaded, the same preview player an artist's [Top songs](top-songs.md#on-an-artists-library-page) tab uses. Downloading a row works the same way a search result does: Downtify searches YouTube Music (falling back to standard YouTube) for the closest match to the track's title, artist and length, the same [matching pipeline](../how-it-works.md) every other download uses. Once a track is downloaded, its row plays it from your library instead of the preview.
- **Albums**, **Artists** and **Playlists** — cover-art grids. Clicking one resolves it ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)) exactly as if you'd pasted that Deezer link into the search box yourself: its tracklist loads, ready to pick from and download.

## Why tracks download (and play a preview) directly from here, but albums, artists and playlists open a page first

A chart track doesn't need a resolve step to download: Deezer already gives its title, artist and album name, which is enough to search for and match on YouTube, the same way a free-text search result is. An album, artist or playlist does need one — turning its link into a tracklist — so its card opens that resolved page instead of downloading straight from the grid. The preview clip on a track row is a separate thing Deezer streams for most tracks (never for albums, artists or playlists) — the same short-clip player an artist's Spotify top songs already use, just fed a Deezer link instead of a Spotify one.

## API

See [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) in the API Reference.
