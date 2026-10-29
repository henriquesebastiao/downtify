---
icon: lucide/eye-off
---

# Hidden playlist songs

A playlist downloaded from a Spotify, YouTube Music or Deezer link follows its source, and one a [Playlist Monitor](playlist-monitor.md) watch keeps up to date follows it on every sweep. Playlists made by generators and radios bring songs you don't want, and taking one out of the M3U by hand doesn't last: the next sweep writes it back. **Hide from playlist** takes the song out and keeps it out.

## Hiding a song

On the playlist's page, open a song's **⋯** menu and pick **Hide from playlist**. The message that confirms it has **Undo**.

From then on:

- **The song leaves the playlist right away**: its line goes from the playlist's [M3U file](m3u-export.md), so it also leaves the media servers that read it, and the Navidrome playlist when [Navidrome sync](slskd-navidrome.md) is on.
- **The file stays in your library**, searchable and playable from its album, its artist and any other playlist. To get rid of the file too, use **Delete** on the song in the Library.
- **Watch sweeps leave it out.** It isn't put back into the M3U and it isn't downloaded again, not even after you delete its file.
- **It is not missing any more.** **Download missing** skips it, and the playlist can be complete without it.
- **Downloading the playlist again from its link** keeps hidden songs out of the playlist.

The original playlist on Spotify or YouTube Music isn't changed: Downtify reads them without an account and can't edit them.

Only the playlist's owner (or an admin) hides songs. People it is [shared with](users.md#sharing-playlists) see the playlist as the owner keeps it. A playlist has to keep at least one song: to get rid of all of them, delete the playlist.

::: info Playlists you created in the Library
A Library playlist has no source to bring a song back, so it is edited directly with **Remove from playlist**. **Detach from source** on an imported playlist forgets its hidden songs the same way: they simply aren't in it any more, and can be added again like any other song.
:::

## Showing a song again

A playlist that hides songs lists them under its tracks, in **N hidden songs**. **Show tracks** opens the list, and **Show again** puts a song back where it was in the playlist.

A song whose file was deleted in the meantime reads **No longer in your library**. Showing it again only forgets that it was hidden: the next watch sweep, or **Download missing**, downloads it like any other missing song.

## In the apps

The apps hide songs by track id with the same rules, and list and show them again the same way: see [`POST /api/v1/playlists/hidden`](../api-reference.md#post-apiv1playlistshidden) and the [mobile client contract](../mobile-client-contract.md).
