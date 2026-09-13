---
icon: lucide/file-headphone
---

# File Organization

By default Downtify saves files in a flat layout. An optional *Organize by artist* mode groups them into per-artist subfolders.

## Default layout (flat)

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

Enable **Settings → File organization → Organize by artist** to group every track — including playlist and album downloads — under a subfolder named after the primary artist:

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

The Library page's file list has a checkbox on every track, plus a **Select all** toggle that selects every track matching the page's current [playlist/artist/album filter](player.md#playing-a-single-playlist-artist-or-album) — including tracks on other pages, not just what's currently visible. **Delete selected** removes all of them in one request (`DELETE /delete/batch`, see [API Reference](../api-reference.md)), with the same per-track cleanup (`.lrc`, orphaned `cover.jpg`, empty folders) as deleting one track at a time.

Since the checkbox selection follows whatever filter is active, deleting an entire album or artist is: pick it from **Filter by**, click **Select all**, then **Delete selected**.
