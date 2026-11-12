---
icon: lucide/list-ordered
---

# Playlist order & repeated songs

A playlist you made in the Library — with **New playlist**, **Save a copy**, [Detach from source](library-catalog.md#detach-an-imported-playlist) or [an import from your music folders](external-playlists.md) — keeps its songs in the order you choose, and can play a song more than once. Playlists that follow a Spotify, YouTube Music or Deezer link keep their source's order, and **Liked songs** is ordered by when you liked each song.

## Reorder a playlist

1. Open the playlist and pick **Reorder**, next to the sort picker above its songs.
2. Move the songs:
    - drag a row to its new place (with a mouse);
    - or use the arrows on each row: **Move up** and **Move down**, and on wider screens **Move to top** and **Move to bottom**. The focus stays on the arrow, so the keyboard can keep moving the same song.
3. Pick **Save order**, or **Cancel** to leave it as it was.

Saving switches the page's sort to **Playlist order**, so you see the order you just saved. The order is written to the playlist's M3U file, which media servers that read it (Jellyfin, Navidrome, Plex) pick up too.

The owner, admins and the playlist's [editors](collaborative-playlists.md) can reorder it. A few things keep it safe:

- **Nobody's change is lost.** If someone else added or removed a song while you were reordering, saving reloads the playlist and asks you to arrange it again instead of dropping their change.
- **Songs hidden from you stay put.** A song an admin [hid from users](users.md#hiding-from-users) is not in your list, and keeps its place in the playlist when you save.

## Repeat a song

Adding a song the playlist already has asks first:

- From **Add to playlist** in a song's **⋯** menu, a dialog says it is **Already in this playlist**: pick **Add anyway** to add it again at the end, or **Don’t add**. Adding several songs at once asks once about all the ones already there; the others are added either way.
- In the **Add songs** dialog on the playlist's page, songs already there are marked **Already added**. Ticking one adds it again.

Each copy is a row of its own: it plays in its place, has its own number, and can be moved on its own. **Save a copy** keeps the repeats. A playlist holds up to 500 songs, copies included.

## Remove one copy

**Remove from playlist** in a row's **⋯** menu takes out that copy only; the song's other copies stay where they are.

## For apps and scripts

- [`PUT /api/library/playlists/order`](../api-reference.md#put-apilibraryplaylistsorder) saves a new order: every song the caller sees, copies included, in its new place. `409` when the playlist changed in the meantime.
- [`POST /api/library/playlists/tracks`](../api-reference.md#post-apilibraryplayliststracks) takes `allow_duplicates` to add a song again, answers which songs it skipped as `already`, and takes `remove_entries` to remove one copy.
- Playlist rows from [`GET /playlists`](../api-reference.md#get-playlists) and [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) list a repeated song once per copy, in order. The Android app shows every copy; reordering is done in the web app.
