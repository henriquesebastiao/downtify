---
icon: lucide/columns-3
---

# Finder

**Finder** is a way to explore Deezer's catalogue before downloading. You search Deezer, then open an artist and browse them in three columns side by side, like the column view of macOS Finder: the artist, their discography and one album's tracks. It needs no Deezer account or API key.

## Searching

Open **Discover** from the sidebar (on phones: **More → Discover**): the Finder's search box is at the top of the page, with your recent Finder searches beside it. Searching replaces Discover's suggestions with what was found — songs, albums and artists with **All / Songs / Albums / Artists** chips, as on the regular Search page, but from Deezer only. Clear the box (the **×**) or go back to see the suggestions again; a recent search runs again with one click, and **Clear** forgets them all. Recent searches are kept in this browser only.

**Find songs** on an artist Discover suggests (its **⋯** menu) shows that artist's songs here, as a search: Deezer is searched for the artist's name, and only the songs by that very artist — matched by their Deezer id, so a namesake or a song merely called that is left out — are listed, up to the first few hundred.

- **Songs** stream in full and download like any search result. Downtify matches the song on YouTube Music (falling back to YouTube) by title, artist and length. Clicking a song's title opens its album in the column view, with the song highlighted.
- **Albums** open on their artist, with that album selected. The download button on the cover queues the whole album.
- **Artists** open the column view on that artist.

## The column view

| Column          | What it shows                                                                                                                                                                                                                                                                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Artist**      | The artist's photo and album count, their bio in the interface's language (expandable), their 10 most popular tracks, and "Fans also like" (related artists).                                                                                                                                                                                  |
| **Discography** | Every album, single, EP and compilation, most recent first, with its cover, title, release type, year and track count. Chips filter by release type.                                                                                                                                                                                           |
| **Tracks**      | The selected album's cover and title, its artist, year, track count and length. An information panel lists the release date, label, genres, credits and UPC. Below it are the album's tracks, where each one streams in full until it's downloaded and plays from your library afterwards, with a **Download album** button to queue them all. |

Clicking a popular track selects its album and highlights the track, both columns scroll smoothly to bring them into view (instantly when the system is set to reduce motion), and once the album's tracks are on screen the track starts playing in full — streamed, or the song itself if it's already in your library. Clicking it again while it plays doesn't pause it; opening the page from a link that points at a track doesn't start anything. Clicking a related artist opens that artist, and the browser's back button returns to the previous one. The path bar above the columns (**Discover › artist › album**) leads back to the search (or Discover, when the columns weren't opened from one) or to the artist alone. What's open is saved in the URL, so it survives a reload and can be bookmarked.

On a wide screen, drag the edge between two columns to make one wider or narrower, or focus it and use the arrow keys. A double-click puts the default widths back. The arrow button at the top of the artist and discography columns collapses the column to just its pictures: the artist's photo, their popular tracks' covers and the related artists' photos, or the album covers. Each picture still works like its full row, and its name shows on hover. Widths and collapsed columns only last while you're on the page: they're never saved, so a reload or leaving the Finder resets them.

On a phone, the columns sit side by side and you swipe between them. Picking an album slides over to its tracks.

::: info Why track counts appear a moment later
Deezer's discography listing has no track count, so Downtify asks for each album's count separately, a few albums at a time, staying under Deezer's limit of 50 requests every 5 seconds. Counts appear while you look, and are remembered until Downtify restarts. An album whose count couldn't be fetched shows `…`.
:::

## API

See [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) and the endpoints after it in the API Reference.
