---
icon: lucide/users-round
---

# Collaborative playlists

A playlist you [share with specific people](users.md#sharing-playlists) is view-only for them: they play it, follow it and save a copy. On a playlist made in the Library (with **New playlist**, or [detached](library-catalog.md#detach-an-imported-playlist) from its source) you can also let some of them add and remove its songs — a party playlist the whole house fills, say. They become its **editors**; everyone else on the list keeps listening only.

## Letting people edit

1. Open the playlist and pick **Share…**, on its page or in its **⋯** menu.
2. Choose **Specific people** and tick who to share it with.
3. Under each person you picked, tick **Can add and remove songs** for those who should edit it, then **Save**.

Open **Share…** again to see who edits it and to change that.

## What an editor can do

The playlist shows up for them under **Shared with me**, and its page says it is by its owner and that they can add and remove songs. An editor can:

- **Add songs** from the playlist page or its **⋯** menu, and pick the playlist under **Add to playlist** in any song's menu, after their own playlists.
- **Remove from playlist** in a song's **⋯** menu on the playlist's page.

Renaming, sharing, deleting and the cover art saved from a source link stay with the owner and admins. An editor can still **Save a copy**, like any viewer.

A few things hold for everyone who edits it, the owner included:

- **Only songs they can see.** Songs come from the shared library; one an admin [hid from users](users.md#hiding-from-users) can't be added by someone it is hidden from.
- **Changes show up at once** for the owner and the other editors, without reloading the page.
- **Nobody's songs get lost.** Two people adding songs at the same moment both get theirs in: edits are applied one after the other.

## When editing ends

Editing goes with the share:

- Untick **Can add and remove songs** for someone and they go back to listening only. Removing them from the list takes the playlist away from them altogether.
- Making the playlist **Private** or **Public** ends all editing: a public playlist is view-only for everyone.
- While an admin has **Settings › Library › Allow users to share playlists** off, nobody edits a playlist that isn't theirs. Like the shares themselves, the editors are back when it is switched on again.
- Renaming the playlist keeps its editors. Deleting it, or deleting an editor's account, drops them.

## Imported playlists

A playlist downloaded from a Spotify, YouTube Music or Deezer link follows its source — its watch or a new download of the link rewrites it — so it can't have editors. To fill one together:

- **Share an editable copy**: in **Share…**, with **Specific people** chosen, this saves a copy that is yours and opens its sharing with the people you picked, each already allowed to add and remove songs: untick anyone who should only listen, then **Save**. The original keeps following its source.
- **Detach from source** turns the playlist itself into a Library one, which stops following its source and can then have editors.

## For apps and scripts

Playlist rows from [`GET /playlists`](../api-reference.md#get-playlists) and [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) carry `can_edit_tracks`, and the owner's rows list `editors` (usernames). [`PUT /api/library/playlists/visibility`](../api-reference.md#put-apilibraryplaylistsvisibility) takes `editors`, some of `shared_with`; leaving it out keeps the current editors still on the list. Editors change songs with [`POST /api/library/playlists/tracks`](../api-reference.md#post-apilibraryplayliststracks), like the owner.
