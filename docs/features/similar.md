---
icon: lucide/sparkles
---

# Similar

**Similar** finds tracks that sound like one you name, using Last.fm's `track.getSimilar` — what Last.fm's listeners play next after your track.

## How to use it

Last.fm needs an API key, and it has to be yours: create a free one at [last.fm/api/account/create](https://www.last.fm/api/account/create) and paste it once in **Settings → Audio sources → Last.fm** (admins). The **Test connection** button next to the field tries the key as typed — saved or not — and says whether Last.fm accepts it, so a typo shows up before the first search, not after. Until a working key is saved, the page tells you where the key goes instead of searching.

Open **Similar** from the sidebar (under **Charts**, or the **More** sheet on phones). Type the **Artist** and the **Track**, then **Find similar**. Every row shows Last.fm's cover art and how closely it ranks the match (the `%`):

You don't have to type, either: every track row in the app carries a **Similar** button (the wand icon next to the download button — in Search, Charts, Top songs, pasted links, and as a context-menu item on Library, Album, Artist and Playlist tracks). It opens this page already searching for that track.

- **Preview** — tap the cover to hear the 30-second clip, the same preview player the [Charts](charts.md#how-to-use-it) tracks use (looked up on Deezer by artist and title).
- **Download** — the download button first resolves the row into a real song (Last.fm rows carry no download link of their own): Downtify searches for the closest match to its title and artist and queues that, the same [matching pipeline](../how-it-works.md) every other download uses. From then on the row shows that download's progress, and a check once the song is in your library.
- The arrow opens the track's Last.fm page.

## API

See [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) and [`POST /api/similar/test`](../api-reference.md#post-apisimilartest) in the API Reference.
