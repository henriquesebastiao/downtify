---
icon: lucide/trending-up
---

# Charts

**Charts** shows Deezer's own global chart — no genre filter, whatever is trending worldwide right now — without needing a Deezer account or API key.

## How to use it

Open **Charts** from the sidebar (or the **More** sheet on phones). Four tabs read from the same chart: **Tracks**, **Albums**, **Artists** and **Playlists**.

- **Tracks** — a ranked list. Press one (or tap its row) to stream it in full from YouTube, straight into the built-in player, before it's downloaded. Downloading a row works the same way a search result does: Downtify searches YouTube Music (falling back to standard YouTube) for the closest match to the track's title, artist and length, the same [matching pipeline](../how-it-works.md) every other download uses. Once a track is downloaded, its row plays it from your library instead of streaming it.
- **Albums**, **Artists** and **Playlists** — cover-art grids. Clicking one resolves it ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)) exactly as if you'd pasted that Deezer link into the search box yourself: its tracklist loads, ready to pick from and download.

## Why tracks download (and play in full) directly from here, but albums, artists and playlists open a page first

A chart track doesn't need a resolve step to download: Deezer already gives its title, artist and album name, which is enough to search for and match on YouTube, the same way a free-text search result is. An album, artist or playlist does need one — turning its link into a tracklist — so its card opens that resolved page instead of downloading straight from the grid. Playing a track row streams it in full from YouTube (never for albums, artists or playlists) — the same streaming every other track row uses, just fed the chart's title and artist.

## Watching or saving a chart playlist

Each playlist card has a **⋯** menu over its cover, with the two things its page offers besides downloading:

- **Watch for new tracks** adds a [Playlist Monitor](playlist-monitor.md#deezer-playlists) watch, checked every 6 hours: its first check downloads what the playlist has now, later ones what is added to it. Change the interval, pause or stop it on the **Monitor** page.
- **Add to my playlists** opens the playlist picker with the playlist's songs that are **already in your library**, to add them to one of your playlists or a new one named after it. Nothing is downloaded, and your playlist doesn't follow the chart playlist afterwards — use the download button or **Watch for new tracks** for that. When none of its songs are in the library yet, it says so instead.

## API

See [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) in the API Reference.
