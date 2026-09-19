---
icon: lucide/heart
---

# Liked songs

Tap the heart on a song to like it. As soon as one song is liked, Downtify keeps a **Liked songs** playlist with every song you have liked, so your favourites are one click away — in Downtify and in any media server pointed at your library.

There is nothing to switch on.

## Liking a song

The heart sits next to every song you have downloaded:

- in the track lists — Library, albums, artists and playlists;
- in the [player bar](player.md#player-bar) (on screens 640px wide and up);
- in [Now playing](player.md#now-playing), beside the song title.

Tap it to like, tap it again to take the like back. It fills in green and the change is on the server right away, so a heart tapped on your phone is there on your desktop too — open tabs and devices follow along on their own.

Only songs in your library can be liked. A search result you haven't downloaded yet has no heart; download it first.

## The playlist

The first like creates the playlist, and a short notice offers to open it. It is listed like any other playlist — in the sidebar, on the Home page and in **Library → Playlists** — but always **first**, with a heart instead of a cover. Its songs are ordered with the most recently liked at the top.

Taking back the last like removes the playlist again; there is no empty **Liked songs** hanging around.

The title follows your [language](internationalization.md). On disk the playlist is a plain [M3U file](m3u-export.md) with a fixed name:

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

That is why Jellyfin, Navidrome, Plex and friends show it too: they read the same file. The name is reserved on purpose. Spotify playlists called *Liked Songs* are common, and a downloaded playlist of that name would otherwise have written into the same file.

## Removing all likes

Open the playlist, then **⋯ → Remove all likes**, and confirm. Every heart is cleared and the playlist goes away.

::: info Your songs stay
Removing likes never deletes audio. Only the hearts and the playlist are removed — the files are still in your library. This is different from deleting a downloaded playlist, which deletes its songs; **Liked songs** is never handled that way. Asking to delete it (in the app or through the [API](../api-reference.md#delete-apilibraryplaylist)) just clears the likes.
:::

## Keeping likes in step with the files

A like follows the file it was given to:

| What happens to the file | What happens to the like |
|--------------------------|--------------------------|
| You delete the song in Downtify | The like goes with it, and the playlist is rewritten |
| You move it and run [Fix library paths](library-catalog.md#fix-library-paths) | The like follows the file to its new place |
| It disappears outside Downtify (an unmounted drive, a manual delete) | The like is kept, but the song is left out of the playlist until it is back |

Keeping the like of a missing file means an unplugged drive doesn't cost you your hearts. If you deleted files by hand and want the likes gone too, use **Remove all likes**, or unlike the songs before you delete them.

## Good to know

- Likes are stored in the library database (`downtify_library.db`, in your `/data` volume), not in the audio files. Nothing is written into a song's tags.
- The playlist is not created in [Navidrome](slskd-navidrome.md) by Downtify. It is a plain M3U file, so what a media server does with it depends on how that server reads M3U files.
- The [playlist file](m3u-export.md) is written even when *Write M3U playlists* is off in the download settings: the playlist is the point of the feature.

## API

`GET /api/likes`, `PUT /api/likes` and `POST /api/likes/clear`, plus a `liked` flag on [`GET /playlists`](../api-reference.md#get-playlists). See the [API reference](../api-reference.md#likes).
