---
icon: lucide/file-headphone
---

# File Organization

A new server organizes files by artist and album (`Artist/Album/…`): **Organize by artist** and **Organize by album** are both on by default. Turn them off for the flat layout below. Servers set up before this default keep the choice they had.

## Flat layout (both off)

Single tracks and YouTube searches go directly into the root of the downloads folder. Playlist and album tracks go into a per-playlist or per-album subfolder:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← single track
```

## Organize by artist

With **Settings → File organization → Organize by artist** on (the default), to group every track — including playlist and album downloads — under a subfolder named after the primary artist:

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

This structure is compatible with media servers (Jellyfin, Navidrome, Plex) and library managers (Beets) that expect an `Artist/Song.ext` folder layout.

## M3U and artist folders

When *Organize by artist* is on and you download a Spotify playlist with M3U generation also enabled, the M3U is placed in `<downloads>/Playlists/<playlist-name>.m3u` rather than inside the playlist subfolder. This is because the tracks are now spread across multiple artist folders. The relative paths inside the M3U still resolve correctly regardless of where you mount the library.

## Changing the setting

The setting takes effect immediately for all **new** downloads. Existing files already on disk are not moved.

## Deleting a track cleans up empty folders

Deleting a track from the Library page removes its per-playlist, artist or album folder too, once it's empty — and keeps climbing up through any now-empty parent folders (e.g. the artist folder after its last album is gone), stopping at the downloads directory itself, which is never removed. A folder that still holds anything else — another track, an `.m3u`, a `cover.jpg` still in use — is left alone.

## Selecting and deleting several tracks at once

The Library's track list has a checkbox on every track, plus a **Select all** checkbox that selects every track matching the current filter (see [Library page](library-catalog.md#library-page)). **Delete from library** in the selection bar removes all of them in one request (`DELETE /delete/batch`, see [API Reference](../api-reference.md)), with the same per-track cleanup (`.lrc`, orphaned `cover.jpg`, empty folders) as deleting one track at a time.

To delete a whole album or playlist, open it and pick **Delete** from its **⋯** menu. For everything by one artist, type the artist's name in the track list's filter, then **Select all** and delete.
