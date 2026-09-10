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

## When it is written

The M3U is written **twice** per run — once as soon as the *first* track finishes downloading, and again when the run completes:

| Run type | Early write | Final write |
|----------|-------------|-------------|
| Playlist / album download, [CSV import](library-import.md) | After the first track finishes | After every track finishes |
| [Playlist Monitor](playlist-monitor.md#m3u-integration) sweep | After the first new track finishes | After the sweep completes |

The early write means the playlist is already playable — and you can confirm the sync is working — without waiting for the whole batch. A single slow or hung download no longer keeps the M3U from appearing at all. The final write picks up everything else that downloaded.

Both writes list tracks in **playlist order**, not in the order downloads happened to finish, so a partially-written M3U is still correctly ordered.

## Regeneration

The M3U is regenerated fresh on every run — re-pasting the same playlist URL produces a complete, in-order file including any tracks that were missing on earlier runs.

Tracks that failed to download or had no YouTube Music match are silently skipped.

## Compatibility

The generated file uses:

- UTF-8 encoding, no BOM
- LF line endings
- The standard `#EXTM3U` / `#EXTINF` format

This is compatible with Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos and any other player or media server that consumes standard M3U playlists.
