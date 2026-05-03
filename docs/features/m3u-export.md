---
icon: lucide/list-music
---

# M3U Export

Downtify automatically generates a standard `EXTM3U` playlist file whenever a Spotify playlist is downloaded — either manually or via the [Playlist Monitor](playlist-monitor.md).

## File location

| Situation | M3U path |
|-----------|---------|
| Playlist downloaded normally | `<downloads>/<playlist-name>/<playlist-name>.m3u` |
| Playlist downloaded with *Organize by artist* enabled | `<downloads>/Playlists/<playlist-name>.m3u` |

When *Organize by artist* is on, tracks are spread across multiple artist folders, so the M3U is placed in a central `Playlists/` directory instead of the playlist subfolder.

## Relative paths

Track paths inside the M3U are written **relative to the M3U file itself**, not as absolute paths. This means the same file works whether it is read from inside the Downtify container (`/downloads/…`) or from another consumer that mounts the same library at a different root — for example Jellyfin under `/nas/music/…`. Just point your media server at the same library mount and the playlist will appear as a single unit.

## Enabling / disabling

M3U generation is controlled by **Settings → Generate M3U file for playlists** (on by default). Turning it off skips M3U creation entirely; the rest of the download flow is unchanged.

## Regeneration

The M3U is regenerated fresh on every run:

- Re-pasting the same playlist URL produces a complete, in-order file including any tracks that were missing on earlier runs
- The Playlist Monitor regenerates the M3U after each sweep that downloads at least one new track

Tracks that failed to download or had no YouTube Music match are silently skipped.

## Compatibility

The generated file uses:

- UTF-8 encoding, no BOM
- LF line endings
- The standard `#EXTM3U` / `#EXTINF` format

This is compatible with Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos and any other player or media server that consumes standard M3U playlists.
