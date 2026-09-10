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

The M3U is rewritten **after every track finishes downloading**, so the playlist file grows as the download progresses instead of appearing all at once at the end. This applies to playlist and album downloads, [CSV imports](library-import.md) and [Playlist Monitor](playlist-monitor.md#m3u-integration) sweeps alike.

That means the playlist is playable from the moment the first track lands, you can see the sync is working as it goes, and a single slow or hung download can never keep the M3U — or the tracks that already finished — from showing up.

A final rewrite runs once the whole run completes. It resolves every track against the filesystem (rather than the in-memory list of what this run downloaded), so it also picks up files from earlier runs and corrects anything that changed on disk mid-run.

Every write lists tracks in **playlist order**, not in the order downloads happened to finish, so a partially-written M3U is still correctly ordered.

!!! note "Tracks already on disk"
    Tracks downloaded by an earlier run stay in the M3U throughout — they're included from the first write, not only added by the final one.

## Regeneration

The M3U is regenerated fresh on every run — re-pasting the same playlist URL produces a complete, in-order file including any tracks that were missing on earlier runs.

Tracks that failed to download or had no YouTube Music match are silently skipped.

## Compatibility

The generated file uses:

- UTF-8 encoding, no BOM
- LF line endings
- The standard `#EXTM3U` / `#EXTINF` format

This is compatible with Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos and any other player or media server that consumes standard M3U playlists.
