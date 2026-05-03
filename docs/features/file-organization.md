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
│   ├── Arctic Monkeys - Do I Wanna Know.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── Arctic Monkeys - R U Mine.mp3       ← single track
```

## Organize by artist

Enable **Settings → File organization → Organize by artist** to group every track — including playlist and album downloads — under a subfolder named after the primary artist:

```
downloads/
├── Arctic Monkeys/
│   ├── Arctic Monkeys - Do I Wanna Know.mp3
│   └── Arctic Monkeys - R U Mine.mp3
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
