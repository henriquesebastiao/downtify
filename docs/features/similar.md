---
icon: lucide/sparkles
---

# Similar

**Similar** finds tracks that sound like one you name, from YouTube Music's own radio mix — what YouTube plays after your track. No API key, no setup.

## How to use it

Open **Similar** from the sidebar (under **Charts**, or the **More** sheet on phones). Type the **Artist** and the **Track**, then **Find similar**. Every row shows cover art and how closely the match ranks (the `%`):

You don't have to type, either: every track row in the app carries a **Similar** button (the wand icon next to the download button — in Search, Charts, Top songs, pasted links, and as a context-menu item on Library, Album, Artist and Playlist tracks). It opens this page already searching for that track.

- **Play in full** — tap the cover and the track streams from this server straight into the built-in player, downloaded or not.
- **Download** — every row already carries its video and downloads straight away: Downtify queues the match through the same [matching pipeline](../how-it-works.md) every other download uses. From then on the row shows that download's progress, and a check once the song is in your library.
- **Endless list** — scrolling to the end loads the next page from the last track's own mix, and playback past the last row keeps the queue growing the same way, without end.

## API

See [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) in the API Reference.
