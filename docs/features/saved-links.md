---
icon: lucide/bookmark
---

# Saved links

Paste a Spotify, Deezer or YouTube Music playlist or album link in the search bar and Downtify opens its page. Songs already in your library play from it, and the rest stream through the server. **Save** keeps that page in Downtify, so you can come back to it later without downloading anything.

## Save a link

1. Paste the playlist or album link in the search bar.
2. On its page, choose **Save**. The button changes to **Saved**.

Choose **Saved** to remove it again.

**Save** is on playlists and albums from Spotify, Deezer and YouTube Music. Songs, artists and SoundCloud links can't be saved.

## Open a saved link

Your saved links are in **Library → Playlists**, in their own **Saved links** section, the newest first. Each one shows its cover, its name and where it comes from. Click one to open its page.

The page is read again each time you open it, so it shows the playlist as it is now, with any songs added since. The filter above the playlists also searches your saved links. The section is hidden while you have none.

To remove a saved link, open its **⋯** menu and choose **Remove**.

## What a saved link is

A saved link is a bookmark, nothing more:

- **Nothing is downloaded.** No M3U file, Navidrome playlist or Library playlist is made, and the playlist isn't watched.
- **It is yours.** Nobody else sees your saved links, admins included. Deleting your account deletes them.
- **Once per playlist.** The same playlist is saved once, however you pasted it (with or without `?si=` and other tracking parts).
- **Up to 500.** Remove one to save another after that.

To download the songs, use the download buttons on the page. To keep the playlist downloaded as it changes, use **Watch for new tracks** ([Playlist Monitor](playlist-monitor.md)). To make a playlist of the songs already in your library, use **Add to my playlists**.

Saved links are in the web app only for now. The mobile apps don't show them yet.

## API

The web app uses [`GET /api/library/saved-links`](../api-reference.md#get-apilibrarysaved-links), [`PUT /api/library/saved-links`](../api-reference.md#put-apilibrarysaved-links) and [`DELETE /api/library/saved-links`](../api-reference.md#delete-apilibrarysaved-links). They need a signed-in browser and only ever touch the caller's own links.
